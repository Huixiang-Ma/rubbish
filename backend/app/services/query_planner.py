"""查询分解（rag_lab 验证后回填）：多意图问题 → 子问题 → 多路检索。

三道防线（对应 1.5B 实测失败模式：不拆/乱拆/多段输出）：
1. 规则前置检测（连接词 + ≥2 城市）——单意图零开销且不可能被拆坏；
2. LLM 拆分（提示词强制保留实体，走 LLMClient.try_generate_json）；
3. 实体完整性校验——城市实体丢失即回退原问题（安全回退，宁可不拆不错拆）。
"""
from __future__ import annotations

from typing import Any

from app.services.llm_client import LLMClient

_DECOMPOSE_PROMPT = (
    "把下面这个问题拆成 2-3 个独立的单意图子问题。每个子问题必须"
    "**完整保留原问题中的城市名、店名、景点名等实体**，只改变问法。\n"
    '只输出 JSON：{"sub_questions": ["问题一", "问题二"]}，不要任何其他文字。\n'
    "【用户问题】{question}"
)

_MULTI_HINTS = ("和", "与", "分别", "还有", "以及", "哪个更", "对比", "两个")
_CITIES = (
    "北京", "上海", "杭州", "南京", "西安", "成都", "重庆", "广州", "厦门", "青岛",
    "长沙", "武汉", "昆明", "丽江", "桂林", "三亚", "苏州", "大同", "泰安",
)


def _looks_multi_intent(question: str) -> bool:
    if not any(h in question for h in _MULTI_HINTS):
        return False
    return sum(1 for c in _CITIES if c in question) >= 2


def _key_entities(question: str) -> list[str]:
    return [c for c in _CITIES if c in question]


def _subquestions_valid(question: str, subs: list[str]) -> bool:
    for entity in _key_entities(question):
        if not any(entity in s for s in subs):
            return False
    return all(len(s) >= 6 for s in subs)


def _parse_sub_questions(raw: dict[str, Any] | None) -> list[str] | None:
    if not isinstance(raw, dict):
        return None
    items = raw.get("sub_questions")
    if not isinstance(items, list):
        return None
    questions = [str(q).strip() for q in items if str(q).strip()]
    return questions or None


def decompose(question: str, llm: LLMClient | None = None) -> list[str]:
    """多意图问题 → 子问题列表；单意图/LLM 失败/实体丢失 → [原问题]（安全回退）。"""
    if not _looks_multi_intent(question):
        return [question]
    llm = llm or LLMClient()
    # 用 replace 注入（避免 .format 把 prompt 里字面的 {"sub_questions"} 当占位符）
    raw = llm.try_generate_json(_DECOMPOSE_PROMPT.replace("{question}", question))
    questions = _parse_sub_questions(raw)
    if not questions or len(questions) > 4 or not _subquestions_valid(question, questions):
        return [question]
    return questions
