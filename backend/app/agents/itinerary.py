import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.agents.base import AgentBase
from app.services import amap_client, fliggy_client, weather_client
from app.services.llm_client import LLMClient
from app.services.scenic_spot_service import ScenicSpotService
from app.services.travel_context_service import CITY_CENTER, TravelContextService


def compute_schedule(
    visit_minutes: list[int], commute_minutes: list[int], start_minute: int = 8 * 60 + 40
) -> dict[str, list[tuple[int, int]]]:
    """按通勤与游览时长顺序推算全天时间轴（分钟制）。

    - 首站出发时间由用户约束决定（默认 08:40 早餐后；「避免早起」时延后至 09:40）
    - 每段游览时长收敛到 60-150 分钟
    - 午餐紧随上午行程（不早于 12:00，60 分钟），下午行程从午餐后继续
    - 晚餐不早于 18:20 且在末站结束之后；夜宵至少在晚餐结束 1 小时后
    """
    def clamp(visit: int | None) -> int:
        return min(max(visit or 120, 60), 150)

    items: list[tuple[int, int]] = []
    clock = start_minute
    lunch = (12 * 60, 13 * 60)
    for index, visit in enumerate(visit_minutes):
        commute = commute_minutes[index] if index < len(commute_minutes) else 15
        start = clock + commute
        end = start + clamp(visit)
        items.append((start, end))
        if index == 0:
            lunch = (max(12 * 60, end + 10), max(12 * 60, end + 10) + 60)
            clock = lunch[1]
        else:
            clock = end
    last_end = items[-1][1] if items else 17 * 60
    dinner_start = max(18 * 60 + 20, last_end + 10)
    dinner = (dinner_start, dinner_start + 60)
    supper_start = max(21 * 60 + 30, dinner[1] + 60)
    supper = (supper_start, supper_start + 40)
    return {
        "items": items,
        "breakfast": (start_minute - 40, start_minute),
        "lunch": lunch,
        "dinner": dinner,
        "supper": supper,
    }


def _fmt_clock(minute: int) -> str:
    # 防溢出：行程过满被推到 24 点后时，显示为"次日 HH:MM"，杜绝 25:58/32:07 这类错乱时间
    hour, minute_of_hour = minute // 60, minute % 60
    if hour >= 24:
        return f"次日 {hour - 24:02d}:{minute_of_hour:02d}"
    return f"{hour:02d}:{minute_of_hour:02d}"


