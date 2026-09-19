import csv
import io
import json

from fastapi import APIRouter, Query, Response

from app.models.states import JobStatus
from app.services import job_index
from app.services.checkpoint_store import CheckpointStore
from app.services.paths import DATA_ROOT

router = APIRouter(prefix="/api", tags=["admin"])

store = CheckpointStore()

PENDING_STATUSES = {
    JobStatus.WAITING_BUDGET_APPROVAL.value,
    JobStatus.WAITING_SAFETY_REVIEW.value,
}


def _iter_states():
    yield from job_index.iter_states(DATA_ROOT)


@router.get("/approvals/pending")
def pending_approvals(tenant: str | None = None) -> dict:
    """B2 审核台：聚合当前挂起待人工处理的任务队列（可按租户过滤）。"""
    items = []
    for state in _iter_states():
        if state.get("status") not in PENDING_STATUSES:
            continue
        if tenant and state.get("tenant") != tenant:
            continue
        user_input = state.get("user_input", {})
        items.append(
            {
                "job_id": state.get("job_id"),
                "status": state.get("status"),
                "error": state.get("error"),
                "resume_from": state.get("resume_from"),
                "version": state.get("version", 1),
                "destination": user_input.get("destination"),
                "origin": user_input.get("origin"),
                "days": user_input.get("days"),
                "budget": user_input.get("budget"),
                "customer": state.get("customer"),
                "updated_at": state.get("updated_at"),
            }
        )
    items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return {"total": len(items), "items": items}


