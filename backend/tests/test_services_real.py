"""旅行服务大厅 / 周边 POI 真实化单测：HTTP 全部 monkeypatch，不发起真实请求。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import amap_client
from app.services.travel_context_service import TravelContextService


@pytest.fixture(autouse=True)
def _reset_cache():
    amap_client._cache.clear()
    yield
    amap_client._cache.clear()


def _enable_amap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k")
    monkeypatch.setattr(
        amap_client, "geocode",
        lambda address: {"lng": 116.397, "lat": 39.908, "adcode": "110000", "city": "北京市"},
    )
    monkeypatch.setattr(
        amap_client, "search_pois",
        lambda city, keywords, size=10: [
            {"name": "故宫博物院", "lng": 116.397, "lat": 39.918, "address": "景山前街4号", "type": "风景名胜;世界遗产"},
        ],
    )
    monkeypatch.setattr(
        amap_client, "route_between",
        lambda origin, dest, city="北京": {"transit_minutes": 30, "driving_minutes": 20, "distance_km": 8.0},
    )


def test_attractions_real(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_amap(monkeypatch)
    data = TravelContextService().attractions("北京市")
    spot = data["attractions"][0]
    assert spot["name"] == "故宫博物院"
    assert "comfort" not in spot, "不应再输出伪舒适度"
    assert spot["ticket_price"] == 60  # 匹配静态库继承票价


def test_merchants_real(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_amap(monkeypatch)
    monkeypatch.setattr(
        amap_client, "around_pois",
        lambda lng, lat, types="", keywords="", radius=5000, size=8: [
            {"name": "前门大街", "lng": 116.398, "lat": 39.899, "address": "前门大街", "type": "购物服务;商场;购物中心"},
        ],
    )
    data = TravelContextService().merchants("北京市")
    m = data["merchants"][0]
    assert m["name"] == "前门大街"
    assert m["category"] in {"美食", "购物", "休闲"}
    assert isinstance(m["distance_km"], float)
    assert "演示" not in data["note"]


def test_entertainment_real(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_amap(monkeypatch)
    monkeypatch.setattr(
        amap_client, "around_pois",
        lambda lng, lat, types="", keywords="", radius=5000, size=8: [
            {"name": "天桥艺术中心", "lng": 116.395, "lat": 39.885, "address": "天桥南大街9号", "type": "科教文化服务;剧场"},
        ],
    )
    data = TravelContextService().entertainment("北京市")
    e = data["entertainments"][0]
    assert e["name"] == "天桥艺术中心"
    assert e["time"] == "以场馆公告为准"
    assert e["price"] == "以现场公示为准"


def test_hotels_real(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_amap(monkeypatch)
    monkeypatch.setattr(
        amap_client, "around_pois",
        lambda lng, lat, types="", keywords="", radius=5000, size=8: [
            {"name": "北京饭店", "lng": 116.4, "lat": 39.909, "address": "东长安街33号", "type": "住宿服务;宾馆"},
        ],
    )
    data = TravelContextService().hotels("北京市", nights=1)
    h = data["hotels"][0]
    assert h["name"] == "北京饭店"
    assert "per_night" not in h or not isinstance(h.get("per_night"), int), "不应虚构房价"
    assert "演示" not in json.dumps(data, ensure_ascii=False)


def test_train_flight_guidance_only(monkeypatch: pytest.MonkeyPatch) -> None:
    svc = TravelContextService()
    train = svc.train_tickets("上海", "北京")
    flight = svc.flights("上海", "北京")
    for data, kind in ((train, "train"), (flight, "flight")):
        assert data["tickets" if kind == "train" else "flights"] == [], "不得返回虚拟班次"
        assert "12306" in json.dumps(data, ensure_ascii=False) or "航司官网" in json.dumps(data, ensure_ascii=False)
        assert "演示" not in json.dumps(data, ensure_ascii=False)


def test_nearby_real(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_amap(monkeypatch)
    monkeypatch.setattr(
        amap_client, "around_pois",
        lambda lng, lat, types="", keywords="", radius=1000, size=8: [
            {"name": "四季民福(故宫店)", "lng": 116.402, "lat": 39.916, "address": "景山前街", "type": "餐饮服务;中餐厅"},
        ],
    )
    spot = {"name": "故宫博物院", "lat": 39.918, "lng": 116.397}
    pois = TravelContextService().nearby_pois(spot, "food")
    assert pois[0]["name"] == "四季民福(故宫店)"
    assert pois[0]["distance_m"] > 0
    assert "演示" not in pois[0]["note"]


def test_offline_fallbacks_empty_not_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMAP_API_KEY", raising=False)
    svc = TravelContextService()
    assert svc.attractions("北京市")["attractions"] == []
    assert svc.merchants("北京市")["merchants"] == []
    assert svc.entertainment("北京市")["entertainments"] == []
    assert svc.hotels("北京市")["hotels"] == []
    assert svc.nearby_pois({"name": "故宫博物院", "lat": 39.9, "lng": 116.39}, "food") == []
