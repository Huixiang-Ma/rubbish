"""外部 API 客户端（amap_client / qweather_client）的离线单测：HTTP 层全部 monkeypatch，不发起真实请求。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import amap_client, qweather_client


class FakeResp:
    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


@pytest.fixture(autouse=True)
def _reset_cache():
    amap_client._cache.clear()
    qweather_client._cache.clear()
    yield
    amap_client._cache.clear()
    qweather_client._cache.clear()


def test_amap_not_configured_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMAP_API_KEY", raising=False)
    assert amap_client.geocode("北京市") is None
    assert amap_client.search_pois("北京市", "景点") == []


def test_amap_geocode_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k-amap")
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        assert params["key"] == "k-amap"
        assert params["address"] == "北京市"
        return FakeResp(
            {"status": "1", "geocodes": [{"location": "116.397,39.908", "adcode": "110000", "city": "北京市"}]}
        )

    monkeypatch.setattr(amap_client, "_http_get", fake_get)
    result = amap_client.geocode("北京市")
    assert result == {"lng": 116.397, "lat": 39.908, "adcode": "110000", "city": "北京市"}
    assert calls and "v3/geocode/geo" in calls[0]


def test_amap_search_pois_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k-amap")
    monkeypatch.setattr(
        amap_client,
        "_http_get",
        lambda url, params=None, timeout=None: FakeResp(
            {
                "status": "1",
                "pois": [
                    {"name": "故宫博物院", "location": "116.397,39.918", "address": "景山前街4号", "type": "风景名胜;风景名胜;国家级景点"}
                ],
            }
        ),
    )
    pois = amap_client.search_pois("北京市", "景点")
    assert pois[0]["name"] == "故宫博物院"
    assert pois[0]["lat"] == 39.918
    assert "风景名胜" in pois[0]["type"]


def test_amap_route_transit_and_driving(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k-amap")
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen[url] = params
        if "transit" in url:
            return FakeResp({"status": "1", "route": {"transits": [{"duration": "2400"}]}})
        return FakeResp({"status": "1", "route": {"paths": [{"duration": "1200", "distance": "8100"}]}})

    monkeypatch.setattr(amap_client, "_http_get", fake_get)
    result = amap_client.route_between("116.39,39.90", "116.41,39.92", city="北京")
    assert result["transit_minutes"] == 40
    assert result["driving_minutes"] == 20
    assert result["distance_km"] == 8.1
    # 公交路径规划需要 city 参数（城市名，不带"市"后缀）
    transit_url = next(u for u in seen if "transit" in u)
    assert seen[transit_url]["city"] == "北京"


def test_amap_cache_avoids_second_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k-amap")
    counter = {"n": 0}

    def fake_get(url, params=None, timeout=None):
        counter["n"] += 1
        return FakeResp({"status": "1", "geocodes": [{"location": "116.0,39.0", "adcode": "1", "city": "北京市"}]})

    monkeypatch.setattr(amap_client, "_http_get", fake_get)
    amap_client.geocode("北京市")
    amap_client.geocode("北京市")
    assert counter["n"] == 1


def test_amap_bad_status_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "k-amap")
    monkeypatch.setattr(amap_client, "_http_get", lambda url, params=None, timeout=None: FakeResp({"status": "0"}))
    assert amap_client.geocode("不存在的地方xyz") is None


def test_qweather_not_configured_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEATHER_API_KEY", raising=False)
    assert qweather_client.weather_3d("116.39,39.90") is None


def test_qweather_parses_3d(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEATHER_API_KEY", "k-q")
    monkeypatch.setattr(
        qweather_client,
        "_http_get",
        lambda url, params=None, timeout=None, headers=None: FakeResp(
            {
                "code": "200",
                "daily": [
                    {"fxDate": "2026-09-01", "textDay": "晴", "tempMax": "30", "tempMin": "22"},
                    {"fxDate": "2026-09-02", "textDay": "多云", "tempMax": "29", "tempMin": "21"},
                ],
            }
        ),
    )
    daily = qweather_client.weather_3d("116.39,39.90")
    assert daily[0]["text_day"] == "晴"
    assert daily[1]["temp_max"] == "29"


def test_qweather_bad_code_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEATHER_API_KEY", "k-q")
    monkeypatch.setattr(qweather_client, "_http_get", lambda url, params=None, timeout=None, headers=None: FakeResp({"code": "402"}))
    assert qweather_client.weather_3d("116.39,39.90") is None
