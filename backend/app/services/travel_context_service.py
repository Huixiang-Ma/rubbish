import json
import math
from functools import lru_cache
from typing import Any

from app.services import amap_client, qweather_client
from app.services.paths import STATIC_DATA_ROOT
from app.services.scenic_spot_service import ScenicSpotService

# 演示口径：以下速度、价格、时长均为本地静态估算，非实时路网/实时报价（诚实声明口径）。
ROAD_FACTOR = 1.4
WALK_SPEED_KMH = 4.5
METRO_SPEED_KMH = 25
TAXI_SPEED_KMH = 22
METRO_ACCESS_MINUTES = 15
TAXI_WAIT_MINUTES = 5
TAXI_BASE_FARE = 13.0
TAXI_PER_KM = 2.3
TAXI_MIN_FARE_KM = 3.0
MEAL_PER_DAY = 150
CITY_CENTER = {"name": "市中心（天安门）", "lat": 39.9087, "lng": 116.3975}
DAY_COMMUTE_HIGH_MINUTES = 150
LEG_TAXI_HIGH_MINUTES = 90
SAME_DAY_LEG_LIMIT_KM = 30.0

HOTEL_TIERS = [
    {"tier": "经济型", "per_night": 300},
    {"tier": "舒适型", "per_night": 600},
    {"tier": "品质型", "per_night": 1000},
]

# 出发地大交通演示样例：仅覆盖常见城市，时长与往返费用为静态估算。
INTERCITY_TABLE = {
    "上海": {"high_speed": "4.5-6 小时", "flight": "2 小时", "rail_first": True, "round_trip_cost": 1100},
    "杭州": {"high_speed": "4.5-5.5 小时", "flight": "2 小时", "rail_first": True, "round_trip_cost": 1200},
    "南京": {"high_speed": "3.5-4.5 小时", "flight": "2 小时", "rail_first": True, "round_trip_cost": 900},
    "武汉": {"high_speed": "4-5 小时", "flight": "2 小时", "rail_first": True, "round_trip_cost": 1000},
    "长沙": {"high_speed": "5.5-6.5 小时", "flight": "2.5 小时", "rail_first": True, "round_trip_cost": 1200},
    "西安": {"high_speed": "4.5-6 小时", "flight": "2.5 小时", "rail_first": True, "round_trip_cost": 1000},
    "成都": {"high_speed": "7.5-9 小时", "flight": "2.5 小时", "rail_first": False, "round_trip_cost": 1600},
    "广州": {"high_speed": "8-10 小时", "flight": "3 小时", "rail_first": False, "round_trip_cost": 1800},
    "深圳": {"high_speed": "8-10 小时", "flight": "3 小时", "rail_first": False, "round_trip_cost": 1800},
    "哈尔滨": {"high_speed": "6.5-8 小时", "flight": "2 小时", "rail_first": False, "round_trip_cost": 1300},
}
GENERIC_INTERCITY_COST = 1000

WEATHER_NOTES = [
    "春季（3-5 月）：多风沙，偶有扬尘，户外行程建议备口罩与外套。",
    "夏季（6-8 月）：高温多雷雨，正午高温时段建议安排室内场馆，午后户外注意补水。",
    "秋季（9-11 月）：秋高气爽，最适宜户外游览，热门景点需提前预约。",
    "冬季（12-2 月）：寒冷干燥，长城等山区景点注意防风保暖，冰雪天气留意道路封闭。",
]

# 周边 POI 演示模板：名称与距离为静态演示数据，坐标按景点位置确定性偏移生成。
NEARBY_TEMPLATES = {
    "food": [("老字号小吃", 0.3), ("家常菜馆", 0.6), ("网红咖啡", 0.4), ("夜市排档", 0.9)],
    "parking": [("景区地面停车场", 0.2), ("地下停车库", 0.5), ("路侧停车位", 0.35), ("换乘停车场", 1.2)],
    "toilet": [("北门公共厕所", 0.15), ("游客中心卫生间", 0.3), ("园区东侧厕所", 0.5)],
}
COMFORT_LEVELS = ["舒适", "一般", "拥挤"]


