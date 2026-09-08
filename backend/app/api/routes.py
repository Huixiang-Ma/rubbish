"""标品线路 API：/api/routes（CRUD + 微调 + 出行日校验 + 知识渲染）。

对应 docs/行程规划标品方案.md §四在线服务形态；A 形态主商品接口。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services import route_service

router = APIRouter(prefix="/api/routes", tags=["routes"])


def _tenant(payload: dict) -> str:
    return str(payload.get("tenant_id") or "default")


@router.get("")
def list_routes(tenant_id: str = "default", city: str | None = None, status: str | None = None) -> dict[str, Any]:
    return {"routes": route_service.list_routes(tenant_id, city, status)}


@router.get("/{route_id}")
def get_route(route_id: str, tenant_id: str = "default", enrich: bool = True) -> dict[str, Any]:
    route = route_service.get_route(route_id, tenant_id)
    if not route:
        raise HTTPException(status_code=404, detail="线路不存在")
    if enrich:
        route = route_service.enrich_knowledge(route)
    return route


@router.post("")
def create_route(payload: dict) -> dict[str, Any]:
    try:
        return route_service.create_route(payload, _tenant(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{route_id}/publish")
def publish_route(route_id: str, payload: dict) -> dict[str, Any]:
    route = route_service.publish(route_id, _tenant(payload), str(payload.get("reviewer") or "reviewer"))
    if not route:
        raise HTTPException(status_code=404, detail="线路不存在")
    return route


@router.post("/{route_id}/variant")
def apply_variant(route_id: str, payload: dict) -> dict[str, Any]:
    route = route_service.get_route(route_id, _tenant(payload))
    if not route:
        raise HTTPException(status_code=404, detail="线路不存在")
    variant = str(payload.get("variant") or "")
    return route_service.apply_variant(route, variant)


@router.get("/{route_id}/daily-check")
def check_route(route_id: str, tenant_id: str = "default") -> dict[str, Any]:
    route = route_service.get_route(route_id, tenant_id)
    if not route:
        raise HTTPException(status_code=404, detail="线路不存在")
    return {"warnings": route_service.daily_check(route)}