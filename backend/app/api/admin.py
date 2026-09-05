import csv
import io
import json

from fastapi import APIRouter, Response

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
