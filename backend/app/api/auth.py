"""认证 API：登录 / 注册 / token 校验（HMAC 演示级）。"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SmsCodeRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1\d{10}$")


class LoginRequest(BaseModel):
    realm: str = Field(default="toc", pattern="^(toc|tob)$")
    username: str | None = Field(default=None, min_length=1)
    password: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, pattern=r"^1\d{10}$")
    sms_code: str | None = Field(default=None, min_length=1)


class ResetPasswordRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1\d{10}$")
    sms_code: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6, max_length=32)


class RegisterRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1)
    password: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, pattern=r"^1\d{10}$")
    sms_code: str | None = Field(default=None, min_length=1)
    display: str | None = None


def bearer_token(request: Request) -> str:
    return request.headers.get("authorization", "").removeprefix("Bearer ").strip()


@router.post("/request-code")
def request_code(payload: SmsCodeRequest) -> dict:
    """P2.1 验证码签发；mock 通道回显 dev_code 供演示，真实通道上线后移除该字段。"""
    import app.services.auth_service as svc

    sent, dev_code = svc._send_sms(payload.phone)
    if not sent:
        raise HTTPException(status_code=500, detail="验证码发送失败")
    result = {"sent": True}
    from app.config import get_settings

    if get_settings().sms_provider == "mock":
        result["dev_code"] = dev_code
    return result


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    # P2.1 手机号+验证码登录（realm=toc 且带 phone/sms_code 时走短信链路）
    if payload.realm == "toc" and payload.phone and payload.sms_code:
        ok, err = auth_service.verify_sms_code(payload.phone, payload.sms_code)
        if not ok:
            raise HTTPException(status_code=401, detail=err or "验证码错误")
        user = auth_service.login_or_register_phone(payload.phone)
    else:
        user = auth_service.verify(payload.realm, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {
        "token": auth_service.issue_token(user["username"], user["role"], user.get("tenant")),
        "role": user["role"],
        "name": user["display"],
        "tenant": user.get("tenant"),
    }


@router.post("/register")
def register(payload: RegisterRequest) -> dict:
    """注册链路：手机号 + 短信验证码（验码通过才建号），账号即手机号；密码用于后续账号密码登录。"""
    if not payload.phone or not payload.sms_code:
        raise HTTPException(status_code=422, detail="注册需手机号与短信验证码")
    if not payload.password:
        raise HTTPException(status_code=422, detail="注册需设置登录密码")
    ok, err = auth_service.verify_sms_code(payload.phone, payload.sms_code)
    if not ok:
        raise HTTPException(status_code=401, detail=err or "验证码错误")
    username = payload.username or payload.phone
    display, error = auth_service.register(username, payload.password, payload.display, phone=payload.phone)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {
        "token": auth_service.issue_token(username, "traveler"),
        "role": "traveler",
        "name": display,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest) -> dict:
    """toC 找回密码：手机号 + 短信验证码 + 新密码（复用 request-code 通道）。成功即返回新 token。"""
    ok, err = auth_service.verify_sms_code(payload.phone, payload.sms_code)
    if not ok:
        raise HTTPException(status_code=401, detail=err or "验证码错误")
    user, error = auth_service.reset_password_by_phone(payload.phone, payload.password)
    if error or not user:
        raise HTTPException(status_code=400, detail=error or "重置失败")
    return {
        "token": auth_service.issue_token(user["username"], "traveler"),
        "role": "traveler",
        "name": user.get("display", payload.phone),
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

# ---------- toB 企业账号管理（admin 专属；账号由企业内部发放，不开放自助注册） ----------
class TobAccountCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=40)
    password: str = Field(..., min_length=6)
    display: str = Field(default="", max_length=40)
    role: str = Field(default="consultant", pattern="^(admin|supervisor|consultant)$")
    tenant: str = Field(default="wl", max_length=40)


class TobAccountReset(BaseModel):
    password: str = Field(..., min_length=6)


def _require_tob_admin(request: Request) -> dict:
    token = bearer_token(request)
    payload = auth_service.verify_token(token)
    if not payload or payload.get("r") != "admin":
        raise HTTPException(status_code=403, detail="仅工作台管理员可管理企业账号")
    return payload


@router.get("/tob/accounts")
def tob_accounts(request: Request) -> dict:
    _require_tob_admin(request)
    return {"accounts": auth_service.tob_accounts_list()}


@router.post("/tob/accounts")
def tob_account_create(payload: TobAccountCreate, request: Request) -> dict:
    _require_tob_admin(request)
    account, error = auth_service.tob_account_create(
        payload.username.strip(), payload.password, payload.display.strip(), payload.role, payload.tenant)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"ok": True, "account": account}


@router.post("/tob/accounts/{username}/reset")
def tob_account_reset(username: str, payload: TobAccountReset, request: Request) -> dict:
    _require_tob_admin(request)
    ok, error = auth_service.tob_account_reset(username, payload.password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"ok": True}


@router.delete("/tob/accounts/{username}")
def tob_account_delete(username: str, request: Request) -> dict:
    _require_tob_admin(request)
    ok, error = auth_service.tob_account_delete(username)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"ok": True}
