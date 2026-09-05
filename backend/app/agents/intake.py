"""Intake Agent：输入规范化（对齐 8 Agent 清单的偏好解析落点）。

在管线最前统一做归一化：目的地去"市"后缀、travelers 缺省、偏好/约束去重、
交通优先类约束解析为 parsed_flags。后续节点消费规范化输入；原始输入保留在 state 用于展示。
"""
from __future__ import annotations

from typing import Any

from app.agents.base import AgentBase

_TRANSIT_FIRST_KEYWORDS = ("减少打车", "优先地铁", "经济实惠")


class IntakeAgent(AgentBase):
    name = "Intake"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        user_input = context["user_input"]
        destination = str(user_input.get("destination", "")).strip().removesuffix("市")
        days = int(user_input.get("days") or 3)
        days = min(14, max(1, days))
        budget = int(user_input.get("budget") or 0)
        travelers = int(user_input.get("travelers") or 2) or 2

        preferences = list(dict.fromkeys(str(item).strip() for item in user_input.get("preferences", []) if str(item).strip()))
        constraints = list(dict.fromkeys(str(item).strip() for item in user_input.get("constraints", []) if str(item).strip()))
        mood = str(user_input.get("mood") or "").strip() or None

        constraints_text = "".join(constraints)
        parsed_flags = {
            "transit_first": any(keyword in constraints_text for keyword in _TRANSIT_FIRST_KEYWORDS),
            "avoid_early_rise": "不要太赶" in constraints_text or "晚起" in constraints_text,
        }

        missing: list[str] = []
        warnings: list[str] = []
        if not destination:
            missing.append("destination")
        if budget <= 0:
            missing.append("budget")
        if not user_input.get("origin"):
            warnings.append("未填写出发地：城际大交通建议将按通用口径估算。")

        normalized = {
            "destination": destination,
            "days": days,
            "budget": budget,
            "travelers": travelers,
            "mood": mood,
            "origin": user_input.get("origin"),
            "departure_date": user_input.get("departure_date"),
            "return_date": user_input.get("return_date"),
            "preferences": preferences,
            "constraints": constraints,
            "parsed_flags": parsed_flags,
        }
        return {
            "agent": self.name,
            "status": "ok" if not missing else "needs_review",
            "payload": {"normalized_input": normalized, "missing": missing, "warnings": warnings},
        }
