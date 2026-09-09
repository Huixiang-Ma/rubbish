"""Staff 守卫：toB 管理操作统一鉴权。

- 有有效 token 时按 claims 中的角色（admin / supervisor / consultant）判定；
- AUTH_ENABLED 关闭时不做强制（本地演示环境与现有 admin 路由口径一致），按 admin 放行；
- 游客/登录 traveler 无权进入 toB 写接口。
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.config import get_settings
from app.services import auth_service

STAFF_ROLES = {"admin", "supervisor", "consultant"}


def caller(request: Request) -> dict[str, Any] | None:
    """可选鉴权：有有效 token 返回 claims，否则 None（guest 账本）。"""
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not token:
        return None
    payload = auth_service.verify_token(token)
    return payload or None


def require_staff(request: Request) -> dict[str, Any]:
    claims = caller(request)
    if not get_settings().auth_enabled:
        return {"u": (claims or {}).get("u", "guest"), "r": "admin"}
    if not claims:
        raise HTTPException(status_code=401, detail="请先登录企业工作台")
    if claims.get("r") not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="当前账号无 toB 管理权限")
    return claims
