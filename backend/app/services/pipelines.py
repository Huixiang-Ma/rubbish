"""toC / toB 双管线定义：底层能力共享，上层 Agent 组合按提交方向分叉。

- toC（游客体验向）：含 Debate（直播辩论）、Mood（心情剧本，填 mood 才跑）
- toB（企业经营向）：含 Consultant（顾问话术/报价）、Compliance（合规审计摘要），不跑 C 端特色节点

分叉依据：提交的 user_input 带 customer 或 tenant 字段即视为 toB 代客提交。
"""
from __future__ import annotations

from typing import Any

TOC_PIPELINE = ["Intake", "Researcher", "Planner", "Itinerary", "Budget", "Validator", "Sentiment", "Debate", "Mood", "Reporter"]
TOB_PIPELINE = ["Intake", "Researcher", "Planner", "Itinerary", "Budget", "Validator", "Sentiment", "Consultant", "Compliance", "Reporter"]

# 兼容旧 state（无 pipeline 字段）的默认顺序
DEFAULT_PIPELINE = TOC_PIPELINE


def resolve_pipeline(user_input: dict[str, Any]) -> tuple[str, list[str]]:
    """按提交内容判定方向，返回 (pipeline_key, 节点顺序)。"""
    is_tob = bool(user_input.get("customer") or user_input.get("tenant"))
    return ("tob", TOB_PIPELINE) if is_tob else ("toc", TOC_PIPELINE)
