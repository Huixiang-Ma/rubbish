"""外部能力扩展点与语义检索的 API 层。"""
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.services import integrations, semantic

router = APIRouter(prefix="/api", tags=["integrations"])


@router.get("/integrations/status")
def integrations_status() -> dict[str, Any]:
    """明确不接清单的扩展点状态：地图（本地估算可用）/搜索/OCR（mock）/支付（禁用）。"""
    return {"adapters": integrations.status()}


@router.get("/semantic/debug")
def semantic_debug() -> dict[str, Any]:
    """临时调试端点：返回运行进程内 pg_mirror 单例的真实状态（交付前移除）。"""
    from app.services.pg_mirror import pg_mirror as mirror_singleton

    return {
        "singleton_url": mirror_singleton.database_url,
        "singleton_enabled": mirror_singleton.enabled,
        "singleton_engine_none": mirror_singleton.engine is None,
        "last_attempt_age": round(__import__("time").time() - mirror_singleton._last_attempt, 1),
        "settings_url": bool(get_settings().database_url),
    }


@router.get("/semantic/search")
def semantic_search(q: str, k: int = 3, tenant_id: str | None = None, multi: bool | None = None) -> dict[str, Any]:
    """混合语义检索（多意图分解 + BM25/向量 RRF；tenant_id 隔离多租户）。"""
    try:
        return semantic.search_similar(q, k, tenant_id=tenant_id, multi=multi)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/semantic/add")
def semantic_add(job_id: str, content: str, tenant_id: str = "default") -> dict[str, Any]:
    try:
        return semantic.add_chunk(job_id, content, tenant_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
