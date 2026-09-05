"""P1.1 真实票务三级降级：飞猪 MCP（真实班次/报价）→ 本地估算/官方渠道指引 → 诚实空态。

设计（详见 技术方案_完整落地.md §1）：
- fliggy_client 未配置 key（is_ready()=False）时整层直通本地口径，零开销；
- 熔断器：连续 3 次失败或空结果 → 打开 60 秒，期间直接走本地口径，保护调用配额；
- 响应契约：窗口结果新增顶层 "source": "fliggy" | "local"；fliggy 条目带 booking_url（CPS 参数由后端统一追加）；
- 字段映射失败（缺班次号/名称等关键字段）的条目直接丢弃——宁缺毋假。
- ⚠️ MCP 工具返回结构以 backend/scripts/probe_fliggy.py 的探测结果为准；以下映射按官方 flyai-mcp
  常见字段（trainNo/jumpUrl/price 等）写为容错式提取，探测后可在此精确化。
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

from app.services import fliggy_client
from app.services.metrics import FLIGGY_REQUESTS

_BREAKER_THRESHOLD = 3
_BREAKER_SECONDS = 60.0


class Breaker:
    """进程内熔断器：连续失败 N 次后打开一段时间，保护真实数据源配额。"""

    def __init__(self) -> None:
        self.failures = 0
        self.opened_until = 0.0

    def allow(self) -> bool:
        return time.monotonic() >= self.opened_until

    def record(self, ok: bool) -> None:
        if ok:
            self.failures = 0
            return
        self.failures += 1
        if self.failures >= _BREAKER_THRESHOLD:
            self.opened_until = time.monotonic() + _BREAKER_SECONDS
            self.failures = 0


_breaker = Breaker()

# CPS 推广位参数（P2 商业化）：从 .env 注入，前端不感知
_CPS_PARAMS: dict[str, str] = {}


def configure_cps(params: dict[str, str]) -> None:
    _CPS_PARAMS.clear()
    _CPS_PARAMS.update({k: v for k, v in params.items() if v})


def _booking_url(raw: Any) -> str:
    url = str(raw or "").strip()
    if not url.startswith(("http://", "https://")):
        return ""
    if _CPS_PARAMS:
        sep = "&" if "?" in url else "?"
        url = url + sep + "&".join(f"{k}={quote(v)}" for k, v in _CPS_PARAMS.items())
    return url


def _pick(item: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        v = item.get(k)
        if v not in (None, ""):
            return v
    return ""


def _find_items(data: Any, depth: int = 0) -> list[dict[str, Any]]:
    """在 MCP 返回里递归找第一个非空 list[dict]（字段位置以 probe 探测结果为准）。"""
    if depth > 4:
        return []
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        for key in ("itemList", "list", "items", "trains", "flights", "hotelList", "data", "result", "services"):
            if key in data:
                found = _find_items(data[key], depth + 1)
                if found:
                    return found
        for v in data.values():
            found = _find_items(v, depth + 1)
            if found:
                return found
    return []


def _rows_train_flight(items: list[dict[str, Any]], is_train: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items[:8]:
        if is_train:
            no = str(_pick(item, "trainNo", "train_no", "trainCode", "train_number", "no"))
        else:
            no = str(_pick(item, "flightNo", "flight_no", "flightCode", "flight_number", "no"))
        if not no:
            continue  # 无班次号的脏数据丢弃
        rows.append(
            {
                "train_no" if is_train else "flight_no": no,
                "tag": str(_pick(item, "tag", "trainType", "seatClass", "cabin", "desc") or ("车次" if is_train else "航班")),
                "departure": str(_pick(item, "depTime", "departureTime", "departure", "dep", "startTime")),
                "arrival": str(_pick(item, "arrTime", "arrivalTime", "arrive", "endTime")),
                "duration": str(_pick(item, "duration", "runTime", "lasting", "costTime")),
                "seat": str(_pick(item, "seatName", "seat", "seatType", "cabin") or ("二等座" if is_train else "经济舱")),
                "price": _pick(item, "price", "ticketPrice", "minPrice", "lowestPrice", "priceValue") or "",
                "status": str(_pick(item, "ticketStatus", "status", "stock") or "有票"),
                "booking_url": _booking_url(_pick(item, "jumpUrl", "bookingUrl", "detailUrl", "url")),
            }
        )
    return rows


def _fliggy_call(kind: str, tool: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    """带熔断与指标的工具调用；返回原始条目列表（空=失败/无数据）。"""
    if not fliggy_client.is_ready() or not _breaker.allow():
        FLIGGY_REQUESTS.labels(kind=kind, result="breaker").inc()
        return []
    data = fliggy_client.call_tool(tool, arguments)
    items = _find_items(data)
    ok = bool(items)
    _breaker.record(ok)
    FLIGGY_REQUESTS.labels(kind=kind, result="ok" if ok else "empty").inc()
    return items


def enrich_train_flight(base: dict[str, Any], kind: str, origin: str | None, destination: str) -> dict[str, Any]:
    """大交通窗口：本地建议（guide）保留，tickets/flights 有飞猪真实数据则覆盖。"""
    is_train = kind == "train"
    args = {"origin": (origin or "").removesuffix("市"), "destination": destination.removesuffix("市")}
    items = _fliggy_call(kind, "search_train" if is_train else "search_flight", args)
    base.setdefault("source", "local")
    if not items:
        return base
    rows = _rows_train_flight(items, is_train)
    if not rows:
        return base
    key = "tickets" if is_train else "flights"
    base[key] = rows
    base["source"] = "fliggy"
    base["note"] = "来源：飞猪AI 实时检索；价格与库存以供应商页面公示为准。"
    return base


def enrich_attractions(base: dict[str, Any], destination: str) -> dict[str, Any]:
    """景点窗口：高德 POI 为主；命中同名景点时补飞猪预订链接与榜单信息。"""
    base.setdefault("source", "local")
    items = _fliggy_call("attraction", "search_poi", {"cityName": destination.removesuffix("市"), "keyword": "景点"})
    if not items:
        return base
    by_name = {str(i.get("name")): i for i in items if i.get("name")}
    for a in base.get("attractions") or []:
        hit = by_name.get(str(a.get("name"))) or {}
        url = _booking_url(hit.get("jumpUrl") or hit.get("bookingUrl"))
        if url:
            a["booking_url"] = url
        if hit.get("ticketInfo"):
            a["ticket_info"] = hit["ticketInfo"]
    if any(a.get("booking_url") for a in base.get("attractions") or []):
        base["source"] = "fliggy"
    return base


def fliggy_hotels(destination: str) -> list[dict[str, Any]]:
    """酒店（本地商家窗口的住宿档）：飞猪真实酒店列表；失败返回空。"""
    items = _fliggy_call("merchant", "search_hotel", {"destName": destination.removesuffix("市")})
    rows: list[dict[str, Any]] = []
    for item in items[:8]:
        name = str(_pick(item, "name", "hotelName", "title"))
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "category": str(_pick(item, "starName", "star", "level", "category") or "酒店"),
                "score": _pick(item, "score", "rating", "commentScore", "dsaScore") or "",
                "price_hint": (f"¥{_pick(item, 'price', 'minPrice', 'lowestPrice')}" if _pick(item, "price", "minPrice", "lowestPrice") else "以供应商页面为准"),
                "position": str(_pick(item, "position", "address", "location", "regionName")),
                "booking_url": _booking_url(_pick(item, "jumpUrl", "bookingUrl", "detailUrl", "url")),
            }
        )
    return rows
