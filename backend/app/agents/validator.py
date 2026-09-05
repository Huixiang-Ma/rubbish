from typing import Any

from app.agents.base import AgentBase
from app.services.travel_context_service import (
    DAY_COMMUTE_HIGH_MINUTES,
    LEG_TAXI_HIGH_MINUTES,
    TravelContextService,
)


class ValidatorAgent(AgentBase):
    name = "Validator"

    def __init__(self) -> None:
        self.travel = TravelContextService()

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        outputs = context["outputs"]
        itinerary = outputs["Itinerary"]["payload"]["itinerary"]
        findings: list[dict[str, Any]] = []

        for day in itinerary:
            if len(day["items"]) > 3:
                findings.append(
                    {
                        "type": "intensity_warning",
                        "level": "medium",
                        "message": f"第 {day['day']} 天景点数量偏多。",
                        "suggestion": "建议减少一个景点或延长停留天数。",
                    }
                )
            items = day["items"]
            for prev, nxt in zip(items, items[1:]):
                if prev["spot"].get("lat") is None or nxt["spot"].get("lat") is None:
                    continue
                spread_km = self.travel.haversine_km(
                    prev["spot"]["lat"], prev["spot"]["lng"], nxt["spot"]["lat"], nxt["spot"]["lng"]
                )
                if spread_km > 15:
                    findings.append(
                        {
                            "type": "spatial_spread",
                            "level": "medium",
                            "message": (
                                f"第 {day['day']} 天「{prev['spot']['name']}」与「{nxt['spot']['name']}」"
                                f"相距约 {spread_km:.0f} 公里，同日往返地理跨度过大。"
                            ),
                            "suggestion": f"将「{nxt['spot']['name']}」替换为同区域景点，或拆分到相邻日期。",
                        }
                    )
            max_leg = day.get("max_leg")
            if max_leg and max_leg["taxi_minutes"] > LEG_TAXI_HIGH_MINUTES:
                findings.append(
                    {
                        "type": "spatial_conflict",
                        "level": "high",
                        "message": (
                            f"{max_leg['from']}与{max_leg['to']}同日通勤过长："
                            f"路网约 {max_leg['road_km']} 公里，打车估算 {max_leg['taxi_minutes']} 分钟。"
                        ),
                        "suggestion": f"将{max_leg['to']}拆分到单独一天，或当日只保留远郊一地。",
                    }
                )
            commute_minutes = day.get("commute_minutes") or 0
            if commute_minutes > DAY_COMMUTE_HIGH_MINUTES:
                findings.append(
                    {
                        "type": "commute_overload",
                        "level": "medium",
                        "message": f"第 {day['day']} 天全天通勤估算 {commute_minutes} 分钟，占用游览时间过长。",
                        "suggestion": "合并同区域景点，或减少当日跨区移动。",
                    }
                )

        # 预算分项/经济口径/挂起判定已拆分到独立 BudgetAgent（管线：… Itinerary → Budget → Validator …）；
        # 本节点只做时空与强度校验，保证单一职责。
        budget_payload = outputs.get("Budget", {}).get("payload", {})
        if budget_payload.get("budget_breakdown", {}).get("total", 0) > user_input["budget"]:
            findings.append(
                {
                    "type": "budget_exceeded",
                    "level": "high",
                    "message": (
                        f"分项估算合计 {budget_payload['budget_breakdown']['total']} 元超过用户预算 {user_input['budget']} 元"
                        f"（大交通 {budget_payload['budget_breakdown']['intercity']} / 住宿 {budget_payload['budget_breakdown']['hotel']} / "
                        f"市内交通 {budget_payload['budget_breakdown']['local_transport']} / 门票 {budget_payload['budget_breakdown']['tickets']} / 餐饮 {budget_payload['budget_breakdown']['meals']}）。"
                    ),
                    "suggestion": "进入人工预算审批，或降低交通与住宿标准后重规划。",
                }
            )

        status = "needs_review" if any(item["level"] == "high" for item in findings) else "ok"
        return {
            "agent": self.name,
            "status": status,
            "payload": {
                "findings": findings,
                "what_if": self._what_if(context, itinerary, findings),
            },
        }





    def _what_if(
        self,
        context: dict[str, Any],
        itinerary: list[dict[str, Any]],
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for finding in findings:
            if finding.get("type") == "spatial_spread":
                entries.append(
                    {
                        "scene": finding["message"],
                        "risk": "同日跨区往返通勤时间与费用翻倍，挤压游览体验。",
                        "plan_b": finding["suggestion"],
                    }
                )
        legs = [leg for leg in context["outputs"]["Itinerary"]["payload"].get("legs", []) if leg["taxi_minutes"]]
        worst_leg = max(legs, key=lambda leg: leg["taxi_minutes"]) if legs else None
        entries.append(
            {
                "scene": "恶劣天气（暴雨/大风/高温）",
                "risk": "户外景点体验差，山区景点可能临时封闭。",
                "plan_b": "把当日露天景点与室内场馆（博物馆类）顺序互换，优先保证室内游览。",
            }
        )
        if worst_leg:
            entries.append(
                {
                    "scene": f"通勤超时：{worst_leg['from']}→{worst_leg['to']} 打车估算 {worst_leg['taxi_minutes']} 分钟",
                    "risk": "当日行程整体后移，可能错过后续预约时段。",
                    "plan_b": "提前一小时出发、优先地铁，或删减当日最后一个景点。",
                }
            )
        selected = {item["spot"].get("name") for day in itinerary for item in day["items"]}
        dropped = [
            spot["name"]
            for spot in context["outputs"]["Researcher"]["payload"]["spots"]
            if spot["name"] not in selected
        ]
        substitute = dropped[0] if dropped else "同区域备选景点"
        entries.append(
            {
                "scene": "热门场馆约满或临时闭馆（如故宫需提前预约）",
                "risk": "当日核心景点无法进入，行程出现空档。",
                "plan_b": f"启用候选替补「{substitute}」，或与次日行程对调。",
            }
        )
        return entries
