import json
from pathlib import Path
from typing import Any

from app.models.states import JobStatus
from app.services.checkpoint_store import CheckpointStore
from app.services.paths import DATA_ROOT

TERMINAL_STATUSES = {
    JobStatus.COMPLETED.value,
    JobStatus.FAILED.value,
    JobStatus.CORRUPTED.value,
    JobStatus.REPLAN_REQUIRED.value,
}

HOLD_STATUSES = {
    JobStatus.WAITING_BUDGET_APPROVAL.value,
    JobStatus.WAITING_SAFETY_REVIEW.value,
    JobStatus.WAITING_RATE_LIMIT.value,
    JobStatus.WAITING_PARSE_REVIEW.value,
    JobStatus.RECOVERY_REQUIRED.value,
}


def recover_pending_jobs(queue_client: Any) -> dict[str, Any]:
    """进程重启后扫描本地 checkpoint，把未完成任务重新入队。

    对应方案 6.4 恢复规则：QUEUED/RUNNING 从 resume_from 继续调度；
    挂起态等人工介入；终态跳过；state.json 损坏的进入 RECOVERY_REQUIRED。
    """
    store = CheckpointStore()
    recovered: list[str] = []
    corrupted: list[str] = []
    if not DATA_ROOT.exists():
        return {"recovered": recovered, "corrupted": corrupted}
    for job_path in sorted(DATA_ROOT.iterdir()):
        if not job_path.is_dir():
            continue
        job_id = job_path.name
        state_path = job_path / "state.json"
        if not state_path.exists():
            continue
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _mark_recovery_required(store, job_id)
            corrupted.append(job_id)
            continue
        expected_hash = _read_sidecar_hash(state_path)
        if expected_hash is not None and not store.writer.verify_sha256(state_path, expected_hash):
            state["status"] = JobStatus.RECOVERY_REQUIRED.value
            state["error"] = "state.json sha256 校验失败，可能被篡改或损坏"
            store.save(job_id, state)
            corrupted.append(job_id)
            continue
        status = state.get("status")
        if status in TERMINAL_STATUSES or status in HOLD_STATUSES:
            continue
        queue_client.enqueue(job_id)
        recovered.append(job_id)
    return {"recovered": recovered, "corrupted": corrupted}


def _read_sidecar_hash(state_path: Path) -> str | None:
    hash_path = state_path.with_suffix(state_path.suffix + ".sha256")
    if not hash_path.exists():
        return None
    return hash_path.read_text(encoding="utf-8").strip()


def _mark_recovery_required(store: CheckpointStore, job_id: str) -> None:
    try:
        state = store.load(job_id)
    except Exception:
        state = {"job_id": job_id, "user_input": {}}
    state["status"] = JobStatus.RECOVERY_REQUIRED.value
    state["error"] = "state.json 无法解析，等待人工恢复"
    store.save(job_id, state)