class TravelContextService:
    """出行要素服务（地图/通勤/打车/门票/住宿/大交通/天气）。

    全部为本地静态估算，演示口径：不接入实时路网、真实票价与天气预报。
    """

    @lru_cache(maxsize=8)
    def load_spots(self, destination: str) -> list[dict]:
        # 前端选择带行政区划后缀（如"北京市"），匹配时归一化为城市短名
        if destination.removesuffix("市") != "北京":
            return []
        path = STATIC_DATA_ROOT / "scenic_spots_beijing.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def haversine_km(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radius = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * radius * math.asin(math.sqrt(a))

    def commute_between(self, origin: dict[str, Any], target: dict[str, Any], city: str | None = None) -> dict[str, Any]:
        """两个地点之间的通勤估算：真实模式走高德路径规划，否则本地静态估算。"""
        straight_km = self.haversine_km(origin["lat"], origin["lng"], target["lat"], target["lng"])
        road_km = round(straight_km * ROAD_FACTOR, 1)
        taxi_fare = round(TAXI_BASE_FARE + max(road_km, TAXI_MIN_FARE_KM) * TAXI_PER_KM)
        result = {
            "from": origin.get("name", "未知"),
            "to": target.get("name", "未知"),
            "straight_km": round(straight_km, 1),
            "road_km": road_km,
            "metro_minutes": int(METRO_ACCESS_MINUTES + road_km / METRO_SPEED_KMH * 60),
            "taxi_minutes": int(TAXI_WAIT_MINUTES + road_km / TAXI_SPEED_KMH * 60),
            "taxi_fare": taxi_fare,
            "walk_minutes": int(road_km / WALK_SPEED_KMH * 60),
        }
        # 短途（≤2 公里）步行即可，不调公交规划（否则出现"地铁 55 分钟到隔壁"的荒谬结果）
        if straight_km <= 2.0:
            walk = max(4, int(road_km / WALK_SPEED_KMH * 60))
            result["metro_minutes"] = walk
            result["taxi_minutes"] = max(6, walk + 3)
            result["taxi_fare"] = TAXI_BASE_FARE
            return result
        real_route = None
        if (
            amap_client.is_ready()
            and origin.get("lat") is not None
            and target.get("lat") is not None
        ):
            real_route = amap_client.route_between(
                f"{origin['lng']},{origin['lat']}",
                f"{target['lng']},{target['lat']}",
                city=(city or "北京").removesuffix("市"),
            )
        if real_route:
            if real_route.get("transit_minutes") is not None:
                result["metro_minutes"] = real_route["transit_minutes"]
            if real_route.get("driving_minutes") is not None:
                result["taxi_minutes"] = real_route["driving_minutes"]
            if real_route.get("distance_km") is not None:
                road_km = real_route["distance_km"]
                result["road_km"] = road_km
                result["taxi_fare"] = round(TAXI_BASE_FARE + max(road_km, TAXI_MIN_FARE_KM) * TAXI_PER_KM)
            result["source"] = "高德路径规划"
        return result

    def recommend_hotel(
        self, budget: int, days: int, intercity_cost: int, travelers: int = 2
    ) -> dict[str, Any]:
        """按预算分档给住宿策略：靠近次日核心景点或地铁沿线。

        分档按"每间每晚可用预算"计算（大交通+餐饮扣减后 ÷ 晚数 ÷ 房间数），
        预算不足以覆盖最低档时强制降为经济型并标注 adjusted，整体导向经济实惠。
        """
        nights = max(1, days - 1)
        rooms = max(1, math.ceil(max(1, travelers) / 2))
        allowance = max(0, budget - intercity_cost - days * MEAL_PER_DAY * max(1, travelers))
        per_room_allowance = allowance / (nights * rooms) if nights and rooms else 0
        chosen = HOTEL_TIERS[0]
        adjusted = True  # 预算连经济型都覆盖不了时也按经济型执行，视为强制降档
        for tier in HOTEL_TIERS:
            if per_room_allowance >= tier["per_night"]:
                chosen = tier
                adjusted = False
        if chosen["tier"] != HOTEL_TIERS[0]["tier"] and per_room_allowance < chosen["per_night"]:
            chosen = HOTEL_TIERS[0]
        return {
            "tier": chosen["tier"],
            "per_night": chosen["per_night"],
            "nights": nights,
            "rooms": rooms,
            "adjusted": adjusted,
            "strategy": "优先选择靠近次日核心景点或地铁沿线的住宿，减少每日通勤消耗。",
            "note": "住宿价格为本地演示分档，非实时房价，不含真实预订。",
        }

    def intercity_advice(self, origin: str | None) -> dict[str, Any] | None:
        if not origin:
            return None
        info = INTERCITY_TABLE.get(origin)
        if info:
            pick = "高铁（时长与准点率更稳）" if info["rail_first"] else "飞机（时长明显更短，提前购票）"
            return {
                "origin": origin,
                "high_speed": info["high_speed"],
                "flight": info["flight"],
                "recommendation": pick,
                "round_trip_cost": info["round_trip_cost"],
            }
        return {
            "origin": origin,
            "high_speed": "视距离而定",
            "flight": "视距离而定",
            "recommendation": "1000 公里内优先高铁，更远优先飞机（通用建议）",
            "round_trip_cost": GENERIC_INTERCITY_COST,
        }

    def weather_notes(self, destination: str | None = None) -> list[str]:
        # 真实模式：高德地理编码 + 和风 3 天预报；任一步失败回退四季演示样例
        if destination and amap_client.is_ready() and qweather_client.is_ready():
            geo = amap_client.geocode(destination)
            if geo:
                daily = qweather_client.weather_3d(f"{geo['lng']},{geo['lat']}")
                if daily:
                    city_label = geo.get("city") or destination
                    notes = [f"未来三天实时预报（和风天气 · {city_label}）："]
                    notes.extend(
                        f"{day['date']}：{day['text_day']}，{day['temp_min']}~{day['temp_max']}℃"
                        for day in daily
                    )
                    return notes
        return list(WEATHER_NOTES)

    def nearby_pois(self, spot: dict[str, Any], kind: str) -> list[dict[str, Any]]:
        """周边服务实时检索：美食/停车场/公共厕所（高德 POI，真实名称与距离）。"""
        query = {"food": {"types": "050000"}, "parking": {"keywords": "停车场"}, "toilet": {"keywords": "公共厕所"}}.get(kind)
        if not query or not amap_client.is_ready() or spot.get("lat") is None:
            return []
        pois = amap_client.around_pois(spot["lng"], spot["lat"], radius=1000, size=8, **query)
        result = [
            {
                "name": poi["name"],
                "kind": kind,
                "distance_m": int(self.haversine_km(spot["lat"], spot["lng"], poi["lat"], poi["lng"]) * 1000),
                "lat": poi["lat"],
                "lng": poi["lng"],
                "address": poi["address"],
                "note": "来源：高德周边检索",
            }
            for poi in pois
        ]
        return sorted(result, key=lambda item: item["distance_m"])

    def comfort_level(self, spot_name: str, day: int) -> str:
        """景区舒适度演示口径：按名称与天数的确定性伪随机，非实时人流。"""
        seed = sum(ord(char) for char in spot_name) + day * 7
        return COMFORT_LEVELS[seed % len(COMFORT_LEVELS)]

    # ---------- 旅行服务大厅（车票/机票/商家/景点/娱乐，竞品形态吸收，演示口径） ----------

    MERCHANT_TEMPLATES = [
        ("前门老字号美食街", "美食", 0.8, "人均 60-120 元", 4.6),
        ("南锣鼓巷文创集市", "文创", 2.5, "小物件 20-150 元", 4.4),
        ("红桥市场 · 珍珠特产", "购物", 3.2, "议价为主", 4.3),
        ("潘家园旧货市场", "购物", 6.0, "周末集市", 4.2),
        ("王府井百货", "购物", 0.5, "人均 100-300 元", 4.1),
        ("五道营胡同咖啡馆群", "休闲", 3.0, "人均 40-80 元", 4.7),
        ("秀水街服装市场", "购物", 1.5, "议价为主", 4.0),
        ("大栅栏商业街", "美食", 0.9, "人均 50-100 元", 4.3),
    ]
    MEAL_RESTAURANT_TEMPLATES = {
        "早餐": [
            ("护国寺小吃", "豆汁/焦圈/糖火烧", "人均 25-45 元"),
            ("锦芳小吃", "面茶/炸糕/包子", "人均 20-40 元"),
            ("庆丰包子铺", "包子/炒肝/粥", "人均 20-35 元"),
            ("姚记炒肝", "炒肝/包子/卤煮", "人均 25-45 元"),
        ],
        "午餐": [
            ("四季民福烤鸭店", "北京烤鸭/京味热菜", "人均 150-220 元"),
            ("局气", "京味创意菜/兔爷土豆泥", "人均 100-160 元"),
            ("小吊梨汤", "梨汤/京味家常菜", "人均 80-130 元"),
            ("紫光园", "清真家常菜/烤鸭", "人均 70-120 元"),
        ],
        "晚餐": [
            ("大董烤鸭店", "烤鸭/精致京菜", "人均 220-350 元"),
            ("便宜坊烤鸭店", "焖炉烤鸭/传统京菜", "人均 120-200 元"),
            ("北平楼", "京味家常菜/炸酱面", "人均 80-140 元"),
            ("南门涮肉", "铜锅涮肉/烧饼", "人均 120-180 元"),
        ],
        "夜宵": [
            ("簋街胡大饭馆", "麻辣小龙虾/夜宵热菜", "人均 130-220 元"),
            ("方砖厂炸酱面", "炸酱面/卤煮小吃", "人均 40-70 元"),
            ("牛街洪记小吃", "清真小吃/牛肉粒", "人均 35-70 元"),
            ("三里屯夜食街", "烧烤/简餐/酒吧小食", "人均 80-160 元"),
        ],
    }
    ENTERTAINMENT_TEMPLATES = [
        ("老舍茶馆 · 京味曲艺演出", "演出", "每晚 19:50", "前门西大街", "票价 180-380 元（演示）"),
        ("朝阳剧场 · 杂技专场", "演出", "每日 17:30 / 19:30", "东三环北路", "票价 180-480 元（演示）"),
        ("什刹海 · 夜游泛舟", "夜游", "18:00-22:00", "荷花市场码头", "船票 80 元/人起（演示）"),
        ("国家大剧院 · 公开排练参观", "文化", "按排期", "西长安街 2 号", "参观票 30-60 元（演示）"),
        ("胡同三轮车 · 文化导览", "体验", "9:00-17:00", "鼓楼东大街集合", "180 元/车（演示）"),
        ("节假日庙会 / 市集", "市集", "节假日限定", "地坛 / 厂甸等", "免费-20 元（演示）"),
    ]

    def _center(self, destination: str) -> dict[str, Any] | None:
        return amap_client.geocode(destination) if amap_client.is_ready() else None

    def attractions(self, destination: str) -> dict[str, Any]:
        """景点实时检索：高德 POI（含静态库票价/时长继承）；未配置密钥时返回空列表。"""
        if amap_client.is_ready():
            spots = ScenicSpotService().recommend(destination, [], limit=12)
            if spots:
                return {
                    "destination": destination,
                    "attractions": [
                        {
                            "name": s["name"],
                            "tags": s["tags"],
                            "open_time": s.get("open_time", "以景区公告为准"),
                            "ticket_price": s.get("ticket_price", 0),
                            "visit_minutes": s.get("visit_minutes", 120),
                        }
                        for s in spots
                    ],
                    "note": "来源：高德实时 POI 检索；门票以现场公示为准。",
                }
        return {
            "destination": destination,
            "attractions": [],
            "note": "景点实时检索未启用（未配置 AMAP_API_KEY），配置后即可获取真实景点。",
        }

    def merchants(self, destination: str) -> dict[str, Any]:
        """周边商家实时检索：市中心 5 公里内的购物/美食 POI。"""
        center = self._center(destination)
        pois = amap_client.around_pois(center["lng"], center["lat"], types="060000|050000", radius=5000, size=8) if center else []
        merchants = []
        for poi in pois:
            parts = [t for t in poi["type"].split(";") if t]
            big = parts[0] if parts else ""
            category = "美食" if big == "餐饮服务" else ("购物" if big == "购物服务" else (parts[1] if len(parts) > 1 else "休闲"))
            merchants.append(
                {
                    "name": poi["name"],
                    "category": category,
                    "distance_km": round(self.haversine_km(center["lat"], center["lng"], poi["lat"], poi["lng"]), 1),
                    "price_hint": "以门店公示为准",
                    "address": poi["address"],
                }
            )
        note = "来源：高德实时 POI 检索；价格以门店公示为准。" if merchants else "商家实时检索未启用（未配置 AMAP_API_KEY）。"
        return {"destination": destination, "merchants": merchants, "note": note}

    def daily_meals(
        self,
        destination: str,
        day: int,
        anchors: dict[str, str | None] | None = None,
        coords: dict[str, tuple[float, float]] | None = None,
    ) -> list[dict[str, str]]:
        anchors = anchors or {}
        seed = sum(ord(char) for char in f"{destination}{''.join(value or '' for value in anchors.values())}") + day
        meal_slots = {
            "早餐": "08:00-08:40",
            "午餐": "12:00-13:00",
            "晚餐": "18:20-19:20",
            "夜宵": "21:30-22:10",
        }
        # 真实模式：高德周边餐饮 POI（按当日午餐锚点坐标搜周边）；失败回退静态模板
        real_pois: list[dict[str, Any]] = []
        if amap_client.is_ready() and coords:
            anchor_coord = coords.get("午餐") or next(iter(coords.values()), None)
            if anchor_coord:
                real_pois = amap_client.around_pois(anchor_coord[0], anchor_coord[1], types="050000", radius=3000, size=8)
        meals = []
        for offset, (meal, restaurants) in enumerate(self.MEAL_RESTAURANT_TEMPLATES.items()):
            anchor_name = anchors.get(meal) or "当日核心景点"
            if real_pois:
                poi = real_pois[(day - 1 + offset) % len(real_pois)]
                name = poi["name"]
                parts = [t for t in (poi["type"] or "").split(";") if t]
                tail = list(dict.fromkeys(parts[1:] or parts))
                signature = " · ".join(tail) if tail else "餐饮"
                price_hint = "以门店公示为准"
                label, source = name, "高德POI"
            else:
                name, signature, price_hint = restaurants[(seed + offset) % len(restaurants)]
                label, source = f"{destination.removesuffix('市')}{name}", ""
            meal_item = {
                "time": meal_slots[meal],
                "title": f"{meal}推荐｜{label}",
                "meal": meal,
                "restaurant": label,
                "signature": signature,
                "price_hint": price_hint,
                "location_hint": f"建议安排在{anchor_name}周边或顺路地铁站附近",
                "note": "出发前请二次确认营业状态。"
                if not source
                else "来源：高德周边检索；营业状态请出发前二次确认。",
            }
            if source:
                meal_item["source"] = source
            meals.append(meal_item)
        return meals

    def entertainment(self, destination: str) -> dict[str, Any]:
        """娱乐/演出实时检索：市中心周边剧场、电影院、夜市等真实场馆。"""
        center = self._center(destination)
        pois = (
            amap_client.around_pois(center["lng"], center["lat"], keywords="剧场|电影院|音乐厅|夜市", radius=5000, size=8)
            if center
            else []
        )
        entertainments = [
            {
                "name": poi["name"],
                "type": " · ".join(list(dict.fromkeys(t for t in poi["type"].split(";") if t))[1:]) or "休闲",
                "time": "以场馆公告为准",
                "location": poi["address"],
                "price": "以现场公示为准",
            }
            for poi in pois
        ]
        note = "来源：高德实时检索；排期与票价以场馆现场公示为准。" if entertainments else "娱乐检索未启用（未配置 AMAP_API_KEY）。"
        return {"destination": destination, "entertainments": entertainments, "note": note}

    @staticmethod
    def _hotel_category(name: str, poi_type: str) -> str:
        """按名称与 POI 类型把酒店归入 高档酒店 / 酒店 / 民宿公寓 / 商务配套。"""
        if any(k in name for k in ("国际大酒店", "香格里拉", "豪华", "五星", "万豪", "瑞吉", "洲际")):
            return "高档酒店"
        if any(k in name or k in poi_type for k in ("公寓", "民宿", "拾居")):
            return "民宿公寓"
        if any(k in name for k in ("贵宾", "会所", "俱乐部", "商务配套")):
            return "商务配套"
        return "酒店"

    def hotels(self, destination: str, nights: int = 1) -> dict[str, Any]:
        """住宿实时检索：真实酒店名称/位置/坐标，按类型分类，不生成虚拟房价。"""
        center = self._center(destination)
        pois = amap_client.around_pois(center["lng"], center["lat"], types="100000", radius=5000, size=8) if center else []
        hotels = []
        for poi in pois:
            hotels.append(
                {
                    "name": poi["name"],
                    "category": self._hotel_category(poi["name"], poi["type"]),
                    "tier": (poi["type"].split(";")[1:2] or ["宾馆"])[0],
                    "position": poi["address"],
                    "lat": poi["lat"],
                    "lng": poi["lng"],
                    "distance_km": round(self.haversine_km(center["lat"], center["lng"], poi["lat"], poi["lng"]), 1) if center else 0,
                    "nights": nights,
                    "source": "高德实时检索",
                }
            )
        note = "来源：高德实时检索；房价与房态以各预订平台实时公示为准，本系统不生成虚拟房价。" if hotels else "住宿检索未启用（未配置 AMAP_API_KEY）。"
        return {"kind": "hotel", "hotels": hotels, "note": note}

    @staticmethod
    def _budget_hotel_category(tier: str) -> str:
        """预算档位 → 酒店类别：品质型优先高档酒店，舒适型对应标准酒店，经济型对应民宿公寓。"""
        return {"品质型": "高档酒店", "舒适型": "酒店", "经济型": "民宿公寓"}.get(tier, "酒店")

    def recommend_hotel_poi(
        self,
        destination: str,
        budget: int | None = None,
        days: int = 3,
        origin: str | None = None,
    ) -> dict[str, Any] | None:
        """推荐住宿：按预算分档匹配酒店类别（与 Validator 的住宿分档口径一致），返回匹配类别中最近市中心的一家。

        返回值附带 matched_tier / matched_per_night 供行程书展示匹配依据；无预算或类别无匹配时回退第一家。
        """
        hotels = self.hotels(destination).get("hotels", [])
        if not hotels:
            return None
        if budget:
            advice = self.intercity_advice(origin)
            intercity_cost = advice["round_trip_cost"] if advice else 0
            tier_info = self.recommend_hotel(budget, days, intercity_cost)
            category = self._budget_hotel_category(tier_info["tier"])
            matched = [h for h in hotels if h["category"] == category] or hotels
            pick = dict(matched[0])
            pick["matched_tier"] = tier_info["tier"]
            pick["matched_per_night"] = tier_info["per_night"]
            return pick
        return hotels[0]

    def train_tickets(self, origin: str | None, destination: str) -> dict[str, Any]:
        """大交通指引：无合规票务数据源，不生成虚拟班次，提供决策建议与官方渠道。"""
        advice = self.intercity_advice(origin)
        guide = {
            "route": f"{origin or '出发地未填'} → {destination}",
            "advice": advice["recommendation"] if advice else "填写出发地后可获得高铁/飞机决策建议。",
            "channels": [
                {"name": "12306 官方", "desc": "火车票实时查询与购票", "url": "https://www.12306.cn"},
            ],
        }
        return {"kind": "train", "tickets": [], "guide": guide, "note": "不提供虚拟班次与票价；实时车次请通过官方渠道查询。"}

    def flights(self, origin: str | None, destination: str) -> dict[str, Any]:
        """机票指引：不生成虚拟航班，提供决策建议与官方渠道。"""
        advice = self.intercity_advice(origin)
        guide = {
            "route": f"{origin or '出发地未填'} → {destination}",
            "advice": f"飞行时长参考：{advice['flight']}。{advice['recommendation']}" if advice else "填写出发地后可获得决策建议。",
            "channels": [
                {"name": "航司官网", "desc": "国航/东航/南航等官网或持牌平台查询实时报价", "url": ""},
            ],
        }
        return {"kind": "flight", "flights": [], "guide": guide, "note": "不提供虚拟航班与票价；实时航班请通过航司官网或持牌平台查询。"}

    def budget_breakdown(
        self,
        *,
        destination: str,
        days: int,
        selected_spots: list[dict[str, Any]],
        legs: list[dict[str, Any]],
        intercity_cost: int,
        hotel_per_night: int,
        hotel_nights: int,
        travelers: int = 1,
    ) -> dict[str, Any]:
        travelers = max(1, travelers)
        rooms = max(1, math.ceil(travelers / 2))  # 住宿按每 2 人一间
        vehicles = max(1, math.ceil(travelers / 3))  # 市内打车按每 3 人一车拼车
        tickets = sum(spot.get("ticket_price", 0) for spot in selected_spots) * travelers
        local_transport = sum(leg["taxi_fare"] for leg in legs) * vehicles
        meals = days * MEAL_PER_DAY * travelers
        hotel = hotel_per_night * hotel_nights * rooms
        intercity = intercity_cost * travelers
        total = tickets + local_transport + meals + hotel + intercity
        return {
            "intercity": intercity,
            "hotel": hotel,
            "local_transport": local_transport,
            "tickets": tickets,
            "meals": meals,
            "total": total,
            "travelers": travelers,
            "note": (
                "分项口径：门票按公示/静态价目与大交通按人数计，餐饮按每天 150 元/人，"
                "市内交通按高德打车时长估算并按每 3 人一车拼车，住宿按每 2 人一间预算分档。"
            ),
        }
