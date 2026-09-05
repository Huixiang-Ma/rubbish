"""真实 API 接入业务层的单测：外部 HTTP 全部 monkeypatch，验证接线逻辑与回退行为。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import amap_client, qweather_client
from app.services.scenic_spot_service import ScenicSpotService
from app.services.travel_context_service import TravelContextService

AMAP_POIS = [
    {"name": "故宫博物院", "lng": 116.397, "lat": 39.918, "address": "景山前街4号", "type": "风景名胜;国家级景点"},
    {"name": "国家博物馆", "lng": 116.4, "lat": 39.905, "address": "东长安街16号", "type": "博物馆;科教文化场所"},
]


@pytest.fixture(autouse=True)
def _reset_cache():
    amap_client._cache.clear()
    qweather_client._cache.clear()
    yield
    amap_client._cache.clear()
    qweather_client._cache.clear()


def test_scenic_recommend_uses_amap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(amap_client, "search_pois", lambda city, keywords, size=10: AMAP_POIS)
    spots = ScenicSpotService().recommend("北京市", ["博物馆"], limit=8)
    assert spots[0]["name"] == "故宫博物院"
    assert spots[0]["source"] == "高德POI"
    assert spots[0]["lat"] == 39.918


def test_scenic_recommend_fallback_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMAP_API_KEY", raising=False)
    spots = ScenicSpotService().recommend("北京市", ["亲子"], limit=8)
    assert spots and spots[0].get("name")  # 静态演示库
    assert "source" not in spots[0]


def test_commute_uses_real_route(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(
        amap_client,
        "route_between",
        lambda origin, dest, city="北京": {"transit_minutes": 40, "driving_minutes": 20, "distance_km": 8.1},
    )
    leg = TravelContextService().commute_between(
        {"name": "A", "lat": 39.9, "lng": 116.39},
        {"name": "B", "lat": 39.92, "lng": 116.41},
        city="北京市",
    )
    assert leg["metro_minutes"] == 40
    assert leg["taxi_minutes"] == 20
    assert leg["taxi_fare"] == round(13 + 8.1 * 2.3)  # 打车费仍按本地口径：起步价+公里单价
    assert leg["source"] == "高德路径规划"


def test_commute_fallback_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMAP_API_KEY", raising=False)
    leg = TravelContextService().commute_between(
        {"name": "A", "lat": 39.9, "lng": 116.39},
        {"name": "B", "lat": 39.92, "lng": 116.41},
    )
    assert leg["metro_minutes"] > 0 and leg["taxi_minutes"] > 0
    assert "source" not in leg


def test_daily_meals_uses_amap_around(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(amap_client, "around_pois", lambda lng, lat, types="050000", radius=3000, size=8: AMAP_POIS)
    meals = TravelContextService().daily_meals(
        "北京市", 1, {"早餐": "故宫博物院", "午餐": "故宫博物院", "晚餐": "国家博物馆", "夜宵": "国家博物馆"},
        coords={"午餐": (116.397, 39.918), "晚餐": (116.4, 39.905)},
    )
    assert len(meals) == 4
    assert meals[0]["restaurant"] == "故宫博物院"
    assert meals[0]["price_hint"] == "以门店公示为准"
    assert meals[0]["source"] == "高德POI"


def test_daily_meals_fallback_without_coords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    meals = TravelContextService().daily_meals("北京市", 1, {"早餐": "故宫博物院"})
    assert meals[0]["restaurant"].startswith("北京")  # 回退演示模板
    assert "source" not in meals[0]


def test_weather_notes_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setenv("QWEATHER_API_KEY", "kq")
    monkeypatch.setattr(
        amap_client, "geocode",
        lambda address: {"lng": 116.397, "lat": 39.908, "adcode": "110000", "city": "北京市"},
    )
    monkeypatch.setattr(
        qweather_client, "weather_3d",
        lambda location: [
            {"date": "2026-09-01", "text_day": "晴", "text_night": "多云", "temp_max": "30", "temp_min": "22"},
        ],
    )
    notes = TravelContextService().weather_notes("北京市")
    assert any("和风天气" in note for note in notes)
    assert any("晴" in note for note in notes)


def test_weather_notes_fallback_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("AMAP_API_KEY", raising=False)
    notes = TravelContextService().weather_notes("北京市")
    assert any("春季" in note for note in notes)  # 四季演示样例
