"""地理聚类编排与跨度校验测试：同天景点不允许跨度过大。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.planner import _cluster_areas
from app.agents.validator import ValidatorAgent


def test_cluster_areas_groups_nearby_spots() -> None:
    """相邻（≤5km）景点归入同一地理区域，远距离景点分开。"""
    spots = [
        {"name": "滕王阁", "lat": 28.681, "lng": 115.881},
        {"name": "万寿宫", "lat": 28.679, "lng": 115.885},  # 距滕王阁 <1km
        {"name": "梅岭", "lat": 28.87, "lng": 115.77},  # 远郊
    ]
    areas = _cluster_areas(spots)
    assert areas["滕王阁"] == areas["万寿宫"], "相邻景点应同区域"
    assert areas["梅岭"] != areas["滕王阁"], "远郊景点应分属不同区域"


def test_validator_flags_spatial_spread(monkeypatch: pytest.MonkeyPatch) -> None:
    """同天相邻景点直线距离超过 15km 时生成 spatial_spread 告警并进入翻车预演。"""
    import test_no_demo_content as helper

    context = helper._build_context()
    itinerary = context["outputs"]["Itinerary"]["payload"]["itinerary"]
    # 构造跨度过大的一天：第二站搬到远郊
    far = {"name": "远郊景点", "lat": 29.4, "lng": 116.6, "tags": [], "ticket_price": 0}
    itinerary[0]["items"].append(
        {"time": "13:00-15:00", "title": "游览远郊景点", "spot": far, "transport": "x", "reason": "x"}
    )
    validation = ValidatorAgent().run(context)["payload"]
    types = [f["type"] for f in validation["findings"]]
    assert "spatial_spread" in types, types
    scenes = [e["scene"] for e in validation["what_if"]]
    assert any("地理跨度过大" in s or "相距约" in s for s in scenes), scenes
