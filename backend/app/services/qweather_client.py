"""和风天气客户端：实时+逐日预报（v7/weather/3d）。

密钥由 api_registry 统一管理（QWEATHER_API_KEY）；未配置或失败返回 None，业务侧回退演示文案。
坐标来源建议先用 amap_client.geocode 把城市名转成 "lng,lat"。
"""
from __future__ import annotations

import time
from typing import Any, Callable

import httpx

from app.api_registry import get_api_config

_http_get: Callable[..., httpx.Response] = httpx.get

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 600


def is_ready() -> bool:
    return get_api_config("qweather").enabled


def _get(path: str, params: dict[str, Any]) -> Any | None:
    config = get_api_config("qweather")
    if not config.enabled:
        return None
    cache_key = path + "|" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]
    # base_url 归一化：用户从控制台复制的专属 Host 可能带或不带 /v7 前缀，
    # 而接口 path 均为 "/weather/3d" 形式，统一补齐避免整站 404。
    base_url = config.base_url.rstrip("/")
    if not base_url.endswith("/v7"):
        base_url += "/v7"
    try:
        response = _http_get(
            f"{base_url}{path}",
            params={**params, "key": config.api_key},
            headers={"X-QW-Api-Key": config.api_key},
            timeout=config.timeout_seconds,
        )
        data = response.json()
    except Exception:
        return None
    if str(data.get("code")) != "200":
        _cache[cache_key] = (now + CACHE_TTL_SECONDS, None)
        return None
    _cache[cache_key] = (now + CACHE_TTL_SECONDS, data)
    return data


def weather_3d(location: str) -> list[dict[str, Any]] | None:
    """未来 3 天预报。location 支持 "lng,lat" 或和风 LocationID。失败返回 None。"""
    data = _get("/weather/3d", {"location": location})
    if not data or not data.get("daily"):
        return None
    return [
        {
            "date": day.get("fxDate", ""),
            "text_day": day.get("textDay", ""),
            "text_night": day.get("textNight", ""),
            "temp_max": day.get("tempMax", ""),
            "temp_min": day.get("tempMin", ""),
        }
        for day in data["daily"]
    ]