@router.get("/audit/export.csv")
def export_audit_csv() -> Response:
    """B4 合规审计导出：谁/何时/改了什么（详情 JSON），UTF-8 BOM 兼容 Excel。"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["job_id", "created_at", "action", "operator", "detail"])
    events_by_job = job_index.audit_events(DATA_ROOT)
    for job_id, events in events_by_job.items():
        for event in events:
            detail = {k: v for k, v in event.items() if k not in ("job_id", "created_at", "action", "operator")}
            writer.writerow(
                [
                    job_id,
                    event.get("created_at", ""),
                    event.get("action", ""),
                    event.get("operator", ""),
                    json.dumps(detail, ensure_ascii=False),
                ]
            )
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )


@router.get("/feedbacks")
def list_feedbacks(kind: str | None = None, customer: str | None = None, limit: int = 100) -> dict:
    """客户之声：从各任务审计日志聚合反馈事件（好评/投诉），演示级口径。"""
    states = {state.get("job_id"): state for state in _iter_states()}
    items: list[dict] = []
    praise = complaint = 0
    for job_id, events in job_index.audit_events(DATA_ROOT).items():
        state = states.get(job_id, {})
        for event in events:
            if event.get("action") != "feedback":
                continue
            event_kind = event.get("kind", "praise")
            if kind and event_kind != kind:
                continue
            if customer and state.get("customer") != customer:
                continue
            if event_kind == "praise":
                praise += 1
            else:
                complaint += 1
            items.append(
                {
                    "job_id": job_id,
                    "created_at": event.get("created_at", ""),
                    "kind": event_kind,
                    "operator": event.get("operator", "-"),
                    "content": event.get("content", ""),
                    "customer": state.get("customer"),
                    "destination": (state.get("user_input") or {}).get("destination"),
                }
            )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    items = items[: max(1, min(limit, 500))]
    return {"total": len(items), "praise_count": praise, "complaint_count": complaint, "items": items}


@router.get("/stats/overview")
def stats_overview(tenant: str | None = None) -> dict:
    """B6 经营分析看板：聚合真实任务数据（演示级）。"""
    daily: dict[str, int] = {}
    status_counter: dict[str, int] = {}
    customer_counter: dict[str, int] = {}
    total = 0
    completed = 0
    for state in _iter_states():
        if tenant and state.get("tenant") != tenant:
            continue
        total += 1
        status = state.get("status", "UNKNOWN")
        status_counter[status] = status_counter.get(status, 0) + 1
        if status == JobStatus.COMPLETED.value:
            completed += 1
        day = str(state.get("created_at", ""))[:10]
        if day:
            daily[day] = daily.get(day, 0) + 1
        customer = state.get("customer") or "未归属"
        customer_counter[customer] = customer_counter.get(customer, 0) + 1
    return {
        "total": total,
        "completed_rate": round(completed / total, 4) if total else None,
        "daily_created": [{"date": day, "count": count} for day, count in sorted(daily.items())][-30:],
        "status_distribution": sorted(status_counter.items(), key=lambda pair: pair[1], reverse=True),
        "customers": sorted(customer_counter.items(), key=lambda pair: pair[1], reverse=True)[:8],
        "tenant": tenant,
    }


# ---------- 数据智能闭环：价格时效环（环5） + POI 批量拉取（素材自动化） ----------


def _catalog_std_price(name: str) -> tuple[int, str] | None:
    """按名称互相包含匹配标品库，返回 (标准票价, 标品名)。取 skus 首个非零价（成人口径）。"""
    from app.services import material_store

    for p in material_store.product_rows():
        pname = str(p.get("name") or "")
        if p.get("category") not in ("景点", "文化") or not pname:
            continue
        if pname in name or name in pname:
            prices = [int(s.get("price") or 0) for s in (p.get("skus") or []) if s.get("price")]
            price = next((x for x in prices if x > 0), int(p.get("price_min") or 0))
            return price, pname
    return None


@router.get("/stats/price-drift")
def price_drift(job_id: str | None = None) -> dict:
    """价格时效环：任务行程实采票面价 vs 标品库标准票 → 漂移清单（实时计算不落盘）。

    默认取最近一个 COMPLETED 任务。票面价来自高德/静态/标品回退链，标品价来自 skus 成人价。
    """
    states = [s for s in _iter_states() if s.get("status") == JobStatus.COMPLETED.value]
    states.sort(key=lambda s: str(s.get("updated_at") or ""), reverse=True)
    if job_id:
        states = [s for s in states if s.get("job_id") == job_id]
    if not states:
        return {"total": 0, "items": [], "note": "暂无已完成任务"}
    state = states[0]
    jid = state.get("job_id")
    b_rel = (state.get("agent_outputs") or {}).get("Budget")
    budget_payload: dict = {}
    if b_rel:
        try:
            raw = (DATA_ROOT / jid / b_rel).read_text(encoding="utf-8")
            budget_payload = (json.loads(raw.splitlines()[-1])).get("payload", {})
        except Exception:
            budget_payload = {}
    try:
        itin_rel = (state.get("agent_outputs") or {}).get("Itinerary")
        output = json.loads((DATA_ROOT / jid / itin_rel).read_text(encoding="utf-8"))
        itinerary = output.get("payload", {}).get("itinerary") or []
    except Exception:
        itinerary = []

    items: list[dict] = []
    checked = 0
    for day in itinerary:
        for it in day.get("items", []):
            spot = it.get("spot") or {}
            name = str(spot.get("name") or "").strip()
            used = int(spot.get("ticket_price") or 0)
            if not name or used <= 0:
                continue
            checked += 1
            match = _catalog_std_price(name)
            if match is None:
                items.append({"spot": name, "used_price": used, "catalog_price": None,
                              "catalog_name": "", "note": "标品库无对应素材（未覆盖）"})
            else:
                cat_price, cat_name = match
                if abs(cat_price - used) > max(2, int(cat_price * 0.1)):
                    items.append({"spot": name, "used_price": used, "catalog_price": cat_price,
                                  "catalog_name": cat_name,
                                  "note": f"漂移 {cat_price - used:+d} 元，建议核对素材价格"})
    return {"job_id": jid, "checked": checked, "total": len(items), "items": items,
            "budget_tickets": budget_payload.get("budget_breakdown", {}).get("tickets")}


@router.get("/stats/poi-candidates")
def poi_candidates(city: str = Query(..., min_length=1)) -> dict:
    """素材自动化：按城市拉取高德 POI 候选（含静态/标品票价回退），供批量生成素材草稿。"""
    from app.services.scenic_spot_service import ScenicSpotService
    from app.services import material_store

    spots = ScenicSpotService().recommend(city, [], limit=12)
    existing = {str(p.get("name") or "") for p in material_store.product_rows()}
    items = []
    for s in spots:
        name = str(s.get("name") or "")
        if not name:
            continue
        dup = any(name in e or e in name for e in existing)
        items.append({
            "name": name, "city": city, "category": "景点",
            "price": s.get("ticket_price", 0),
            "visit_minutes": s.get("visit_minutes", 120),
            "open_time": s.get("open_time", ""),
            "rating": s.get("rating", ""),
            "tags": s.get("tags", [])[:3],
            "description": f"{name}（{city}）。开放时间 {s.get('open_time', '以景区公告为准')}。"
                           f"建议游玩 {s.get('visit_minutes', 120)} 分钟。",
            "duplicate": dup,
        })
    return {"city": city, "total": len(items), "items": items}
