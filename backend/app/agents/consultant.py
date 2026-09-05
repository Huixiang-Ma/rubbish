from typing import Any

from app.agents.base import AgentBase, get_budget_payload


class ConsultantAgent(AgentBase):
    """toB 顾问助手：把校验后的方案转成顾问对客户的话术、分项报价口径与跟进建议。"""

    name = "Consultant"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        outputs = context["outputs"]
        validation = outputs["Validator"]["payload"]
        itinerary = outputs["Itinerary"]["payload"]["itinerary"]
        customer = user_input.get("customer") or "客户"
        days = user_input["days"]
        estimated = get_budget_payload(outputs).get("estimated_budget") or validation.get("estimated_budget", 0)
        budget = user_input["budget"]
        budget_line = (
            f"预估花费 {estimated} 元，在您 {budget} 元预算内。"
            if estimated <= budget
            else f"预估花费 {estimated} 元，略超 {budget} 元预算，可按分项调档后再确认。"
        )
        themes = "、".join(f"Day{day['day']} {day['theme']}" for day in itinerary)
        breakdown = get_budget_payload(outputs).get("budget_breakdown") or validation.get("budget_breakdown", {})
        quotation = (
            f"大交通 {breakdown.get('intercity', 0)} 元｜住宿 {breakdown.get('hotel', 0)} 元｜"
            f"市内交通 {breakdown.get('local_transport', 0)} 元｜门票 {breakdown.get('tickets', 0)} 元｜"
            f"餐饮 {breakdown.get('meals', 0)} 元（按分项口径估算）"
        )
        talking_points = [
            f"行程结构：{days} 天覆盖 {themes}，节奏与{customer}的偏好匹配。",
            f"费用结论：{budget_line}",
            f"分项报价：{quotation}",
            "核心体验：首日安排确定性最高的核心景点，替换空间留给现场弹性。",
        ]
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "customer": customer,
                "talking_points": talking_points,
                "quotation_note": quotation,
                "follow_up": f"建议 3 日内向{customer}回访，确认出发日期与住宿档次后锁定方案。",
            },
        }
