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
    """（保留兜底）按班次号键名容错提取；flight 实测结构见 _rows_flight。"""
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


def _fmt_duration(minutes: Any) -> str:
    try:
        m = int(str(minutes))
        return f"{m // 60}小时{m % 60:02d}分" if m % 60 else f"{m // 60}小时"
    except (TypeError, ValueError):
        return str(minutes or "")


def _rows_flight(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """飞猪 search_flight 实测结构（docs/飞猪MCP探测.md）：
    data.itemList[].jumpUrl = 预订链接；journeys[0].segments[0] = 航段详情；ticketPrice 需报价权限，通常为空。"""
    rows: list[dict[str, Any]] = []
    for item in items[:8]:
        journeys = item.get("journeys") or []
        if not journeys:
            continue
        journey = journeys[0]
        seg = (journey.get("segments") or [{}])[0]
        no = str(_pick(seg, "marketingTransportNo", "flightNo", "flight_no") or "")
        if not no:
            continue
        airline = str(_pick(seg, "marketingTransportName", "airline") or "")
        dep_station = str(_pick(seg, "depStationName") or "")
        arr_station = str(_pick(seg, "arrStationName") or "")
        dep_term = str(_pick(seg, "depTerm") or "")
        rows.append(
            {
                "flight_no": no,
                "tag": (airline + " · " if airline else "") + str(_pick(journey, "journeyType") or "直达"),
                "departure": " ".join(x for x in [str(_pick(seg, "depDateTime")), dep_station + (f" T{dep_term}" if dep_term else "")] if x and x != "None"),
                "arrival": " ".join(x for x in [str(_pick(seg, "arrDateTime")), arr_station] if x and x != "None"),
                "duration": _fmt_duration(journey.get("totalDuration")),
                "seat": str(_pick(seg, "seatClassName") or "经济舱"),
                "price": _pick(seg, "ticketPrice") or _pick(item, "ticketPrice") or "",
                "status": "可预订" if item.get("jumpUrl") else "查询班次",
                "booking_url": _booking_url(item.get("jumpUrl")),
            }
        )
    return rows


def enrich_train_flight(base: dict[str, Any], kind: str, origin: str | None, destination: str) -> dict[str, Any]:
    """大交通窗口：本地建议（guide）保留，flights 有飞猪真实数据则覆盖；火车票无搜索工具，维持 12306 官方渠道口径。"""
    is_train = kind == "train"
    base.setdefault("source", "local")
    if is_train:
        return base  # 探测结论：飞猪 MCP 无火车票搜索工具（train/12306 仅代理商履约接口）
    items = _fliggy_call(kind, "search_flight", {"origin": (origin or "").removesuffix("市"), "destination": destination.removesuffix("市")})
    if not items:
        return base
    rows = _rows_flight(items)
    if not rows:
        return base
    base["flights"] = rows
    base["source"] = "fliggy"
    base["note"] = "来源：飞猪AI 实时检索；票价需在供应商页面查询（未展示的价格以对方公示为准）。"
    return base


def enrich_attractions(base: dict[str, Any], destination: str) -> dict[str, Any]:
    """景点窗口：高德 POI 为主；命中同名景点补飞猪预订链接；高德没覆盖的飞猪榜单 POI 追加进列表。"""
    base.setdefault("source", "local")
    items = _fliggy_call("attraction", "search_poi", {"cityName": destination.removesuffix("市"), "keyword": "景点"})
    if not items:
        return base
    by_name = {str(i.get("name")): i for i in items if i.get("name")}
    linked = 0
    seen = {str(a.get("name")) for a in base.get("attractions") or []}
    for a in base.get("attractions") or []:
        hit = by_name.get(str(a.get("name"))) or {}
        url = _booking_url(hit.get("jumpUrl"))
        if url:
            a["booking_url"] = url
            linked += 1
        if hit.get("ticketInfo"):
            a["ticket_info"] = hit["ticketInfo"]
    # 高德没覆盖的飞猪 POI（带预订链接与地址）追加展示，去重后最多补 4 个
    added = 0
    for name, poi in by_name.items():
        if name in seen or added >= 4:
            continue
        if not poi.get("jumpUrl"):
            continue
        base["attractions"].append(
            {
                "name": name,
                "tags": [poi["category"]] if poi.get("category") else [],
                "open_time": "以景区公告为准",
                "ticket_price": 0,
                "visit_minutes": 120,
                "address": str(poi.get("address") or ""),
                "booking_url": _booking_url(poi.get("jumpUrl")),
            }
        )
        seen.add(name)
        added += 1
        linked += 1
    if linked:
        base["source"] = "fliggy"
        base["note"] = "来源：高德实时 POI + 飞猪AI 榜单（带预订链接）；门票以景区公示为准。"
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
