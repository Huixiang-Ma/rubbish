"""Intake Agent 单测：归一化、缺省填充、去重、transit_first 判定。"""
from app.agents.intake import IntakeAgent


def test_normalization_and_flags():
    agent = IntakeAgent()
    result = agent.run({
        "user_input": {
            "destination": "北京市",
            "days": 3,
            "budget": 5000,
            "travelers": 2,
            "preferences": ["博物馆", "博物馆", " 美食 "],
            "constraints": ["减少打车", "减少打车", "不要太赶"],
        }
    })
    payload = result["payload"]
    normalized = payload["normalized_input"]
    assert normalized["destination"] == "北京"
    assert normalized["preferences"] == ["博物馆", "美食"]  # 去重 + 去空白
    assert normalized["constraints"] == ["减少打车", "不要太赶"]
    assert normalized["parsed_flags"]["transit_first"] is True
    assert normalized["parsed_flags"]["avoid_early_rise"] is True
    assert payload["missing"] == []


def test_defaults_and_warnings():
    agent = IntakeAgent()
    result = agent.run({"user_input": {"destination": "西安"}})
    normalized = result["payload"]["normalized_input"]
    assert normalized["days"] == 3  # 缺省 3 天
    assert normalized["travelers"] == 2  # 缺省 2 人
    assert normalized["budget"] == 0
    assert "budget" in result["payload"]["missing"]
    assert any("出发地" in w for w in result["payload"]["warnings"])


def test_days_clamped():
    agent = IntakeAgent()
    result = agent.run({"user_input": {"destination": "北京", "days": 99, "budget": 3000}})
    assert result["payload"]["normalized_input"]["days"] == 14


def test_pipeline_starts_with_intake():
    from app.services.pipelines import TOB_PIPELINE, TOC_PIPELINE

    for pipeline in (TOC_PIPELINE, TOB_PIPELINE):
        assert pipeline[0] == "Intake"
        assert pipeline.index("Budget") == pipeline.index("Itinerary") + 1
        assert pipeline.index("Validator") == pipeline.index("Budget") + 1
