"""工单 7 · 运行态强干预（Memory Mutator）：外部/人工直接修正运行中任务的内部 State。

安全三件套：
- 鉴权：API 层 require_role("supervisor","admin")（AUTH_ENABLED 时强制 Bearer）；
- 并发：复用 distributed 的 Redis 分布式锁（SETNX），未配 Redis 时进程内锁兜底；
- 原子：version 校验 + CheckpointStore 原子写 + version++，并发冲突返回 409。

防脏读语义：PlanProcessor 在每个核心节点边界 re-load state（mark_node_done 落盘后
把返回 state 写回局部变量；本 mutator 修改的是 state.json 持久层）。为了让「运行中」
任务立即感知干预，mutator 额外把干预事件写进 state["interventions"] 队列字段；
管线在下一节点边界消费该队列：热替换 context["user_input"] 并 append_audit。
"""
from __future__ import annotations

import json
from typing import Any

import threading

from app.services.checkpoint_store import CheckpointStore
from app.services.distributed import distributed_lock
from app.services.pg_mirror import pg_mirror
from app.services.queue_client import queue_client

_process_locks: dict[str, threading.Lock] = {}
_process_guard = threading.Lock()


def _job_lock(job_id: str) -> threading.Lock:
    with _process_guard:
        return _process_locks.setdefault(job_id, threading.Lock())

_ALLOWED_FIELDS = {
    "constraints",      # 追加/删除约束（最常用：过敏禁忌、避免早起）
    "budget",           # 预算改写
    "preferences",      # 偏好增删
    "resume_from",      # 恢复锚点校准（挂起任务）
    "mood",             # 心情词（仅 QUEUED 态有意义）
}
_INTERVENTION_DDL = """
    CREATE TABLE IF NOT EXISTS memory_interventions (
        id BIGSERIAL PRIMARY KEY,
        job_id TEXT NOT NULL,
        thread_id TEXT,
        operator TEXT,
        field TEXT NOT NULL,
        old_value JSONB,
        new_value JSONB,
        reason TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """
_inter_lock = __import__("threading").Lock()
_inter_mem: list[dict[str, Any]] = []
_inter_seq = 0


def _ensure_interventions_table() -> None:
    if pg_mirror.enabled:
        with pg_mirror.engine.begin() as conn:
            conn.execute(__import__("sqlalchemy").text(_INTERVENTION_DDL))


def _record_intervention(job_id: str, operator: str, field: str,
                         old: Any, new: Any, reason: str, thread_id: str | None = None) -> int:
    global _inter_seq
    if pg_mirror.enabled:
        import sqlalchemy

        with pg_mirror.engine.begin() as conn:
            row = conn.execute(
                sqlalchemy.text(
                    "INSERT INTO memory_interventions (job_id, thread_id, operator, field, old_value, new_value, reason) "
                    "VALUES (:j, :th, :o, :f, CAST(:ov AS JSONB), CAST(:nv AS JSONB), :re) RETURNING id"
                ),
                {"j": job_id, "th": thread_id, "o": operator, "f": field,
                 "ov": json.dumps(old, ensure_ascii=False, default=str),
                 "nv": json.dumps(new, ensure_ascii=False, default=str), "re": reason},
            )
            return row.scalar_one()
    with _inter_lock:
        _inter_seq += 1
        _inter_mem.append({"id": _inter_seq, "job_id": job_id, "field": field,
                           "old": old, "new": new, "operator": operator, "reason": reason})
        return _inter_seq


def list_interventions(job_id: str) -> list[dict[str, Any]]:
    if pg_mirror.enabled:
        import sqlalchemy

        with pg_mirror.engine.connect() as conn:
            rows = conn.execute(
                sqlalchemy.text(
                    "SELECT field, old_value, new_value, operator, reason, created_at "
                    "FROM memory_interventions WHERE job_id=:j ORDER BY id DESC LIMIT 50"
                ),
                {"j": job_id},
            ).mappings().all()
            return [dict(r) for r in rows]
    with _inter_lock:
        return [dict(t) for t in reversed(_inter_mem) if t["job_id"] == job_id][:50]


