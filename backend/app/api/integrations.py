"""外部能力扩展点与语义检索的 API 层。"""
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services import integrations, semantic

router = APIRouter(prefix="/api", tags=["integrations"])


@router.get("/integrations/status")
def integrations_status() -> dict[str, Any]:
    """明确不接清单的扩展点状态：地图（本地估算可用）/搜索/OCR（mock）/支付（禁用）。"""
    return {"adapters": integrations.status()}


@router.get("/semantic/search")
def semantic_search(q: str, k: int = 3) -> dict[str, Any]:
    """语义检索（未配置 PG 时内存兜底；embedding 见 EMBEDDING_PROVIDER）。"""
    try:
        return semantic.search_similar(q, k)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/semantic/add")
def semantic_add(job_id: str, content: str) -> dict[str, Any]:
    try:
        return semantic.add_chunk(job_id, content)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
