"""标品目录知识化 API（/api/catalog/*）：语料摄入、健康探针、逐点 RAG 背书。"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import catalog_rag

router = APIRouter(prefix="/api/catalog", tags=["标品知识背书"])


class GroundRequest(BaseModel):
    terms: list[Any] = Field(..., description="站点名列表，元素为字符串或 {name, city}")
    tenant_id: str | None = None


@router.get("/health")
def health() -> dict[str, Any]:
    """语料与检索层健康探针：前端可在详情页据此决定是否显示「知识背书」区块。"""
    return {"ok": True, **catalog_rag.ensure_corpus()}


@router.post("/ingest")
def ingest() -> dict[str, Any]:
    """强制（重新）摄入语料到语义检索层。PG 模式供 toB 管理侧手动刷新。"""
    return catalog_rag.ensure_corpus(force=True)


@router.post("/grounding")
def grounding(body: GroundRequest) -> dict[str, Any]:
    """对方案停留点做知识语料背书：逐站检索 → 命中返回原文片段 + 置信度。"""
    return catalog_rag.ground_terms(body.terms or [], tenant_id=body.tenant_id)