def apply_intervention(store: CheckpointStore, job_id: str, patch: dict[str, Any],
                       operator: str, reason: str, base_version: int) -> dict[str, Any]:
    """对运行中/挂起任务执行受控字段干预；返回 {applied, changes}，冲突抛 ValueError(409)。"""
    state = store.load(job_id)
    if state.get("version", 1) != base_version:
        raise ValueError("VERSION_CONFLICT")
    status = state.get("status")
    if status not in {"RUNNING", "WAITING_BUDGET_APPROVAL", "WAITING_SAFETY_REVIEW",
                      "WAITING_RATE_LIMIT", "WAITING_PARSE_REVIEW", "QUEUED"}:
        raise ValueError("INVALID_STATE")

    field = patch.get("field", "")
    if field not in _ALLOWED_FIELDS:
        raise ValueError(f"FIELD_NOT_ALLOWED：允许字段 {_ALLOWED_FIELDS}")
    new_value = patch.get("new_value")
    jlock = _job_lock(job_id)
    redis_client = getattr(queue_client, "client", None)
    with distributed_lock(redis_client, f"intervene:{job_id}"):
        with jlock:
            return _apply_locked(store, job_id, patch, operator, reason, base_version, field, new_value)


def _apply_locked(store: CheckpointStore, job_id: str, patch: dict[str, Any],
                  operator: str, reason: str, base_version: int,
                  field: str, new_value: Any) -> dict[str, Any]:
    if True:
        # 锁内重读：拿最新 version 与内容，避免竞态窗口覆盖
        state = store.load(job_id)
        if state.get("version", 1) != base_version:
            raise ValueError("VERSION_CONFLICT")
        if state.get("status") not in {"RUNNING", "WAITING_BUDGET_APPROVAL", "WAITING_SAFETY_REVIEW",
                                       "WAITING_RATE_LIMIT", "WAITING_PARSE_REVIEW", "QUEUED"}:
            raise ValueError("INVALID_STATE")
        user_input = state.setdefault("user_input", {})
        changes: dict[str, Any] = {}
        if field in {"constraints", "preferences"}:
            mode = patch.get("mode", "append")
            current = list(user_input.get(field, []))
            old = list(current)
            values = new_value if isinstance(new_value, list) else [new_value]
            if mode == "remove":
                current = [v for v in current if v not in values]
            else:
                current += [v for v in values if v not in current]
            user_input[field] = current
            changes[field] = {"old": old, "new": current}
        elif field == "resume_from":
            old = state.get("resume_from")
            state["resume_from"] = str(new_value)
            changes[field] = {"old": old, "new": str(new_value)}
        elif field == "mood":
            old = user_input.get("mood")
            user_input["mood"] = str(new_value)
            changes[field] = {"old": old, "new": str(new_value)}
        else:  # budget
            old = user_input.get("budget")
            user_input[field] = int(new_value)
            changes[field] = {"old": old, "new": int(new_value)}

        # 干预事件进 state 队列：管线在下一节点边界消费（热替换 user_input 并审计）
        queue = state.setdefault("interventions", [])
        queue.append({"field": field, "changes": changes, "operator": operator,
                      "reason": reason, "seq": len(queue) + 1})

        prev_version = state.get("version", 1)
        store.save(job_id, state)          # 原子写 + version++ + 审计镜像
        state = store.load(job_id)
        inter_id = _record_intervention(job_id, operator, field,
                                        changes[field]["old"], changes[field]["new"],
                                        reason, thread_id=state.get("thread_id"))
        return {"applied": True, "version": state.get("version", prev_version + 1),
                "changes": changes, "intervention_id": inter_id}
