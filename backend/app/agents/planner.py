import json
import math
from typing import Any

from app.agents.base import AgentBase
from app.services.llm_client import LLMClient

CLUSTER_RADIUS_KM = 5.0  # 同一地理簇的半径：簇内景点彼此步行/短途可达


def _cluster_areas(spots: list[dict[str, Any]]) -> dict[str, str]:
    """按坐标把景点贪心聚成地理簇（≤5km），返回 name → 区域标签（如"城东A区"）。

    LLM 对坐标距离不敏感，给出区域标签后"同天景点彼此相邻"才可执行。
    """
    areas: dict[str, str] = {}
    clusters: list[dict[str, Any]] = []
    directions = ["东", "东南", "南", "西南", "西", "西北", "北", "东北"]
    for spot in spots:
        if spot.get("lat") is None or spot.get("lng") is None:
            continue
        lat, lng = float(spot["lat"]), float(spot["lng"])
        for cluster in clusters:
            dlat = (cluster["lat"] - lat) * 111.0
            dlng = (cluster["lng"] - lng) * 111.0 * math.cos(math.radians(lat))
            if math.sqrt(dlat**2 + dlng**2) <= CLUSTER_RADIUS_KM:
                cluster["count"] += 1
                areas[spot["name"]] = cluster["label"]
                break
        else:
            angle = (math.degrees(math.atan2(lng - 116.0, lat - 34.0)) + 360) % 360
            label = f"城{directions[int(angle / 45) % 8]}{chr(ord('A') + len(clusters) % 26)}区"
            clusters.append({"lat": lat, "lng": lng, "count": 1, "label": label})
            areas[spot["name"]] = label
    return areas


