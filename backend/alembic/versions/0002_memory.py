"""工单 7：共享图记忆（三元组）与运行态干预流水表。

Revision ID: 0002_memory
Revises: 0001_init
Create Date: 2026-09-05
"""
from alembic import op

revision = "0002_memory"
down_revision = "0001_init"
branch_labels = None
depends_on = None

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS memory_entities (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        etype TEXT NOT NULL DEFAULT 'concept',
        tenant TEXT,
        job_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (name, etype, tenant)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_triples (
        id BIGSERIAL PRIMARY KEY,
        head_id BIGINT NOT NULL REFERENCES memory_entities(id) ON DELETE CASCADE,
        relation TEXT NOT NULL,
        tail_id BIGINT NOT NULL REFERENCES memory_entities(id) ON DELETE CASCADE,
        thread_id TEXT,
        job_id TEXT,
        source_round INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_triples_head ON memory_triples(head_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_triples_thread ON memory_triples(thread_id, status)",
    """
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
    """,
    "CREATE INDEX IF NOT EXISTS idx_interventions_job ON memory_interventions(job_id, created_at)",
]


def upgrade() -> None:
    for ddl in _DDL:
        op.execute(ddl)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_interventions")
    op.execute("DROP TABLE IF EXISTS memory_triples")
    op.execute("DROP TABLE IF EXISTS memory_entities")
