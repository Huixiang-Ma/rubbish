"""初始 schema：plan_jobs / audit_logs / safety_events / document_chunks（pgvector）。

Revision ID: 0001_init
Revises:
Create Date: 2026-08-30
"""
from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

_DDL = [
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
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id BIGSERIAL PRIMARY KEY,
        job_id TEXT,
        content TEXT,
        embedding vector(1024) -- 运行时 pg_mirror 按 EMBEDDING_PROVIDER 自适应（mock=8 / ollama=BGE-M3=1024）
    )
    """,
]


def upgrade() -> None:
    for ddl in _DDL:
        op.execute(ddl)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.execute("DROP TABLE IF EXISTS safety_events")
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS plan_jobs")