class PlannerAgent(AgentBase):
    """规划决策 Agent：大模型基于实时数据做"选景点/分天/编排"，规则切片作为兜底。

    LLM 输出严格校验（天数/景点白名单/不跨天重复/单日≤3 个），任何违规回退规则编排，
    保证坏输出不会进入下游（Itinerary/Validator 依赖稳定结构）。
    """

    name = "Planner"
    MAX_SPOTS_PER_DAY = 3

    def __init__(self) -> None:
        self.llm = LLMClient()

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        spots = context["outputs"]["Researcher"]["payload"]["spots"]
        constraints = user_input.get("constraints", []) or []
        max_per_day = 2 if any("不要太赶" in c or "轻松" in c for c in constraints) else self.MAX_SPOTS_PER_DAY
        llm_days = self._llm_plan(user_input, spots)
        days = llm_days if llm_days is not None else self._rule_days(user_input, spots, max_per_day)
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "days": days,
                "budget": user_input["budget"],
                "mode": "llm" if llm_days is not None else "rule",
            },
        }

    def _rule_days(
        self, user_input: dict[str, Any], spots: list[dict[str, Any]], max_per_day: int | None = None
    ) -> list[dict[str, Any]]:
        """规则编排兜底：经济实惠导向（免费/低价优先），按每日上限切片分天。"""
        limit = max_per_day or self.MAX_SPOTS_PER_DAY
        ordered = sorted(spots, key=lambda spot: spot.get("ticket_price", 0))
        days = []
        per_day = max(1, min(limit, len(ordered) // user_input["days"] or 1))
        themes = ["历史文化经典线", "城市漫步体验线", "亲子休闲美食线", "自然风景放松线"]
        for day in range(1, user_input["days"] + 1):
            start = (day - 1) * per_day
            selected = ordered[start : start + per_day]
            if not selected:
                selected = ordered[:per_day]
            days.append(
                {
                    "day": day,
                    "theme": themes[(day - 1) % len(themes)],
                    "spot_names": [spot["name"] for spot in selected],
                    "reason": "按经济实惠导向（免费/低价优先）与每日强度分配。",
                }
            )
        return days

    def _llm_plan(self, user_input: dict[str, Any], spots: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        """大模型编排：输入实时景点事实与用户需求，输出每日分组；任何校验不过返回 None（走规则兜底）。"""
        if self.llm.mode != "real" or not spots:
            return None
        valid_names = [spot["name"] for spot in spots]
        facts = [
            {
                "name": spot.get("name", ""),
                "tags": spot.get("tags", []),
                "ticket_price": spot.get("ticket_price", 0),
                "visit_minutes": spot.get("visit_minutes", 120),
            }
            for spot in spots
        ]
        preferences = user_input.get("preferences", []) or []
        constraints = user_input.get("constraints", []) or []
        travelers = user_input.get("travelers", 2)
        per_person_budget = int(user_input["budget"] / max(1, travelers))
        max_per_day = 2 if any("不要太赶" in c or "轻松" in c for c in constraints) else self.MAX_SPOTS_PER_DAY
        areas = _cluster_areas(spots)
        facts = [
            {
                "name": spot.get("name", ""),
                "area": areas.get(spot.get("name", ""), ""),
                "tags": spot.get("tags", []),
                "ticket_price": spot.get("ticket_price", 0),
                "visit_minutes": spot.get("visit_minutes", 120),
            }
            for spot in spots
        ]
        prompt = (
            f"你是行程编排师，为用户编排一趟经济实惠、安排合理、体验感好的旅行。目的地 {user_input['destination']}，"
            f"共 {user_input['days']} 天，{travelers} 人出行，总预算 {user_input['budget']} 元（人均约 {per_person_budget} 元，含交通住宿餐饮门票）。\n"
            f"用户偏好：{preferences or ['未填写']}；用户约束：{constraints or ['未填写']}。\n"
            "编排要求：\n"
            "1. 地理跨度约束（最重要）：area 相同的景点彼此相邻，必须优先安排在同一天；"
            "同一天只允许出现同一个 area（若当日景点不足，可从相邻 area 补 1 个），严禁同天跨区往返；\n"
            "2. 严格贴合用户偏好：选点与 theme 优先匹配偏好标签（如偏好博物馆则优先博物馆类景点）；\n"
            "3. 经济实惠且体验感好：优先免费/低门票景点填充行程，但每天保留 1 个最符合偏好、最具代表性的核心景点作为体验亮点"
            "（收费景点每天至多 1 个）；整趟门票总额控制在预算的 15% 以内；\n"
            "4. 约束优先：若约束含「不要太赶/轻松」则每天不超过 "
            f"{max_per_day} 个景点；含「避免早起」则当天首站选开放晚、无需预约的景点。\n"
            f'输出 JSON {{"days": [{{"day": int, "theme": str, "spot_names": [str]}}]}}，要求：'
            f"恰好 {user_input['days']} 天；每天 1-{max_per_day} 个景点；景点只能从候选清单选择且不跨天重复；theme 不超过 8 个字。\n"
            "候选景点事实（名称/地理区域/标签/门票元/建议游览分钟）：" + json.dumps(facts, ensure_ascii=False)
        )
        result = self.llm.try_generate_json(prompt)
        return self._validate_plan(result, user_input["days"], valid_names, max_per_day)

    def _validate_plan(
        self,
        result: Any,
        expected_days: int,
        valid_names: list[str],
        max_per_day: int | None = None,
    ) -> list[dict[str, Any]] | None:
        if not isinstance(result, dict) or not isinstance(result.get("days"), list):
            return None
        limit = max_per_day or self.MAX_SPOTS_PER_DAY
        days_raw = result["days"]
        if len(days_raw) != expected_days:
            return None
        themes = ["历史文化经典线", "城市漫步体验线", "亲子休闲美食线", "自然风景放松线"]
        seen: set[str] = set()
        days: list[dict[str, Any]] = []
        for index, item in enumerate(days_raw):
            if not isinstance(item, dict):
                return None
            spot_names = item.get("spot_names")
            if not isinstance(spot_names, list) or not (1 <= len(spot_names) <= limit):
                return None
            if any(not isinstance(name, str) or name not in valid_names for name in spot_names):
                return None
            if any(name in seen for name in spot_names):
                return None
            seen.update(spot_names)
            theme = item.get("theme")
            days.append(
                {
                    "day": index + 1,
                    "theme": theme if isinstance(theme, str) and theme.strip() else themes[index % len(themes)],
                    "spot_names": spot_names,
                    "reason": "由大模型基于实时数据与偏好约束编排。",
                }
            )
        return days
