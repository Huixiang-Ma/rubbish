"""Open-Meteo 客户端：免密钥全球天气灾备源（和风主源失败时切换）。

每日 1 万次免费额度（非商用），带 10 分钟 TTL 缓存控制调用量；
WMO weather_code 映射为中文天气文案，输出结构与 qweather_client.weather_3d
完全一致（date/text_day/text_night/temp_max/temp_min）。
仅支持 "lng,lat"（高德坐标顺序）输入，和风 LocationID 不适用于本源。
"""
from __future__ import annotations

import time
from typing import Any, Callable

import httpx

from app.api_registry import get_api_config

_http_get: Callable[..., httpx.Response] = httpx.get

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 600

# WMO weather interpretation codes（常用档位）→ 中文文案
_WMO_TEXT = {
    0: "晴", 1: "基本晴", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨", 81: "阵雨", 82: "强阵雨",
    85: "阵雪", 86: "阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "雷阵雨伴冰雹",
}


def is_ready() -> bool:
    return get_api_config("open_meteo").enabled


def _weather_text(code: Any) -> str:
    try:
        return _WMO_TEXT.get(int(code), "未知")
    except (TypeError, ValueError):
        return "未知"


def weather_3d(location: str) -> list[dict[str, Any]] | None:
    """未来 3 天预报。location 仅支持 "lng,lat"（高德坐标顺序）；失败返回 None。"""
    config = get_api_config("open_meteo")
    if not config.enabled or "," not in location:
        return None
    lng, _, lat = location.partition(",")
    try:
        float(lng), float(lat)
    except ValueError:
        return None
    cache_key = f"om|{lng},{lat}"
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]
    try:
        response = _http_get(
            f"{config.base_url.rstrip('/')}/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lng,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "forecast_days": 3,
                "timezone": "Asia/Shanghai",
            },
            timeout=config.timeout_seconds,
        )
        data = response.json()
    except Exception:
        return None
    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    if not dates:
        _cache[cache_key] = (now + CACHE_TTL_SECONDS, None)
        return None
    codes = daily.get("weather_code") or []
    temp_max = daily.get("temperature_2m_max") or []
    temp_min = daily.get("temperature_2m_min") or []
    result = [
        {
            "date": dates[i],
            "text_day": _weather_text(codes[i]) if i < len(codes) else "未知",
            "text_night": _weather_text(codes[i]) if i < len(codes) else "未知",
            "temp_max": temp_max[i] if i < len(temp_max) else "",
            "temp_min": temp_min[i] if i < len(temp_min) else "",
        }
        for i in range(len(dates))
    ]
    _cache[cache_key] = (now + CACHE_TTL_SECONDS, result)
    return result
