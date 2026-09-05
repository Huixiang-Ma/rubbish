from abc import ABC, abstractmethod
from typing import Any


def get_budget_payload(outputs: dict[str, Any]) -> dict[str, Any]:
    """读取预算 payload：新管线从 Budget 节点取；旧任务兜底 Validator 历史字段。"""
    budget = outputs.get("Budget", {}).get("payload")
    if budget:
        return budget
    validator = outputs.get("Validator", {}).get("payload", {})
    return {
        key: validator[key]
        for key in ("estimated_budget", "budget_breakdown", "approval_required", "economy_total", "travel_advice", "economy_tips")
        if key in validator
    }


class AgentBase(ABC):
    name: str

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
