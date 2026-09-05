"""PostgreSQL 镜像层（生产演进）：把任务/审计/安全事件跨实例落库。

设计原则：
- 本地 state.json checkpoint 仍是唯一事实源，PG 只是可观测/审计镜像；
- 未配置 DATABASE_URL 时整层 no-op，零依赖演示不受影响；
- 镜像写入失败只记日志，绝不阻断主流程。
表结构（与 alembic 初始迁移一致）：plan_jobs / audit_logs / safety_events / document_chunks。
document_chunks 维度由当前 embedder 决定（mock=8，ollama=BGE-M3 即 EMBEDDING_DIM），历史维度不匹配时自动重建。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.services.embedding import active_dim

logger = logging.getLogger("wl.pg_mirror")

_DDL = [
    "ALTER TABLE plan_jobs ADD COLUMN IF NOT EXISTS user_id TEXT",
    "CREATE EXTENSION IF NOT EXISTS vector",
    """
    CREATE TABLE IF NOT EXISTS plan_jobs (
        job_id TEXT PRIMARY KEY,
        status TEXT,
        version INTEGER DEFAULT 1,
        destination TEXT,
        origin TEXT,
        customer TEXT,
        tenant TEXT,
        user_id TEXT,
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        payload JSONB
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id BIGSERIAL PRIMARY KEY,
        job_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        action TEXT,
        payload JSONB
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS safety_events (
        id BIGSERIAL PRIMARY KEY,
        job_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        risk_level TEXT,
        action TEXT,
        evidence JSONB
    )
    """,
]

# document_chunks 维度随 embedder 变化（mock=8 / BGE-M3=EMBEDDING_DIM），单独按维度建表
_DOCUMENT_CHUNKS_DDL = """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id BIGSERIAL PRIMARY KEY,
        job_id TEXT,
        content TEXT,
        embedding vector({dim})
    )
    """


class PgMirror:
    """PostgreSQL 镜像层：延迟初始化（Postgres 未就绪时每 30 秒重试，自愈）。"""

    RETRY_SECONDS = 30

    def __init__(self) -> None:
        settings = get_settings()
        self.database_url = settings.database_url
        self.enabled = False
        self.engine = None
        self.Session = sessionmaker
        self._last_attempt = 0.0

    def _ensure(self) -> bool:
        if self.engine is not None:
            return True
        if not self.database_url:
            return False
        if time.time() - self._last_attempt < self.RETRY_SECONDS:
            return False
        self._last_attempt = time.time()
        try:
            self.engine = create_engine(self.database_url, pool_pre_ping=True, future=True)
            with self.engine.begin() as conn:
                for ddl in _DDL:
                    conn.execute(text(ddl))
                self._ensure_chunks_table(conn)
            self.enabled = True
            logger.info("pg mirror ready")
        except Exception as exc:
            logger.warning("pg mirror init failed (will retry): %s", exc)
            self.engine = None
        return self.enabled

    def _ensure_chunks_table(self, conn: Any) -> None:
        """document_chunks 按当前 embedder 输出维度建表；历史维度不匹配时重建。

        chunks 是可重灌的派生数据（embedding 模型变更后旧向量本就作废），
        重建优于静默写入维度不符的向量。pgvector 的 atttypmod 即维度值。
        """
        dim = active_dim(get_settings())
        row = conn.execute(
            text(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = to_regclass('document_chunks') AND attname = 'embedding'"
            )
        ).first()
        if row is None:
            conn.execute(text(_DOCUMENT_CHUNKS_DDL.format(dim=dim)))
            return
        if row[0] != dim:
            logger.warning(
                "document_chunks 维度不匹配（%s → %s），重建表，chunk 需重新入库", row[0], dim
            )
            conn.execute(text("DROP TABLE document_chunks"))
            conn.execute(text(_DOCUMENT_CHUNKS_DDL.format(dim=dim)))

    def _safe(self, sql: str, params: dict[str, Any]) -> None:
        if not self._ensure():
            return
        try:
            with self.engine.begin() as conn:
                conn.execute(text(sql), params)
        except Exception as exc:
            logger.warning("pg mirror write failed: %s", exc)

    def record_job(self, state: dict[str, Any]) -> None:
        user_input = state.get("user_input", {})
        self._safe(
            """
            INSERT INTO plan_jobs (job_id, status, version, destination, origin, customer, tenant, user_id, updated_at, payload)
            VALUES (:job_id, :status, :version, :destination, :origin, :customer, :tenant, :user_id, NOW(), :payload)
            ON CONFLICT (job_id) DO UPDATE SET
                status = EXCLUDED.status, version = EXCLUDED.version,
                destination = EXCLUDED.destination, origin = EXCLUDED.origin,
                customer = EXCLUDED.customer, tenant = EXCLUDED.tenant, user_id = EXCLUDED.user_id,
                updated_at = NOW(), payload = EXCLUDED.payload
            """,
            {
                "job_id": state.get("job_id"),
                "status": state.get("status"),
                "version": state.get("version", 1),
                "destination": user_input.get("destination"),
                "origin": user_input.get("origin"),
                "customer": state.get("customer"),
                "tenant": state.get("tenant"),
                "user_id": state.get("user_id"),
                "payload": json.dumps(state, ensure_ascii=False, default=str),
            },
        )

    def record_audit(self, job_id: str, event: dict[str, Any]) -> None:
        self._safe(
            "INSERT INTO audit_logs (job_id, action, payload) VALUES (:job_id, :action, :payload)",
            {
                "job_id": job_id,
                "action": event.get("action"),
                "payload": json.dumps(event, ensure_ascii=False, default=str),
            },
        )

    def record_safety(self, job_id: str, risk_level: str, action: str, evidence: list[str]) -> None:
        self._safe(
            "INSERT INTO safety_events (job_id, risk_level, action, evidence) VALUES (:job_id, :risk_level, :action, :evidence)",
            {
                "job_id": job_id,
                "risk_level": risk_level,
                "action": action,
                "evidence": json.dumps(evidence, ensure_ascii=False),
            },
        )

    def add_chunk(self, job_id: str, content: str, embedding: list[float]) -> int | None:
        if not self._ensure():
            return None
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO document_chunks (job_id, content, embedding) "
                    "VALUES (:job_id, :content, :embedding) RETURNING id"
                ),
                {"job_id": job_id, "content": content, "embedding": str(embedding)},
            )
            return row.scalar_one()

    def search_chunks(self, query_embedding: list[float], k: int = 3) -> list[dict[str, Any]]:
        if not self._ensure():
            return []
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT job_id, content, embedding <=> :emb AS distance "
                    "FROM document_chunks ORDER BY embedding <=> :emb LIMIT :k"
                ),
                {"emb": str(query_embedding), "k": k},
            )
            return [{"job_id": r.job_id, "content": r.content, "distance": float(r.distance)} for r in rows]


pg_mirror = PgMirror()
