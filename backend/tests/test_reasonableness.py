"""行程书合理性修复的单测：景点去重、短途步行、动态时间轴、菜品展示友好化、门票继承。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.agents.itinerary import ItineraryAgent, _fmt_clock, compute_schedule
from app.services import amap_client
from app.services.scenic_spot_service import ScenicSpotService
from app.services.travel_context_service import TravelContextService


@pytest.fixture(autouse=True)
def _reset_cache():
    amap_client._cache.clear()
    yield
    amap_client._cache.clear()


def test_scenic_recommend_dedupes_nested_and_duplicate_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    """天安门 是 天安门广场 的子集名：只保留更完整的一个；重复标签去重。"""
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(
        amap_client,
        "search_pois",
        lambda city, keywords, size=10: [
            {"name": "天安门广场", "lng": 116.397, "lat": 39.903, "address": "", "type": "风景名胜;风景名胜;红色景区"},
            {"name": "天安门", "lng": 116.397, "lat": 39.908, "address": "", "type": "风景名胜;国家级景点"},
            {"name": "故宫博物院", "lng": 116.397, "lat": 39.918, "address": "", "type": "世界遗产;世界遗产;科教文化服务"},
        ],
    )
    spots = ScenicSpotService().recommend("北京市", ["博物馆"], limit=8)
    names = [s["name"] for s in spots]
    assert "天安门" not in names, f"嵌套重复景点未去除：{names}"
    assert "天安门广场" in names
    for spot in spots:
        assert len(spot["tags"]) == len(set(spot["tags"])), f"标签未去重：{spot['tags']}"
    # 故宫匹配静态库：门票与游览时长继承
    gugong = next(s for s in spots if s["name"] == "故宫博物院")
    assert gugong["ticket_price"] == 60
    assert gugong["visit_minutes"] == 180


def test_commute_short_distance_walks(monkeypatch: pytest.MonkeyPatch) -> None:
    """1 公里内步行即可：不调公交规划（地铁 55 分钟到隔壁不合理）。"""
    monkeypatch.setenv("AMAP_API_KEY", "k")
    called = {"n": 0}

    def fake_route(origin, dest, city="北京"):
        called["n"] += 1
        return {"transit_minutes": 55, "driving_minutes": 20, "distance_km": 0.4}

    monkeypatch.setattr(amap_client, "route_between", fake_route)
    leg = TravelContextService().commute_between(
        {"name": "天安门", "lat": 39.908, "lng": 116.397},
        {"name": "天安门广场", "lat": 39.903, "lng": 116.397},
        city="北京",
    )
    assert called["n"] == 0, "短途不应触发公交路径规划"
    assert leg["metro_minutes"] <= 15, f"短途通勤应按步行：{leg['metro_minutes']}"
    assert leg["taxi_minutes"] <= 15


def test_daily_meal_signature_friendly(monkeypatch: pytest.MonkeyPatch) -> None:
    """推荐菜品展示为友好菜系名，不暴露 '餐饮服务;xxx' 内部类型码。"""
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(
        amap_client,
        "around_pois",
        lambda lng, lat, types="050000", radius=3000, size=8: [
            {"name": "四季民福", "lng": 116.4, "lat": 39.9, "address": "", "type": "餐饮服务;中餐厅;北京菜"},
        ],
    )
    meals = TravelContextService().daily_meals(
        "北京市", 1, {"午餐": "故宫博物院"},
        coords={"午餐": (116.4, 39.9)},
    )
    lunch = next(m for m in meals if m["meal"] == "午餐")
    assert "餐饮服务" not in lunch["signature"], lunch["signature"]
    assert lunch["signature"] == "中餐厅 · 北京菜"


def test_compute_schedule_dynamic_times() -> None:
    """时间轴按通勤+游览时长顺序推算，用餐时间随之让位，不再写死。"""
    # 常规：2 个景点（游览 150/120 分钟，通勤 30/20 分钟）
    plan = compute_schedule(visit_minutes=[150, 120], commute_minutes=[30, 20])
    assert plan["items"][0] == (550, 700)   # 09:10-11:40
    assert plan["lunch"] == (720, 780)      # 12:00-13:00
    assert plan["items"][1] == (800, 920)   # 13:20-15:20
    assert plan["dinner"][0] == 1100        # 18:20
    assert plan["supper"][0] == 1290        # 21:30
    # 紧凑：3 个长游览，各段顺延
    plan2 = compute_schedule(visit_minutes=[150, 150, 150], commute_minutes=[60, 50, 40])
    starts = [s for s, _ in plan2["items"]]
    assert starts == sorted(starts), "游览开始时间必须单调递增"
    assert plan2["dinner"][0] >= plan2["items"][-1][1], "晚餐必须在最后一个景点结束之后"
    assert plan2["supper"][0] >= plan2["dinner"][1] + 60, "夜宵至少在晚餐结束 1 小时后"


def test_fmt_clock_never_exceeds_24h() -> None:
    """时间渲染防溢出：超过 24 点显示为"次日 HH:MM"，杜绝 25:58/32:07 这类错乱时间。"""
    assert _fmt_clock(559) == "09:19"
    assert _fmt_clock(1558) == "次日 01:58"
    assert _fmt_clock(1927) == "次日 08:07"


def test_itinerary_anchor_uses_destination_city(monkeypatch: pytest.MonkeyPatch) -> None:
    """行程首站通勤锚点应为目的地市中心，而非写死的北京天安门（非北京城市曾算出 15 小时通勤）。"""
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(
        amap_client, "geocode",
        lambda address: {"lng": 115.857, "lat": 28.682, "adcode": "360100", "city": "南昌市"},
    )
    monkeypatch.setattr(
        amap_client, "route_between",
        lambda origin, dest, city="北京": {"transit_minutes": 40, "driving_minutes": 25, "distance_km": 9.0},
    )
    context = {
        "user_input": {"destination": "南昌市", "days": 1, "budget": 5000, "travelers": 2},
        "outputs": {
            "Planner": {"payload": {"days": [{"day": 1, "theme": "豫章古韵", "spot_names": ["滕王阁"]}]}},
            "Researcher": {
                "payload": {
                    "spots": [
                        {"name": "滕王阁", "lat": 28.672, "lng": 115.89, "tags": ["地标"], "ticket_price": 50, "visit_minutes": 120}
                    ]
                }
            },
        },
    }
    payload = ItineraryAgent().run(context)["payload"]
    assert payload["legs"][0]["from"] == "南昌市中心", payload["legs"][0]["from"]
    assert "天安门" not in payload["legs"][0]["from"]
