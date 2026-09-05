"""行程书内容口径单测：任何模式下渲染出的 travel_plan.md 都不得包含演示性内容。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents import compliance, consultant  # noqa: F401 触发注册
from app.agents.debate import DebateAgent
from app.agents.itinerary import ItineraryAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.validator import ValidatorAgent
from app.services import amap_client, qweather_client
from app.services.markdown_reporter import MarkdownReporter


def _build_context(pipeline: str = "toc") -> dict:
    user_input = {
        "destination": "北京市",
        "days": 2,
        "budget": 8000,
        "origin": "上海",
        "preferences": ["博物馆"],
        "constraints": ["减少打车"],
        "travelers": 2,
        "customer": "示例客户" if pipeline == "tob" else None,
    }
    context = {"user_input": user_input, "outputs": {}, "pipeline": pipeline}
    chain = [ResearcherAgent(), PlannerAgent(), ItineraryAgent(), ValidatorAgent()]
    if pipeline == "toc":
        chain.append(DebateAgent())
    else:
        from app.agents.consultant import ConsultantAgent
        from app.agents.compliance import ComplianceAgent

        chain += [ConsultantAgent(), ComplianceAgent()]
    for agent in chain:
        context["outputs"][agent.name] = agent.run(context)
    return context


def _stub_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """辩论/心情已模板化（LLM 仅存在于 Planner 决策层），无需打桩；保留占位以维持调用形态。"""
    return None


def test_offline_render_has_no_demo_wording(monkeypatch: pytest.MonkeyPatch) -> None:
    """无密钥离线模式：无真实来源的板块要么省略、要么给官方渠道指引，不出现假班次/假房价。"""
    # 显式置空密钥并强制 mock LLM：.env 兜底加载会让 delenv 失效，离线模式必须真正无密钥。
    from app.config import get_settings
    for key in ("AMAP_API_KEY", "QWEATHER_API_KEY", "FLIGGY_AI_API_KEY", "LLM_API_KEY"):
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("LLM_MODE", "mock")
    get_settings.cache_clear()
    amap_client._cache.clear()
    qweather_client._cache.clear()
    md = MarkdownReporter().render(_build_context())
    assert "演示" not in md, [line for line in md.splitlines() if "演示" in line][:3]
    assert "G1" not in md, "离线模式不得渲染虚拟班次（旧演示版特征）"


def test_real_render_uses_live_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    """配置密钥后：行程书引用高德/和风实时数据，酒店为真实检索结果。"""
    _stub_llm(monkeypatch)
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setenv("QWEATHER_API_KEY", "kq")
    amap_client._cache.clear()
    qweather_client._cache.clear()
    monkeypatch.setattr(
        amap_client, "search_pois",
        lambda city, keywords, size=10: [
            {"name": "故宫博物院", "lng": 116.397, "lat": 39.918, "address": "景山前街4号", "type": "风景名胜;世界遗产", "open_time": "08:30-17:00"},
            {"name": "中国国家博物馆", "lng": 116.4, "lat": 39.905, "address": "东长安街16号", "type": "博物馆;科教文化场所", "open_time": "09:00-17:00"},
        ],
    )
    monkeypatch.setattr(
        amap_client, "route_between",
        lambda origin, dest, city="北京": {"transit_minutes": 30, "driving_minutes": 20, "distance_km": 8.0},
    )
    def fake_geocode(address):
        return {"lng": 116.397, "lat": 39.908, "adcode": "110000", "city": "北京市"}
    def fake_around(lng, lat, types="050000", radius=3000, size=8):
        if types == "100000":
            return [{"name": "北京饭店", "lng": 116.4, "lat": 39.909, "address": "东长安街33号", "type": "住宿服务;宾馆"}]
        return [{"name": "四季民福", "lng": 116.4, "lat": 39.9, "address": "", "type": "餐饮服务;中餐厅;北京菜"}]
    monkeypatch.setattr(amap_client, "geocode", fake_geocode)
    monkeypatch.setattr(amap_client, "around_pois", fake_around)
    monkeypatch.setattr(
        qweather_client, "weather_3d",
        lambda location: [{"date": "2026-09-01", "text_day": "晴", "temp_max": "30", "temp_min": "22"}],
    )
    md = MarkdownReporter().render(_build_context())
    assert "演示" not in md, [line for line in md.splitlines() if "演示" in line][:3]
    assert "北京饭店" in md, "住宿推荐应来自高德真实检索"
    assert "四季民福" in md
    assert "开放时间：08:30-17:00（高德实时）" in md, "景点开放时间应来自高德实时字段并标注来源"
