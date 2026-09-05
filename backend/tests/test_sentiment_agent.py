"""Sentiment 舆情 Agent 单测：告警口径、本地库回退、管线接入。"""
from app.agents.sentiment import SentimentAgent


def _context_with(spots: list[dict], itinerary_names: list[str]) -> dict:
    return {
        "user_input": {"destination": "北京市", "days": 3, "budget": 5000},
        "outputs": {
            "Researcher": {"agent": "Researcher", "status": "ok", "payload": {"spots": spots}},
            "Itinerary": {
                "agent": "Itinerary",
                "status": "ok",
                "payload": {
                    "itinerary": [
                        {"day": i + 1, "items": [{"spot": {"name": name}} for name in day_names]}
                        for i, day_names in enumerate([itinerary_names])
                    ]
                },
            },
        },
    }


def test_benign_no_alert():
    agent = SentimentAgent()
    context = _context_with(
        [{"name": "景山公园"}],
        ["景山公园"],
    )
    result = agent.run(context)
    reviews = result["payload"]["reviews"]
    assert reviews and reviews[0]["risk_level"] == "BENIGN"
    assert result["payload"]["risk_alerts"] == []


def test_scam_alert():
    agent = SentimentAgent()
    # 南锣鼓巷 在本地舆情库中标记为 SCAM_RISK
    context = _context_with([{"name": "南锣鼓巷"}], ["南锣鼓巷"])
    result = agent.run(context)
    alerts = result["payload"]["risk_alerts"]
    assert any(a["name"] == "南锣鼓巷" and a["risk_level"] == "SCAM_RISK" and a["suggestion"] for a in alerts)


def test_unknown_fallback_conservative(monkeypatch):
    agent = SentimentAgent()
    # 模拟 LLM 不可用（mock 模式）：必须回退本地库，未收录景点输出 UNKNOWN 保守文案
    monkeypatch.setattr(agent.llm, "mode", "mock")
    context = _context_with([{"name": "不存在的景点XYZ"}], ["不存在的景点XYZ"])
    result = agent.run(context)
    review = result["payload"]["reviews"][0]
    assert review["risk_level"] == "UNKNOWN"
    assert "自行确认" in review["warnings"][0]


def test_names_dedup_from_researcher_and_itinerary():
    agent = SentimentAgent()
    context = _context_with([{"name": "故宫博物院"}, {"name": "景山公园"}], ["故宫博物院", "景山公园"])
    result = agent.run(context)
    names = [r["name"] for r in result["payload"]["reviews"]]
    assert names == ["故宫博物院", "景山公园"]


def test_pipeline_contains():
    from app.services.pipelines import TOB_PIPELINE, TOC_PIPELINE

    assert "Sentiment" in TOC_PIPELINE
    assert "Sentiment" in TOB_PIPELINE
    # 顺序约束：Sentiment 必须紧跟 Validator 之后
    for pipeline in (TOC_PIPELINE, TOB_PIPELINE):
        assert pipeline.index("Sentiment") == pipeline.index("Validator") + 1
