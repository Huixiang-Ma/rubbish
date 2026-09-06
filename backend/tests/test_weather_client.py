"""双源天气（weather_client / open_meteo_client）离线单测：HTTP 层全部 monkeypatch，不发起真实请求。"""
import pytest

from app.api_registry import load_api_configs
from app.services import open_meteo_client, qweather_client, weather_client


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _clear_caches():
    open_meteo_client._cache.clear()
    qweather_client._cache.clear()
    yield
    open_meteo_client._cache.clear()
    qweather_client._cache.clear()


def test_qweather_primary_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(qweather_client, "weather_3d", lambda loc: [{"date": "2026-09-06"}])

    def _boom(*args, **kwargs):
        raise AssertionError("open-meteo 不应在主源成功时被调用")

    monkeypatch.setattr(open_meteo_client, "weather_3d", _boom)
    assert weather_client.weather_3d("116.39,39.90") == [{"date": "2026-09-06"}]
    assert weather_client.last_source_label() == "和风天气"


def test_fallback_when_qweather_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(qweather_client, "weather_3d", lambda loc: None)
    monkeypatch.setattr(open_meteo_client, "weather_3d", lambda loc: [{"date": "2026-09-06"}])
    assert weather_client.weather_3d("116.39,39.90") == [{"date": "2026-09-06"}]
    assert weather_client.last_source_label() == "Open-Meteo"


def test_open_meteo_parses_daily(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "daily": {
            "time": ["2026-09-06", "2026-09-07"],
            "weather_code": [0, 61],
            "temperature_2m_max": [30.1, 26.0],
            "temperature_2m_min": [22.4, 20.5],
        }
    }
    calls: list[str] = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return _Resp(payload)

    monkeypatch.setattr(open_meteo_client, "_http_get", fake_get)
    daily = open_meteo_client.weather_3d("116.39,39.90")
    assert daily[0]["text_day"] == "晴"
    assert daily[1]["text_day"] == "小雨"
    assert daily[0]["temp_max"] == 30.1
    assert "api.open-meteo.com" in calls[0]


def test_open_meteo_rejects_non_coordinate(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("非坐标 location 不应发起请求")

    monkeypatch.setattr(open_meteo_client, "_http_get", _boom)
    assert open_meteo_client.weather_3d("101010100") is None  # 和风 LocationID 不适用本源


def test_open_meteo_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "daily": {
            "time": ["2026-09-06"],
            "weather_code": [2],
            "temperature_2m_max": [30.0],
            "temperature_2m_min": [22.0],
        }
    }
    calls: list[str] = []

    def fake_get(url, params=None, timeout=None):
        calls.append(url)
        return _Resp(payload)

    monkeypatch.setattr(open_meteo_client, "_http_get", fake_get)
    open_meteo_client.weather_3d("116.39,39.90")
    open_meteo_client.weather_3d("116.39,39.90")
    assert len(calls) == 1  # 10 分钟 TTL 内第二次调用命中缓存


def test_open_meteo_enabled_without_key() -> None:
    assert load_api_configs()["open_meteo"].enabled is True  # 免密钥公开服务，恒可用
