from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import amap_client, ticketing
from app.services.metrics import BOOKING_CLICKS
from app.services.travel_context_service import TravelContextService

router = APIRouter(prefix="/api/services", tags=["services"])
travel = TravelContextService()

# CPS 推广位参数：环境变量 FLIGGY_CPS_<名>=<值> 全量注入（P2 商业化，未配置时为直链）
import os as _os

ticketing.configure_cps(
    {k.removeprefix("FLIGGY_CPS_").lower(): v for k, v in _os.environ.items() if k.startswith("FLIGGY_CPS_")}
)

SERVICE_KINDS = {"train", "flight", "attraction", "merchant", "entertainment"}

# 实时窗口结果短缓存（60s）：高德数据本就有分钟级时效，短缓存可削峰且不损失"实时性"口径；
# 键含全部查询参数，避免不同城市/出发地互相污染
_window_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_WINDOW_TTL_SECONDS = 60.0


@router.get("/travel")
def travel_module(destination: str = "北京", origin: str | None = None, days: int = 3) -> dict[str, Any]:
    """toC 出行模块：火车票 / 机票 / 酒店住宿多选项（演示口径；真实票务与酒店 API 未接入，字段留空）。"""
    return {
        "destination": destination,
        "origin": origin,
        "trains": travel.train_tickets(origin, destination),
        "flights": travel.flights(origin, destination),
        "hotels": travel.hotels(destination, max(1, days - 1)),
    }


@router.get("/{kind}")
def service_window(kind: str, destination: str = "北京", origin: str | None = None) -> dict[str, Any]:
    """toC 旅行服务大厅：车票/机票/商家/景点/娱乐五个窗口（演示口径 + 本地计算）。"""
    import time as _time

    if kind not in SERVICE_KINDS:
        raise HTTPException(status_code=400, detail="kind must be train|flight|attraction|merchant|entertainment")
    cache_key = f"{kind}|{destination}|{origin or ''}"
    cached = _window_cache.get(cache_key)
    if cached and _time.monotonic() - cached[0] < _WINDOW_TTL_SECONDS:
        return cached[1]
    result = _dispatch_service_window(kind, origin, destination)
    _window_cache[cache_key] = (_time.monotonic(), result)
    return result


def _dispatch_service_window(kind: str, origin: str | None, destination: str) -> dict[str, Any]:
    # 三级降级（技术方案 §1）：飞猪真实数据优先 → 本地估算/官方渠道 → 诚实空态
    if kind == "train":
        return ticketing.enrich_train_flight(travel.train_tickets(origin, destination), kind, origin, destination)
    if kind == "flight":
        return ticketing.enrich_train_flight(travel.flights(origin, destination), kind, origin, destination)
    if kind == "attraction":
        return ticketing.enrich_attractions(travel.attractions(destination), destination)
    if kind == "merchant":
        base = travel.merchants(destination)
        hotels = ticketing.fliggy_hotels(destination)
        if hotels:
            base["hotels"] = hotels
            base["source"] = "fliggy"
        return base
    return travel.entertainment(destination)


class BookingClickRequest(BaseModel):
    kind: str
    job_id: str | None = None


@router.post("/booking/click")
def booking_click(payload: BookingClickRequest) -> dict[str, str]:
    """预订跳转埋点：CPS 转化归因的粗口径（跳转在浏览器发生，服务端只记点击）。"""
    if payload.kind not in SERVICE_KINDS:
        raise HTTPException(status_code=400, detail="kind must be train|flight|attraction|merchant|entertainment")
    BOOKING_CLICKS.labels(kind=payload.kind).inc()
    return {"status": "ok"}


_city_photo_cache: dict[str, tuple[float, list[dict[str, str]]]] = {}
_CITY_PHOTO_TTL_SECONDS = 3600.0
_last_amap_ts = [0.0]


@router.get("/city/photo")
def city_photo(destination: str = "") -> dict[str, Any]:
    """目的地著名景点实拍图（高德 POI 自带照片，国内可达；未配置 key 或无图返回空 url，前端静默降级）。"""
    import time as _time

    name = (destination or "").strip()
    if not name:
        return {"url": "", "name": ""}
    cached = _city_photo_cache.get(name)
    if cached and _time.monotonic() - cached[0] < _CITY_PHOTO_TTL_SECONDS:
        photos = cached[1]
        return {"url": photos[0]["url"] if photos else "", "name": photos[0]["name"] if photos else "", "photos": photos}
    if not amap_client.is_ready():
        return {"url": "", "name": "", "photos": []}
    # 简单限速：高德个人 key QPS 有限，前端并发拉图会触发限流（被当作无数据）
    elapsed = _time.monotonic() - _last_amap_ts[0]
    if elapsed < 0.4:
        _time.sleep(0.4 - elapsed)
    _last_amap_ts[0] = _time.monotonic()
    try:
        # 两路检索合并：关键字"风景名胜"（大城市场景命中率高）+ 类型码 110000（风景名胜，覆盖面广）
        candidates = [poi for poi in amap_client.search_pois(name, "风景名胜", size=8) if poi.get("photo")]
        if len(candidates) < 2:
            extra = amap_client._get("/v3/place/text", {"city": name, "types": "110000", "offset": 8, "page": 1, "extensions": "all"})
            candidates += [poi for poi in amap_client._parse_pois(extra) if poi.get("photo")]
        if candidates:
            # 按评分排序取前几张：前端每次渲染随机挑一张，避免总是同一张照片
            ranked = sorted(candidates, key=lambda p: float(p.get("rating") or 0), reverse=True)[:6]
            photos = [{"url": poi["photo"], "name": poi.get("name", "")} for poi in ranked]
            _city_photo_cache[name] = (_time.monotonic(), photos)
            return {"url": photos[0]["url"], "name": photos[0]["name"], "photos": photos}
    except Exception:
        pass
    _city_photo_cache[name] = (_time.monotonic(), [])
    return {"url": "", "name": "", "photos": []}
