from typing import Any

from app.agents.base import AgentBase, get_budget_payload


class ComplianceAgent(AgentBase):
    """toB 合规审计：汇总校验结论、风险清单与数据口径声明，供管理层/审计视图使用。"""

    name = "Compliance"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        outputs = context["outputs"]
        validation = outputs["Validator"]["payload"]
        tenant = user_input.get("tenant") or "default"
        estimated = get_budget_payload(outputs).get("estimated_budget") or validation.get("estimated_budget", 0)
        budget = user_input["budget"]
        summary = (
            f"租户 {tenant} 的方案已完成结构化校验：预估花费 {estimated} 元"
            + ("，在客户预算内。" if estimated <= budget else "，超出客户预算，需留审批记录。")
        )
        risks = [
            {"scene": item["scene"], "plan_b": item["plan_b"]}
            for item in validation.get("what_if", [])
        ]
        data_declarations = [
            "通勤时长/费用、住宿分档、大交通为估算口径，非实时报价；天气为和风实时预报。",
            "门票与景点数据来自静态库与高德实时检索；数据源接入边界见 api_registry 配置中心。",
            "travel_plan.md 是展示与导出产物，任务状态以 state.json 与审计日志为准。",
        ]
        approval_suggestion = (
            "本单未触发预算挂起，可直接交付。"
            if not validation.get("approval_required")
            else "本单预估超预算，请确认 HITL 审批记录后再交付。"
        )
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "tenant": tenant,
                "summary": summary,
                "risks": risks,
                "data_declarations": data_declarations,
                "approval_suggestion": approval_suggestion,
            },
        }
