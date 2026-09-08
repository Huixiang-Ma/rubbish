"""高德开放平台客户端：地理编码 / POI 检索（景点、餐饮）/ 路径规划。

- 密钥与启停由 api_registry 统一管理（AMAP_API_KEY），未配置时所有方法返回 None/[]，业务侧回退演示口径。
- 结果带内存缓存（默认 10 分钟），控制免费额度消耗。
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import httpx

from app.api_registry import get_api_config

_http_get: Callable[..., httpx.Response] = httpx.get

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 600


def is_ready() -> bool:
    return get_api_config("amap").enabled


def _get(path: str, params: dict[str, Any]) -> Any | None:
    config = get_api_config("amap")
    if not config.enabled:
        return None
    cache_key = path + "|" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]
    data: Any | None = None
    for attempt in range(2):  # SSL/连接瞬时抖动重试一次
        try:
            response = _http_get(
                f"{config.base_url}{path}",
                params={**params, "key": config.api_key},
                timeout=config.timeout_seconds,
            )
            data = response.json()
            break
        except Exception:
            if attempt == 0:
                time.sleep(0.5)
                continue
            return None  # 网络失败不缓存：瞬时抖动不应放大成 10 分钟数据空窗
    if str(data.get("status")) != "1":
        _cache[cache_key] = (now + 60, None)  # 业务失败（限流等）仅短缓存 60 秒
        return None
    _cache[cache_key] = (now + CACHE_TTL_SECONDS, data)
    return data


def _to_coord(location: str) -> tuple[float, float] | None:
    try:
        lng, lat = str(location).split(",")
        return float(lng), float(lat)
    except (ValueError, AttributeError):
        return None


def ip_location() -> dict[str, Any] | None:
    """高德 IP 定位（城市级）：浏览器定位不可用/不可信时的兜底，返回矩形中心与城市名。"""
    data = _get("/v3/ip", {})
    if not data or data.get("rectangle") is None:
        return None
    try:
        lng1, lat1 = _to_coord(data["rectangle"].split(";")[0])
        lng2, lat2 = _to_coord(data["rectangle"].split(";")[1])
        city = data.get("city")
        if isinstance(city, list):
            city = city[0] if city else ""
        return {
            "province": data.get("province") or "",
            "city": city,
            "lat": round((lat1 + lat2) / 2, 6),
            "lng": round((lng1 + lng2) / 2, 6),
            "precision": "city",
        }
    except (ValueError, IndexError):
        return None


def geocode(address: str) -> dict[str, Any] | None:
    """地理编码：地址 → 经纬度 + 行政区信息。未配置/失败返回 None。"""
    data = _get("/v3/geocode/geo", {"address": address})
    if not data or not data.get("geocodes"):
        return None
    first = data["geocodes"][0]
    coord = _to_coord(first.get("location", ""))
    if not coord:
        return None
    lng, lat = coord
    city = first.get("city") or ""
    if isinstance(city, list):
        city = city[0] if city else ""
    return {"lng": lng, "lat": lat, "adcode": first.get("adcode", ""), "city": city}


def _extract_open_time(poi: dict[str, Any]) -> str:
    """开放时间在高德返回中可能出现在多个字段（v3 extensions=all），逐个兜底；均无则空串。"""
    biz_ext = poi.get("biz_ext") or {}
    deep_info = poi.get("deep_info") if isinstance(poi.get("deep_info"), dict) else {}
    for value in (
        poi.get("opentime"),
        poi.get("open_time"),
        biz_ext.get("open_time"),
        biz_ext.get("opentime"),
        deep_info.get("opentime"),
    ):
        if value:
            return str(value)
    return ""


def _extract_rating(poi: dict[str, Any]) -> str:
    """高德 POI 评分（biz_ext.rating），无则空串。"""
    biz_ext = poi.get("biz_ext") or {}
    rating = biz_ext.get("rating") or poi.get("rating") or ""
    return str(rating) if rating else ""


def _parse_pois(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not data:
        return []
    pois = []
    for poi in data.get("pois", []):
        coord = _to_coord(poi.get("location", ""))
        if not coord:
            continue
        lng, lat = coord
        pois.append(
            {
                "name": poi.get("name", ""),
                "lng": lng,
                "lat": lat,
                "address": poi.get("address", "") or "",
                "type": poi.get("type", "") or "",
                "open_time": _extract_open_time(poi),
                "rating": _extract_rating(poi),
                # 高德 POI 自带实拍图（extensions=all）；取第一张，供前端展示目的地景点
                "photo": ((poi.get("photos") or [{}])[0].get("url") or "") if isinstance(poi.get("photos"), list) else "",
            }
        )
    return pois


def search_pois(city: str, keywords: str, size: int = 10) -> list[dict[str, Any]]:
    """城市内关键字 POI 检索（景点/餐饮等），extensions=all 携带营业时间等深度信息。"""
    return _parse_pois(
        _get("/v3/place/text", {"city": city, "keywords": keywords, "offset": size, "page": 1, "extensions": "all"})
    )


def around_pois(lng: float, lat: float, types: str = "", keywords: str = "", radius: int = 3000, size: int = 8) -> list[dict[str, Any]]:
    """周边 POI：可按类型（如餐饮 050000 / 住宿 100000）或关键字（如 停车场）检索，extensions=all 携带深度信息。"""
    params: dict[str, Any] = {"location": f"{lng},{lat}", "radius": radius, "offset": size, "page": 1, "extensions": "all"}
    if types:
        params["types"] = types
    if keywords:
        params["keywords"] = keywords
    return _parse_pois(_get("/v3/place/around", params))


def route_between(origin: str, dest: str, city: str = "北京") -> dict[str, Any] | None:
    """路径规划：transit（公交地铁，需城市名）+ driving（打车）时长与驾车距离，两路并发请求。失败返回 None。"""
    with ThreadPoolExecutor(max_workers=2) as pool:
        transit_future = pool.submit(
            _get, "/v3/direction/transit/integrated", {"origin": origin, "destination": dest, "city": city}
        )
        driving_future = pool.submit(_get, "/v3/direction/driving", {"origin": origin, "destination": dest})
        transit_data = transit_future.result()
        driving_data = driving_future.result()
    if not transit_data and not driving_data:
        return None
    transit_minutes: int | None = None
    driving_minutes: int | None = None
    distance_km: float | None = None
    try:
        transits = transit_data["route"]["transits"]
        if transits:
            transit_minutes = round(int(transits[0]["duration"]) / 60)
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    try:
        path = driving_data["route"]["paths"][0]
        driving_minutes = round(int(path["duration"]) / 60)
        distance_km = round(int(path["distance"]) / 1000, 1)
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    if transit_minutes is None and driving_minutes is None:
        return None
    return {
        "transit_minutes": transit_minutes,
        "driving_minutes": driving_minutes,
        "distance_km": distance_km,
    }
