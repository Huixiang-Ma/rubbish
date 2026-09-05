from typing import Any

from fastapi import APIRouter

from app.services import job_index
from app.services.paths import DATA_ROOT
from app.services.safety_service import aggregate_safety_events

router = APIRouter(prefix="/api/safety", tags=["safety"])


@router.get("/summary")
def safety_summary() -> dict[str, Any]:
    summary = aggregate_safety_events(DATA_ROOT, events_by_job=job_index.audit_events(DATA_ROOT))
    summary["note"] = "仅统计当前 DATA_ROOT 下的审计日志，非跨实例持久化看板。"
    return summary
