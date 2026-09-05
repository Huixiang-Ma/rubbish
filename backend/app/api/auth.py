"""认证 API：登录 / 注册 / token 校验（HMAC 演示级）。"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    realm: str = Field(default="toc", pattern="^(toc|tob)$")
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    display: str | None = None


def bearer_token(request: Request) -> str:
    return request.headers.get("authorization", "").removeprefix("Bearer ").strip()


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    user = auth_service.verify(payload.realm, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {
        "token": auth_service.issue_token(user["username"], user["role"]),
        "role": user["role"],
        "name": user["display"],
    }


@router.post("/register")
def register(payload: RegisterRequest) -> dict:
    display, error = auth_service.register(payload.username, payload.password, payload.display)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {
        "token": auth_service.issue_token(payload.username, "traveler"),
        "role": "traveler",
        "name": display,
    }


@router.get("/me")
def me(request: Request) -> dict:
    data = auth_service.verify_token(bearer_token(request))
    if not data:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    return {"username": data.get("u"), "role": data.get("r"), "exp": data.get("exp")}


def require_traveler(request: Request) -> dict:
    """P2.2 toC 登录守卫：返回 token payload（u=用户名）；未登录 401、非游客角色 403。"""
    token = bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="需要登录")
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    if payload.get("r") != "traveler":
        raise HTTPException(status_code=403, detail="FORBIDDEN_ROLE")
    return payload


def require_admin(request: Request) -> None:
    """AUTH_ENABLED=true 时挂载到 toB 管理路由的守卫。"""
    if not auth_service.verify_token(bearer_token(request), role="admin"):
        raise HTTPException(status_code=401, detail="需要工作台管理员登录")


def require_role(*roles: str):
    """RBAC 守卫：token 角色须在 roles 内；缺失 token 视为未认证，角色不符返回 403。"""

    def dep(request: Request) -> dict:
        token = bearer_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="需要登录")
        payload = auth_service.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="token 无效或已过期")
        if payload.get("r") not in roles:
            raise HTTPException(status_code=403, detail="FORBIDDEN_ROLE")
        return payload

    return dep
