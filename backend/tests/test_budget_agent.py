"""Budget Agent 单测：字段名兼容、挂起判定、超预算 what_if 迁移。"""
from app.agents.budget import BudgetAgent


def _context(budget: int) -> dict:
    return {
        "user_input": {"destination": "北京市", "days": 3, "budget": budget, "travelers": 2, "origin": "上海市"},
        "outputs": {
            "Researcher": {"agent": "Researcher", "status": "ok", "payload": {"spots": []}},
            "Itinerary": {
                "agent": "Itinerary",
                "status": "ok",
                "payload": {"itinerary": [], "legs": []},
            },
            "Validator": {
                "agent": "Validator",
                "status": "ok",
                "payload": {"findings": [], "what_if": [{"scene": "同日跨区", "risk": "通勤翻倍", "plan_b": "换同区域景点"}]},
            },
        },
    }


def test_field_names_unchanged():
    agent = BudgetAgent()
    result = agent.run(_context(5000))
    for key in ("estimated_budget", "budget_breakdown", "approval_required", "economy_total", "travel_advice", "economy_tips", "what_if"):
        assert key in result["payload"], key


def test_approval_required_when_far_over():
    agent = BudgetAgent()
    result = agent.run(_context(100))
    payload = result["payload"]
    assert payload["approval_required"] is True
    assert payload["estimated_budget"] > 100


def test_what_if_budget_entry_migrated():
    agent = BudgetAgent()
    result = agent.run(_context(100))
    scenes = [item["scene"] for item in result["payload"]["what_if"]]
    assert any("预算超支" in scene for scene in scenes)


def test_validator_no_longer_produces_budget_fields():
    from app.agents.validator import ValidatorAgent

    assert not hasattr(ValidatorAgent(), "_budget_breakdown")
    assert not hasattr(ValidatorAgent(), "_economy_total")
    source = open("app/agents/validator.py", encoding="utf-8").read()
    assert "approval_required" not in source


def test_reporter_budget_dual_read():
    """Reporter 对旧任务（无 Budget 输出）兜底读 Validator 历史字段，不抛错。
    economy_tips 不进 travel_plan.md（由 /result 接口单独返回，plans.py 双读兜底）。"""
    context = _context(5000)
    context["outputs"]["Validator"] = {
        "agent": "Validator",
        "status": "ok",
        "payload": {
            "findings": [],
            "what_if": [],
            # 旧字段（历史 Validator 产物）
            "estimated_budget": 4076,
            "budget_breakdown": {"total": 4076},
            "travel_advice": {"intercity": {}, "hotel": {"nights": 2}, "weather_notes": ["晴"]},
            "economy_tips": ["历史口径提示"],
        },
    }
    from app.services.markdown_reporter import MarkdownReporter

    markdown = MarkdownReporter().render(context)
    assert "4076" in markdown  # 兜底字段正常渲染
    assert "晴" in markdown  # travel_advice.weather_notes 兜底渲染


def test_result_api_economy_tips_dual_read():
    """/result 接口 economy_tips：新任务读 Budget，旧任务兜底 Validator。"""
    import json

    from app.services.checkpoint_store import CheckpointStore
    from app.services.paths import job_dir

    store = CheckpointStore()
    job_id = "plan_budget_new_probe"
    store.create(job_id, {"destination": "北京"}, "h1")
    try:
        rel = store.mark_node_done(job_id, "Budget", {"agent": "Budget", "status": "ok", "payload": {"economy_tips": ["新口径贴士"]}}, 50)
        state = store.load(job_id)
        budget_relative = state.get("agent_outputs", {}).get("Budget")
        assert budget_relative
        tips = json.loads((job_dir(job_id) / budget_relative).read_text(encoding="utf-8"))["payload"]["economy_tips"]
        assert tips == ["新口径贴士"]
    finally:
        import shutil
        shutil.rmtree(job_dir(job_id), ignore_errors=True)
