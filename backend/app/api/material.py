"""D 档 · 标品素材库真实接口（/api/products）。

- 读取（列表/分类/详情/管理全量）：与 mock productsMock 契约一致；
- 写操作（新建/编辑/上下架/删除）：require_staff（admin/supervisor/consultant），
  改动落 DATA_ROOT 覆盖层，游客端随后可见变化。
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request

from app.api._staff import caller, require_staff
from app.services import material_store

router = APIRouter(tags=["标品素材库：目录 / 素材管理"])


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc) or "请求不合法")


@router.get("/api/products/categories")
def product_categories() -> dict:
    return material_store.product_categories()


@router.get("/api/products/manage")
def products_manage(
    keyword: str = "",
    category: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=300, ge=1, le=1000),
    request: Request = None,
) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    return material_store.manage_products({
        "keyword": keyword, "category": category, "page": page, "page_size": page_size,
    })


@router.get("/api/products")
def products_public(
    category: str = "",
    keyword: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
) -> dict:
    return material_store.public_list({
        "category": category, "keyword": keyword, "page": page, "page_size": page_size,
    })


@router.get("/api/products/{product_id}")
def product_detail(product_id: str) -> dict:
    try:
        return {"product": material_store.public_detail(product_id)}
    except LookupError as e:
        raise _err(e)


@router.post("/api/products")
def product_create(payload: dict[str, Any] = Body(...), request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        return {"product": material_store.create_product(payload)}
    except ValueError as e:
        raise _err(e)


@router.put("/api/products/{product_id}")
def product_update(product_id: str, payload: dict[str, Any] = Body(...), request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        return {"product": material_store.update_product(product_id, payload)}
    except LookupError as e:
        raise _err(e)


@router.post("/api/products/{product_id}/status")
def product_set_status(product_id: str, payload: dict[str, Any] = Body(...), request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        return material_store.set_product_status(product_id, bool(payload.get("listed", True)))
    except LookupError as e:
        raise _err(e)


@router.delete("/api/products/{product_id}")
def product_delete(product_id: str, request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        material_store.delete_product(product_id)
        return {"ok": True}
    except LookupError as e:
        raise _err(e)
