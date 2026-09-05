"""Budget Agent：预算分项、经济口径与挂起判定（从 Validator 拆出，字段名保持不变）。

输出字段与原 Validator 预算部分完全同名：estimated_budget / budget_breakdown /
approval_required / economy_total / travel_advice / economy_tips / what_if（预算相关条目）。
下游（Reporter/挂起逻辑/前端）无需改动；旧任务无 Budget 输出时读取侧用 .get 兜底。
"""
from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase
from app.services.travel_context_service import TravelContextService


class BudgetAgent(AgentBase):
    name = "Budget"

    def __init__(self) -> None:
        self.travel = TravelContextService()

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        outputs = context["outputs"]
        itinerary = outputs["Itinerary"]["payload"]["itinerary"]
        findings = outputs.get("Validator", {}).get("payload", {}).get("findings", [])

        breakdown = self._budget_breakdown(context, itinerary)
        if breakdown["total"] > user_input["budget"]:
            pass  # 超预算提示由 Validator 的 findings 承载（budget_exceeded），此处只算账
        status = "needs_review" if breakdown["total"] > user_input["budget"] else "ok"
        hotel_advice = self._travel_advice(user_input, breakdown)
        economy_total = self._economy_total(user_input, breakdown, hotel_advice["hotel"])
        # 经济实惠导向：标准口径超预算但经济口径能压回预算内时，不阻塞审批，按经济口径交付
        approval_required = breakdown["total"] > user_input["budget"] and economy_total > user_input["budget"]
        return {
            "agent": self.name,
            "status": status,
            "payload": {
                "estimated_budget": breakdown["total"],
                "budget_breakdown": breakdown,
                "approval_required": approval_required,
                "economy_total": economy_total,
                "travel_advice": hotel_advice,
                "economy_tips": self._economy_tips(user_input, breakdown, hotel_advice["hotel"], economy_total),
                "what_if": self._what_if(context, itinerary, breakdown, findings),
            },
        }

    def _economy_total(
        self, user_input: dict[str, Any], breakdown: dict[str, Any], hotel: dict[str, Any]
    ) -> int:
        """经济口径：经济住宿（300 元/间/晚）+ 人均 100 元/天餐饮 + 市内交通减半。"""
        economy_hotel = 300 * hotel["nights"] * max(1, hotel.get("rooms", 1))
        economy_meal = 100 * user_input["days"] * max(1, user_input.get("travelers", 2))
        return (
            breakdown["intercity"]
            + economy_hotel
            + round(breakdown["local_transport"] * 0.5)
            + breakdown["tickets"]
            + economy_meal
        )

    def _budget_breakdown(self, context: dict[str, Any], itinerary: list[dict[str, Any]]) -> dict[str, Any]:
        user_input = context["user_input"]
        outputs = context["outputs"]
        selected_spots = [item["spot"] for day in itinerary for item in day["items"] if item["spot"].get("lat")]
        advice = self.travel.intercity_advice(user_input.get("origin"))
        intercity_cost = advice["round_trip_cost"] if advice else 0
        hotel = self.travel.recommend_hotel(
            user_input["budget"], user_input["days"], intercity_cost, user_input.get("travelers", 2)
        )
        return self.travel.budget_breakdown(
            destination=user_input["destination"],
            days=user_input["days"],
            selected_spots=selected_spots,
            legs=outputs["Itinerary"]["payload"].get("legs", []),
            intercity_cost=intercity_cost,
            hotel_per_night=hotel["per_night"],
            hotel_nights=hotel["nights"],
            travelers=user_input.get("travelers", 2),
        )

    def _travel_advice(self, user_input: dict[str, Any], breakdown: dict[str, Any]) -> dict[str, Any]:
        advice = self.travel.intercity_advice(user_input.get("origin"))
        hotel = self.travel.recommend_hotel(
            user_input["budget"], user_input["days"], advice["round_trip_cost"] if advice else 0,
            user_input.get("travelers", 2),
        )
        return {
            "intercity": advice,
            "hotel": hotel,
            "weather_notes": self.travel.weather_notes(user_input.get("destination")),
        }

    def _economy_tips(
        self,
        user_input: dict[str, Any],
        breakdown: dict[str, Any],
        hotel: dict[str, Any],
        economy_total: int,
    ) -> list[str]:
        """经济实惠导向：超预算时给出可执行的压缩建议与降档后预估，默认口径即经济实惠。"""
        tips: list[str] = []
        over = breakdown["total"] - user_input["budget"]
        if over > 0:
            tips.append(
                f"标准口径估算 {breakdown['total']} 元，超出预算 {over} 元；已按「经济实惠」导向给出以下压缩建议。"
            )
            if hotel.get("adjusted"):
                tips.append(
                    f"住宿已降档为{hotel['tier']}档（约 {hotel['per_night']} 元/晚 × {hotel['nights']} 晚 × {hotel.get('rooms', 1)} 间），比高档组合省出一半以上住宿开销。"
                )
            economy_meal = 100 * user_input["days"] * max(1, user_input.get("travelers", 2))
            saved_meal = breakdown["meals"] - economy_meal
            if saved_meal > 0:
                tips.append(
                    f"餐饮按人均 100 元/天（本地小吃+家常菜）口径约 {economy_meal} 元，比标准口径省约 {saved_meal} 元；早餐尽量在住宿周边解决。"
                )
            tips.append("市内交通优先地铁/公交（费用约为打车的 1/3），仅夜间或无地铁段打车。")
            tips.append("门票优先免费景点（博物馆/公园/历史街区多免费预约），收费景点按「必去 1 个 + 备选免费」组合控制门票开销。")
            economy_hotel = 300 * hotel["nights"] * max(1, hotel.get("rooms", 1))
            economy_total = (
                breakdown["intercity"]
                + economy_hotel
                + round(breakdown["local_transport"] * 0.5)
                + breakdown["tickets"]
                + economy_meal
            )
            tips.append(
                f"按经济口径重估约 {economy_total} 元（经济住宿 {economy_hotel} + 餐饮 {economy_meal} + 市内交通减半），{'已落入预算内，本方案已按经济口径编排交付。' if economy_total <= user_input['budget'] else '仍超预算，建议减少 1 天或改选免费景点组合。'}"
            )
        else:
            tips.append("当前方案已在预算内，整体按经济实惠口径编排：住宿中低档、地铁公交为主、兼顾免费景点。")
        return tips

    def _what_if(
        self,
        context: dict[str, Any],
        itinerary: list[dict[str, Any]],
        breakdown: dict[str, Any],
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """预算相关翻车预演（时空类条目仍在 Validator 的 what_if 中，Reporter 两处合并）。"""
        user_input = context["user_input"]
        entries: list[dict[str, Any]] = []
        if breakdown["total"] > user_input["budget"]:
            entries.append(
                {
                    "scene": f"预算超支：分项估算 {breakdown['total']} 元超出预算 {user_input['budget']} 元",
                    "risk": "行程无法按当前标准执行。",
                    "plan_b": "进入人工预算审批（HITL）确认超支，或降档住宿/餐饮标准后重算。",
                }
            )
        return entries
