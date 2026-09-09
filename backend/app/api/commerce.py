"""C 档 · 商业闭环真实接口（在售方案 / 订单 / 收藏）。

契约路径沿用 frontend mock 声明的目标（/api/plan-products、/api/orders、/api/favorites），
数据与前端展示字段 1:1；用户未登录为 guest 账本，登录 traveler 隔离个人订单/收藏，
staff 角色（admin/supervisor/consultant）可看全量用于 toB 核销。
订单支付 = 演示级成功回执（无真实支付网关），接口语义与 mock 状态机一致。
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.api._staff import require_staff
from app.services import auth_service, shop_store

router = APIRouter(tags=["商业闭环：在售方案 / 订单 / 收藏"])


def _caller(request: Request) -> dict[str, Any] | None:
    """可选鉴权：有有效 token 返回 claims，否则 None（guest 账本）。"""
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not token:
        return None
    payload = auth_service.verify_token(token)
    return payload or None


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc) or "请求不合法")


# ---------- 在售方案目录 ----------
@router.get("/api/plan-products/categories")
def plan_categories() -> dict:
    return shop_store.catalog_categories()


@router.get("/api/plan-products/featured")
def plan_featured() -> dict:
    return {"items": shop_store.catalog_featured(8)}


@router.get("/api/plan-products/top")
def plan_top() -> dict:
    return {"items": shop_store.catalog_top(10)}


@router.get("/api/plan-products")
def plan_list(
    category: str = "",
    city: str = "",
    days: Optional[int] = None,
    pace: str = "",
    keyword: str = "",
    sort: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=60),
) -> dict:
    return shop_store.catalog_list({
        "category": category, "city": city, "days": days, "pace": pace,
        "keyword": keyword, "sort": sort, "page": page, "page_size": page_size,
    })


@router.get("/api/plan-products/manage")
def plan_manage(
    request: Request,
    keyword: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=60, ge=1, le=200),
) -> dict:
    """方案馆管理列表：全量（含下架/自建），行内 stock 为实算余位。"""
    require_staff(request)
    return shop_store.plan_manage_list({"keyword": keyword, "page": page, "page_size": page_size})


@router.post("/api/plan-products")
def plan_create(payload: dict[str, Any] = Body(...), request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        return {"plan": shop_store.plan_create(payload)}
    except ValueError as e:
        raise _err(e)


@router.put("/api/plan-products/{plan_id}")
def plan_update(plan_id: str, payload: dict[str, Any] = Body(...), request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        return {"plan": shop_store.plan_update(plan_id, payload)}
    except (LookupError, ValueError) as e:
        raise _err(e)


@router.post("/api/plan-products/{plan_id}/status")
def plan_set_status(plan_id: str, payload: dict[str, Any] = Body(...), request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        plan = shop_store.plan_set_listed(plan_id, bool(payload.get("listed", True)))
        return {"listed": plan.get("listed", True)}
    except LookupError as e:
        raise _err(e)


@router.delete("/api/plan-products/{plan_id}")
def plan_delete(plan_id: str, request: Request = None) -> dict:
    if isinstance(request, Request):
        require_staff(request)
    try:
        shop_store.plan_remove(plan_id)
        return {"ok": True}
    except LookupError as e:
        raise _err(e)


@router.get("/api/plan-products/{plan_id}")
def plan_detail(plan_id: str) -> dict:
    try:
        return shop_store.catalog_detail(plan_id)
    except LookupError as e:
        raise _err(e)


# ---------- 收藏 ----------
@router.get("/api/favorites")
def favorites_list(request: Request) -> dict:
    return shop_store.fav_list(_caller(request))


@router.put("/api/favorites/{product_id}")
def favorites_add(product_id: str, request: Request) -> dict:
    return shop_store.fav_add(product_id, _caller(request))


@router.delete("/api/favorites/{product_id}")
def favorites_remove(product_id: str, request: Request) -> dict:
    return shop_store.fav_remove(product_id, _caller(request))


@router.post("/api/favorites/{product_id}/toggle")
def favorites_toggle(product_id: str, request: Request) -> dict:
    return shop_store.fav_toggle(product_id, _caller(request))


# ---------- 订单 ----------
class OrderContact(BaseModel):
    name: str = ""
    phone: str = ""


class OrderCreate(BaseModel):
    product_id: str
    persons: Optional[int] = Field(default=None, ge=1)
    qty: Optional[int] = Field(default=None, ge=1)
    use_date: Optional[str] = None
    start_date: Optional[str] = None
    contact: Optional[OrderContact] = None


class OrderPay(BaseModel):
    method: Optional[str] = None
    use_date: Optional[str] = None


@router.post("/api/orders")
def order_create(payload: OrderCreate, request: Request) -> dict:
    try:
        data = payload.model_dump(exclude_none=True)
        if payload.contact is not None:
            data["contact"] = {"name": payload.contact.name, "phone": payload.contact.phone}
        return {"order": shop_store.create_order(data, _caller(request))}
    except (LookupError, ValueError) as e:
        raise _err(e)


@router.get("/api/orders")
def order_list(
    request: Request,
    status: str = "",
    keyword: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
) -> dict:
    res = shop_store.list_orders({"status": status, "keyword": keyword}, _caller(request))
    start = (page - 1) * page_size
    rows = res["items"][start:start + page_size]
    return {**res, "page": page, "page_size": page_size,
            "has_more": start + len(rows) < res["total"], "items": rows}


@router.get("/api/orders/stats")
def order_stats(request: Request) -> dict:
    return shop_store.order_stats(_caller(request))


@router.get("/api/orders/{order_id}")
def order_get(order_id: str, request: Request) -> dict:
    try:
        return {"order": shop_store.order_detail(order_id, _caller(request))}
    except LookupError as e:
        raise _err(e)


@router.post("/api/orders/{order_id}/pay")
def order_pay(order_id: str, payload: OrderPay, request: Request) -> dict:
    try:
        return {"order": shop_store.order_pay(order_id, payload.method or "", payload.use_date, _caller(request))}
    except LookupError as e:
        raise _err(e)


@router.post("/api/orders/{order_id}/cancel")
def order_cancel(order_id: str, request: Request) -> dict:
    try:
        return {"order": shop_store.order_cancel(order_id, _caller(request))}
    except (LookupError, ValueError) as e:
        raise _err(e)


@router.post("/api/orders/{order_id}/complete")
def order_complete(order_id: str, request: Request) -> dict:
    try:
        return {"order": shop_store.order_complete(order_id, _caller(request))}
    except (LookupError, ValueError) as e:
        raise _err(e)


@router.post("/api/orders/{order_id}/refund")
def order_refund(order_id: str, request: Request) -> dict:
    try:
        return {"order": shop_store.order_refund(order_id, _caller(request))}
    except (LookupError, ValueError) as e:
        raise _err(e)