class ItineraryAgent(AgentBase):
    name = "Itinerary"

    def __init__(self) -> None:
        self.scenic_spots = ScenicSpotService()
        self.travel = TravelContextService()
        self.llm = LLMClient()

    def _day_forecasts(self, destination: str) -> list[dict[str, str]]:
        """双源逐日预报（和风主 + Open-Meteo 备，date/text_day/temp_min/temp_max）；均失败时为空。"""
        if not (amap_client.is_ready() and weather_client.is_ready()):
            return []
        geo = amap_client.geocode(destination)
        if not geo:
            return []
        return weather_client.weather_3d(f"{geo['lng']},{geo['lat']}") or []

    def _enrich_with_fliggy(self, destination: str, itinerary: list[dict[str, Any]]) -> None:
        """飞猪AI 补充：按最终景点名精确查询榜单/预订链接/实拍图（并发查询，客户端 10 分钟缓存）。"""
        if not fliggy_client.is_ready():
            return
        names: list[str] = []
        seen: set[str] = set()
        for day in itinerary:
            for item in day.get("items", []):
                name = item["spot"].get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)

        def match_name(poi_name: str, query: str, original: str) -> bool:
            if not poi_name:
                return False
            return (
                poi_name == query
                or query in poi_name
                or poi_name in query
                or poi_name == original
                or original in poi_name
                or poi_name in original
            )

        def lookup(name: str) -> tuple[str, dict[str, Any] | None]:
            # 名称变体：收录名可能不带"南昌"前缀或词序不同（如"八一起义纪念馆" vs "八一南昌起义纪念馆"）
            variants = [name]
            if name.startswith("南昌") and len(name) > 2:
                variants.append(name.replace("南昌", "", 1))
            best: dict[str, Any] | None = None
            for variant in variants:
                try:
                    pois = fliggy_client.search_pois(destination, variant)
                except Exception:
                    continue
                if not pois:
                    continue
                for poi in pois:
                    if match_name(poi.get("name", ""), variant, name):
                        return name, poi
                if best is None:
                    best = pois[0]
            return name, best

        if not names:
            return
        results: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            for name, poi in pool.map(lookup, names):
                if poi:
                    results[name] = poi
        # 网络抖动导致的失败单点串行重试一轮（DNS/连接故障通常瞬时恢复）
        missing = [n for n in names if n not in results]
        for name in missing:
            time.sleep(0.6)
            _, poi = lookup(name)
            if poi:
                results[name] = poi
        for day in itinerary:
            for item in day.get("items", []):
                poi = results.get(item["spot"].get("name", ""))
                if poi:
                    item["spot"]["list_rank"] = poi.get("list_rank", "")
                    item["spot"]["booking_url"] = poi.get("booking_url", "")
                    item["spot"]["main_pic"] = poi.get("main_pic", "")
                    # 来源溯源：飞猪命中时追加预订页链接（去重，保留高德链接在前）
                    booking_url = poi.get("booking_url", "")
                    if booking_url:
                        urls = list(item["spot"].get("source_urls", []))
                        if booking_url not in urls:
                            urls.append(booking_url)
                        item["spot"]["source_urls"] = urls

    def _fallback_tip(self, day: dict[str, Any]) -> str:
        """LLM 不可用时的天气驱动模板建议（确定性文案，不虚构实时信息）。"""
        weather = day.get("weather") or ""
        first = day["items"][0]["spot"].get("name", "首站") if day.get("items") else "首站"
        if any(k in weather for k in ("雨", "雷", "雪")):
            return f"当日有降水，优先安排室内场馆并随身携带雨具；{first}周边的博物馆、老字号茶馆都是避雨歇脚的好去处。"
        return f"天气适宜，建议早点出发避开人流；{first}多留些时间慢慢逛，晚间顺路体验当地夜市烟火气。"

    def _enrich_with_llm(self, user_input: dict[str, Any], itinerary: list[dict[str, Any]]) -> dict[str, dict[str, Any]] | None:
        """LLM 内容增强：趣味建议 + 有内容的景点理由 + 具体菜品与人均参考（失败返回 None 保持原文案）。"""
        if self.llm.mode != "real":
            return None
        days_payload = []
        for day in itinerary:
            days_payload.append(
                {
                    "day": day["day"],
                    "theme": day["theme"],
                    "weather": day.get("weather") or "暂无预报",
                    "spots": [
                        {"name": item["spot"].get("name", ""), "tags": item["spot"].get("tags", [])[:3]}
                        for item in day.get("items", [])
                    ],
                    "meals": [
                        {"meal": meal["meal"], "restaurant": meal.get("restaurant", ""), "type": meal.get("signature", "")}
                        for meal in day.get("meals", [])
                    ],
                }
            )
        prompt = (
            f"为{user_input['destination']}的行程书做内容润色，基于以下真实行程与实时天气数据：\n"
            f"{json.dumps(days_payload, ensure_ascii=False)}\n\n"
            "对每一天输出：\n"
            "1. fun_tip：结合当天天气与景点的一条有趣建议，40字内，具体可执行、有当地特色（如看日落的位置、必尝小吃、避雨方案）\n"
            "2. spot_reasons：每个景点的推荐理由，40字内，讲历史文化或体验亮点，禁止复述标签\n"
            "3. meal_details：每餐的 signature（具体菜名组合，如\"瓦罐汤+拌粉\"，禁止写店铺类型）和 price_hint（写\"人均约 XX 元\"的估算）\n\n"
            '只输出 JSON：{"days": {"1": {"fun_tip": "...", "spot_reasons": {"景点名": "..."}, "meal_details": {"午餐": {"signature": "...", "price_hint": "人均约 XX 元"}}}}}'
        )
        result = self.llm.try_generate_json(prompt, max_tokens=2400)
        if not result or not isinstance(result.get("days"), dict):
            return None
        return result["days"]

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        plan_days = context["outputs"]["Planner"]["payload"]["days"]
        itinerary = []
        all_legs: list[dict[str, Any]] = []
        time_slots = ["09:00-11:30", "13:30-16:00", "16:30-18:00"]
        anchor = dict(CITY_CENTER)
        # 锚点优先级：按预算匹配的推荐酒店（地理位置排程） > 目的地市中心 > 北京天安门兜底
        recommended_hotel = self.travel.recommend_hotel_poi(
            user_input["destination"],
            budget=user_input.get("budget"),
            days=user_input["days"],
            origin=user_input.get("origin"),
        )
        if recommended_hotel:
            anchor = {
                "name": recommended_hotel["name"],
                "lat": recommended_hotel["lat"],
                "lng": recommended_hotel["lng"],
            }
        elif amap_client.is_ready():
            geo = amap_client.geocode(user_input["destination"])
            if geo:
                anchor = {
                    "name": f"{(geo.get('city') or user_input['destination']).removesuffix('市')}市中心",
                    "lat": geo["lat"],
                    "lng": geo["lng"],
                }
        # 真实模式（高德 POI）下 Researcher 返回的景点不在静态库中，优先按名字取其完整字典（含坐标）
        researcher_spots = {
            spot.get("name"): spot
            for spot in context["outputs"]["Researcher"]["payload"].get("spots", [])
            if spot.get("name")
        }
        for day in plan_days:
            items = []
            legs: list[dict[str, Any]] = []
            previous = dict(anchor)
            for index, spot_name in enumerate(day["spot_names"]):
                spot = (
                    researcher_spots.get(spot_name)
                    or self.scenic_spots.get_spot(user_input["destination"], spot_name)
                    or {"name": spot_name}
                )
                leg = None
                transit_first = any(c in user_input.get("constraints", []) for c in ("减少打车", "优先地铁", "经济实惠"))
                if spot.get("lat") is not None and previous.get("lat") is not None:
                    leg = self.travel.commute_between(previous, spot, city=user_input["destination"])
                    legs.append(leg)
                    all_legs.append(leg)
                    source_label = "高德实时规划" if leg.get("source") == "高德路径规划" else "本地估算"
                    prefix = f"从{leg['from']}出发" if index == 0 else f"上一站「{leg['from']}」→ 本站"
                    if transit_first:
                        transport = (
                            f"{prefix}：推荐地铁约 {leg['metro_minutes']} 分钟（经济首选），"
                            f"打车备选约 {leg['taxi_minutes']} 分钟/{leg['taxi_fare']} 元（{source_label}）"
                        )
                    else:
                        transport = (
                            f"{prefix}：地铁约 {leg['metro_minutes']} 分钟，"
                            f"或打车约 {leg['taxi_minutes']} 分钟/{leg['taxi_fare']} 元（{source_label}）"
                        )
                else:
                    transport = "使用地铁/公交或短途打车（本地估算）"
                items.append(
                    {
                        "time": time_slots[index % len(time_slots)],
                        "title": f"游览{spot_name}",
                        "spot": spot,
                        "transport": transport,
                        "reason": f"该景点匹配 {', '.join(spot.get('tags', [])) or '用户偏好'}。",
                    }
                )
                previous = spot
            commute_minutes = sum(leg["taxi_minutes"] for leg in legs)
            max_leg = max(legs, key=lambda leg: leg["taxi_minutes"]) if legs else None
            spot_names = [item["spot"].get("name") for item in items if item["spot"].get("name")]
            meal_anchors = {
                "早餐": spot_names[0] if spot_names else None,
                "午餐": spot_names[0] if spot_names else None,
                "晚餐": spot_names[-1] if spot_names else None,
                "夜宵": spot_names[-1] if spot_names else None,
            }
            # 有坐标时传给四餐推荐：真实模式走高德周边餐饮检索
            meal_coords: dict[str, tuple[float, float]] = {}
            for meal_key, spot_idx in (("午餐", 0), ("晚餐", len(items) - 1)):
                if items and items[spot_idx]["spot"].get("lat") is not None:
                    meal_coords[meal_key] = (items[spot_idx]["spot"]["lng"], items[spot_idx]["spot"]["lat"])
            meals = self.travel.daily_meals(user_input["destination"], day["day"], meal_anchors, coords=meal_coords)
            # 动态时间轴：游览时间按通勤+游览时长推算，四餐时间随之让位；「避免早起」约束延后首站
            visit_minutes = [item["spot"].get("visit_minutes") or 120 for item in items]
            schedule_commutes = [
                legs[index]["metro_minutes"] if index < len(legs) else 15 for index in range(len(items))
            ]
            start_minute = 9 * 60 + 40 if "避免早起" in user_input.get("constraints", []) else 8 * 60 + 40
            schedule = compute_schedule(visit_minutes, schedule_commutes, start_minute)
            for item, (start, end) in zip(items, schedule["items"]):
                item["time"] = f"{_fmt_clock(start)}-{_fmt_clock(end)}"
            meal_schedule_keys = {"早餐": "breakfast", "午餐": "lunch", "晚餐": "dinner", "夜宵": "supper"}
            for meal in meals:
                start, end = schedule[meal_schedule_keys[meal["meal"]]]
                meal["time"] = f"{_fmt_clock(start)}-{_fmt_clock(end)}"
            itinerary.append(
                {
                    "day": day["day"],
                    "theme": day["theme"],
                    "items": items,
                    "meals": meals,
                    "legs": legs,
                    "commute_minutes": commute_minutes,
                    "max_leg": max_leg,
                }
            )
        # 每日天气标注（和风逐日预报，超出 3 天预报窗口的天数不标注）
        forecasts = self._day_forecasts(user_input["destination"])
        for index, day in enumerate(itinerary):
            if index < len(forecasts):
                forecast = forecasts[index]
                day["weather"] = f"{forecast['date']} {forecast['text_day']} {forecast['temp_min']}~{forecast['temp_max']}℃"

        # 飞猪AI 补充：榜单排名 + 预订链接 + 实拍图（按景点名精确查询；补充源失败不影响行程主流程）
        try:
            self._enrich_with_fliggy(user_input["destination"], itinerary)
        except Exception:
            pass

        # 内容增强：趣味建议 + 有内容的推荐理由 + 具体菜品与人均参考（LLM 一次调用；失败保持确定性文案）
        enriched = self._enrich_with_llm(user_input, itinerary)
        for day in itinerary:
            data = (enriched or {}).get(str(day["day"])) or {}
            if data.get("fun_tip"):
                day["fun_tip"] = data["fun_tip"]
            for item in day["items"]:
                reason = (data.get("spot_reasons") or {}).get(item["spot"].get("name", ""))
                if reason:
                    item["reason"] = reason
            for meal in day.get("meals", []):
                detail = (data.get("meal_details") or {}).get(meal.get("meal", ""))
                if detail:
                    if detail.get("signature"):
                        meal["signature"] = detail["signature"]
                    if detail.get("price_hint"):
                        meal["price_hint"] = detail["price_hint"]
            if not day.get("fun_tip"):
                day["fun_tip"] = self._fallback_tip(day)
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "itinerary": itinerary,
                "legs": all_legs,
            },
        }
