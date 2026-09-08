"""线路标品 SKU：itinerary_routes（A 形态商品，含租户/审核/版本字段）。

Revision ID: 0003_routes
Revises: 0002_memory
Create Date: 2026-09-06
"""
from alembic import op

revision = "0003_routes"
down_revision = "0002_memory"
branch_labels = None
depends_on = None

_DDL = [
    # 线路 SKU：骨架引用 POI/知识块，变体规则不复制线路（见 docs/行程规划标品方案.md §二）
    """
    CREATE TABLE IF NOT EXISTS itinerary_routes (
        route_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL DEFAULT 'default',
        city TEXT NOT NULL,
        theme TEXT,
        days INTEGER NOT NULL,
        pace TEXT,
        audience TEXT,
        season TEXT,
        days_detail JSONB NOT NULL,
        variants JSONB,
        knowledge_refs JSONB,
        status TEXT NOT NULL DEFAULT 'draft',
        reviewer TEXT,
        published_at TIMESTAMPTZ,
        version INTEGER NOT NULL DEFAULT 1,
        quality_report TEXT,
        daily_check JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_routes_tenant ON itinerary_routes (tenant_id, city, status)",
    # 语料块补租户列（检索强制带租户过滤，见 §三 租户设计）
    "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'default'",
]
_DOWNSQL = [
    "DROP TABLE IF EXISTS itinerary_routes",
    "ALTER TABLE document_chunks DROP COLUMN IF EXISTS tenant_id",
]


def upgrade() -> None:
    for ddl in _DDL:
        op.execute(ddl)


def downgrade() -> None:
    for ddl in _DOWNSQL:
        op.execute(ddl)
