"""Planner 大模型规划（决策层）与 Debate/Mood 模板化回归的单测。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.debate import DebateAgent
from app.agents.mood import MoodAgent
from app.agents.planner import PlannerAgent

SPOTS = [
    {"name": "故宫博物院", "tags": ["博物馆"], "ticket_price": 60, "visit_minutes": 180, "lat": 39.918, "lng": 116.397},
    {"name": "天坛公园", "tags": ["公园"], "ticket_price": 35, "visit_minutes": 120, "lat": 39.882, "lng": 116.407},
    {"name": "中国国家博物馆", "tags": ["博物馆"], "ticket_price": 0, "visit_minutes": 150, "lat": 39.905, "lng": 116.4},
    {"name": "景山公园", "tags": ["公园"], "ticket_price": 2, "visit_minutes": 90, "lat": 39.923, "lng": 116.397},
]


def _context(days: int = 2):
    return {
        "user_input": {"destination": "北京市", "days": days, "budget": 8000, "preferences": ["博物馆"], "constraints": ["减少打车"]},
        "outputs": {"Researcher": {"payload": {"spots": SPOTS}}},
    }


def _planner_with_llm(monkeypatch: pytest.MonkeyPatch, llm_result, mode: str = "real") -> PlannerAgent:
    agent = PlannerAgent()
    monkeypatch.setattr(agent.llm, "mode", mode)
    monkeypatch.setattr(agent.llm, "try_generate_json", lambda prompt: llm_result)
    return agent


def test_planner_uses_llm_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM 返回合法编排（非顺序切片）时，按 LLM 决策分组。"""
    llm_plan = {
        "days": [
            {"day": 1, "theme": "皇城中轴线", "spot_names": ["中国国家博物馆", "故宫博物院"]},
            {"day": 2, "theme": "坛庙园林", "spot_names": ["天坛公园", "景山公园"]},
        ]
    }
    agent = _planner_with_llm(monkeypatch, llm_plan)
    payload = agent.run(_context())["payload"]
    assert payload["mode"] == "llm"
    assert [d["spot_names"] for d in payload["days"]] == [["中国国家博物馆", "故宫博物院"], ["天坛公园", "景山公园"]]
    assert [d["theme"] for d in payload["days"]] == ["皇城中轴线", "坛庙园林"]


def test_planner_falls_back_to_rule_without_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = _planner_with_llm(monkeypatch, None)
    payload = agent.run(_context())["payload"]
    assert payload["mode"] == "rule"
    # 顺序切片：每天最多 3 个
    assert all(len(d["spot_names"]) <= 3 for d in payload["days"])
    assert sum(len(d["spot_names"]) for d in payload["days"]) <= len(SPOTS)


def test_planner_rejects_invalid_llm_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [
        {"days": [{"day": 1, "theme": "x", "spot_names": ["不存在景点"]}]},                      # 未知景点
        {"days": [{"day": 1, "theme": "x", "spot_names": ["天坛公园"]}]},                        # 天数不足
        {"days": [{"day": 1, "theme": "x", "spot_names": ["天坛公园"]}, {"day": 2, "theme": "y", "spot_names": ["天坛公园"]}]},  # 跨天重复
        {"days": [{"day": 1, "theme": "x", "spot_names": [s["name"] for s in SPOTS]}]},  # 单日超 3 个
    ]
    for bad in cases:
        agent = _planner_with_llm(monkeypatch, bad)
        payload = agent.run(_context())["payload"]
        assert payload["mode"] == "rule", f"非法 LLM 编排未被拒绝：{bad}"


def test_debate_and_mood_are_template_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """辩论/心情不再调用 LLM：即使 LLM 配置为 real 也走确定性模板。"""
    context = _context()
    context["outputs"]["Itinerary"] = {"payload": {"itinerary": [
        {"day": 1, "theme": "历史文化经典线", "items": [{"title": "游览故宫博物院", "spot": {"name": "故宫博物院"}}]},
        {"day": 2, "theme": "城市漫步体验线", "items": [{"title": "游览天坛公园", "spot": {"name": "天坛公园"}}]},
    ]}}
    context["outputs"]["Validator"] = {"payload": {"estimated_budget": 3000, "findings": []}}
    context["outputs"]["Planner"] = {"payload": {"days": [
        {"day": 1, "theme": "历史文化经典线", "spot_names": ["故宫博物院"]},
        {"day": 2, "theme": "城市漫步体验线", "spot_names": ["天坛公园"]},
    ]}}
    context["user_input"]["mood"] = "想被治愈"
    debate = DebateAgent()
    payload = debate.run(context)["payload"]
    assert payload["mode"] == "template"
    assert len(payload["debates"]) == 3
    mood = MoodAgent()
    mood_payload = mood.run(context)["payload"]
    assert mood_payload["phases"], "模板心情剧本应生成每日阶段"
