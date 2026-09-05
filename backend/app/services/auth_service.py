"""演示级认证服务：HMAC 签名 token + 本地用户文件 + 内置演示账号。

诚实口径：登录为页面级门禁 + 签名校验接口；AUTH_ENABLED=true 时 toB 管理类 API
才强制 Bearer token，默认关闭以保证 smoke 与演示零配置可跑。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from app.config import get_settings
from app.services.paths import DATA_ROOT

_USERS_FILE = DATA_ROOT / "auth_users.json"
def _demo_credentials() -> dict:
    """演示账号口令全部走 .env 配置（P0 安全基线）：代码内不再持有任何固定口令。"""
    s = get_settings()
    return {
        "toc_username": s.toc_demo_username,
        "toc_password": s.toc_demo_password,
        "supervisor_password": s.tob_supervisor_password,
        "consultant_password": s.tob_consultant_password,
    }


def _toc_demo_name() -> str:
    return _demo_credentials()["toc_username"]


def _secret() -> str:
    return get_settings().auth_secret


def _hash(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def _load_users() -> dict:
    if _USERS_FILE.exists():
        try:
            return json.loads(_USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_users(users: dict) -> None:
    _USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def register(username: str, password: str, display: str | None) -> tuple[str | None, str | None]:
    if not username or not password:
        return None, "用户名或密码不能为空"
    users = _load_users()
    if username in users or username == _toc_demo_name():
        return None, "用户名已存在"
    salt = secrets.token_hex(8)
    users[username] = {"salt": salt, "hash": _hash(password, salt), "display": display or username}
    _save_users(users)
    return users[username]["display"], None


# toB 演示账号：口令走 .env（TOB_SUPERVISOR_PASSWORD / TOB_CONSULTANT_PASSWORD），代码不持有固定口令
_TOB_DEMO_ROLES: dict[str, dict[str, str]] = {
    "supervisor": {"display": "工作台主管", "role": "supervisor"},
    "consultant": {"display": "工作台顾问", "role": "consultant"},
}


def verify(realm: str, username: str, password: str) -> dict | None:
    settings = get_settings()
    if realm == "tob":
        creds = _demo_credentials()
        if hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
            password, settings.admin_password
        ):
            return {"username": username, "display": "工作台管理员", "role": "admin"}
        account = _TOB_DEMO_ROLES.get(username)
        expected = creds.get(f"{username}_password")
        if account and expected and hmac.compare_digest(password, expected):
            tenant = getattr(settings, f"tob_{username}_tenant", "wl")
            return {"username": username, "display": account["display"], "role": account["role"], "tenant": tenant}
        return None
    creds = _demo_credentials()
    if username == creds["toc_username"] and hmac.compare_digest(password, creds["toc_password"]):
        users = _load_users()
        return {"username": username, "display": users.get(username, {}).get("display", username), "role": "traveler"}
    user = _load_users().get(username)
    if user and hmac.compare_digest(user["hash"], _hash(password, user["salt"])):
        return {"username": username, "display": user.get("display", username), "role": "traveler"}
    return None


def issue_token(username: str, role: str, tenant: str | None = None) -> str:
    claims = {"u": username, "r": role, "exp": int(time.time()) + 7 * 24 * 3600}
    if tenant:
        claims["t"] = tenant
    payload = base64.urlsafe_b64encode(
        json.dumps(claims).encode()
    ).decode().rstrip("=")
    sig = hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{payload}.{sig}"


def verify_token(token: str, role: str | None = None) -> dict | None:
    try:
        payload, sig = token.rsplit(".", 1)
        expected = hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(expected, sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if data.get("exp", 0) < time.time():
            return None
        if role and data.get("r") != role:
            return None
        return data
    except Exception:
        return None
