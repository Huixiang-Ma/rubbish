from typing import Any

from app.agents.base import AgentBase, get_budget_payload


class DebateAgent(AgentBase):
    """C2 辩论式可解释：对行程关键取舍生成规划方/游客方论点与最终结论。

    事实全部取自前序 Agent 的结构化输出（选了什么、放弃了什么、预算数字、校验结论）。
    解释层走确定性模板（内容是事实的纯推导，无需大模型），保证零延迟与结果稳定；
    LLM 已上移到 Planner 决策层，负责真正的行程编排。
    """

    name = "Debate"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": self.name,
            "status": "ok",
            "payload": {
                "debates": self._mock_debates(context),
                "mode": "template",
            },
        }

    def _facts(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        outputs = context["outputs"]
        selected = [
            item["spot"].get("name", item["title"])
            for day in outputs["Itinerary"]["payload"]["itinerary"]
            for item in day["items"]
        ]
        candidates = [spot["name"] for spot in outputs["Researcher"]["payload"]["spots"]]
        dropped = [name for name in candidates if name not in selected]
        budget = get_budget_payload(outputs)
        return {
            "destination": user_input["destination"],
            "days": user_input["days"],
            "budget": user_input["budget"],
            "preferences": user_input.get("preferences", []),
            "constraints": user_input.get("constraints", []),
            "selected_spots": selected,
            "dropped_candidates": dropped[:4],
            "estimated_budget": budget.get("estimated_budget") or 0,
            "findings": [
                {"level": f["level"], "type": f["type"], "message": f["message"]}
                for f in outputs["Validator"]["payload"].get("findings", [])[:4]
            ],
        }

    @staticmethod
    def _valid_debate(debate: Any) -> bool:
        def _side(side: Any) -> bool:
            return (
                isinstance(side, dict)
                and isinstance(side.get("role"), str)
                and isinstance(side.get("point"), str)
                and bool(side.get("point", "").strip())
            )

        verdict = debate.get("verdict") if isinstance(debate, dict) else None
        return (
            isinstance(debate, dict)
            and isinstance(debate.get("topic"), str)
            and bool(debate.get("topic", "").strip())
            and _side(debate.get("plan_side"))
            and _side(debate.get("traveler_side"))
            and isinstance(verdict, dict)
            and isinstance(verdict.get("decision"), str)
            and isinstance(verdict.get("reason"), str)
        )

    def _mock_debates(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        facts = self._facts(context)
        first = facts["selected_spots"][0] if facts["selected_spots"] else "核心景点"
        alternative = facts["dropped_candidates"][0] if facts["dropped_candidates"] else "备选景点"
        findings_text = "；".join(f["message"] for f in facts["findings"]) or "暂无高风险冲突"
        over_budget = facts["estimated_budget"] > facts["budget"]
        budget_line = (
            f"预估预算 {facts['estimated_budget']} 元，超出用户预算 {facts['budget']} 元。"
            if over_budget
            else f"预估预算 {facts['estimated_budget']} 元，在用户预算 {facts['budget']} 元内。"
        )
        return [
            {
                "topic": f"为什么主推「{first}」而不是「{alternative}」",
                "plan_side": {
                    "role": "规划方 Agent",
                    "point": (
                        f"「{first}」与用户偏好（{', '.join(facts['preferences']) or '通用'}）匹配度更高，"
                        "开放时间与当日动线更稳，作为核心景点的确定性最高。"
                    ),
                },
                "traveler_side": {
                    "role": "游客方 Agent",
                    "point": f"「{alternative}」在候选中同样有吸引力，希望列为弹性备选，避免行程千篇一律。",
                },
                "verdict": {
                    "decision": f"当天主推「{first}」，「{alternative}」列为备选",
                    "reason": "先保证可达性与体验确定性，把替换空间留给现场弹性。",
                },
            },
            {
                "topic": "行程强度：多排景点还是留白",
                "plan_side": {
                    "role": "规划方 Agent",
                    "point": f"校验结论：{findings_text}。按当前节奏执行的确定性更高。",
                },
                "traveler_side": {
                    "role": "游客方 Agent",
                    "point": "希望每天留出自由支配时间，逛街或临时加项都更从容。",
                },
                "verdict": {
                    "decision": "维持当前每日节奏",
                    "reason": "以校验结果为准控制强度，把留白时间放在每日晚间弹性段。",
                },
            },
            {
                "topic": "预算分配：花在核心体验还是均匀摊开",
                "plan_side": {
                    "role": "规划方 Agent",
                    "point": budget_line + ("建议压缩交通与餐饮标准后复核。" if over_budget else "可向核心体验适度倾斜。"),
                },
                "traveler_side": {
                    "role": "游客方 Agent",
                    "point": "把钱花在最想去的 1-2 个核心体验上，其余项目从简。",
                },
                "verdict": {
                    "decision": "核心体验优先，其余从简" if not over_budget else "先压缩交通与餐饮标准，超支部分走人工审批",
                    "reason": "预算约束下优先保障核心景点体验，冲突时交给 HITL 审批兜底。",
                },
            },
        ]
