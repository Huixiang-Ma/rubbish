"""飞猪AI开放平台客户端：MCP Streamable HTTP 协议（https://flyai.open.fliggy.com/mcp）。

- 密钥与启停由 api_registry 统一管理（FLIGGY_AI_API_KEY），未配置时所有方法返回 None，业务侧回退高德口径。
- 协议（对齐官方 flyai-cli 客户端）：JSON-RPC 2.0 over HTTP，
  请求需带 HMAC-SHA256 签名头（x-flyai-sign-*，密钥为内置签名密钥，可用 FLIGGY_SIGN_SECRET 覆盖）、
  设备指纹头（x-ff-ctx，gzip 压缩的指纹 JSON）与固定 x-ttid / User-Agent。
- 兼容 application/json 与 text/event-stream 两种响应格式（取最后一条 data: 行）。
- 结果带内存缓存（默认 10 分钟），控制正式 Key 的调用配额。
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.api_registry import get_api_config

MCP_PROTOCOL_VERSION = "2024-11-05"
SIGN_VERSION = "7"
SIGN_ALG = "hmac-sha256"
SIGN_SECRET_DEFAULT = "XSbdYnucPARDc9knhD8+X6hxdD1Nh6ZGI6Hadg25kBw="
X_TTID = "ai2c(sk.clawhub)"
CLIENT_VERSION = "1.0.6"
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 600


def is_ready() -> bool:
    return get_api_config("fliggy_ai").enabled


def _sign_secret() -> str:
    return os.environ.get("FLIGGY_SIGN_SECRET", "").strip() or SIGN_SECRET_DEFAULT


def _auth_header(api_key: str) -> str:
    key = api_key.strip()
    return key if key.startswith("Bearer ") else f"Bearer {key}"


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sign_headers(method: str, pathname: str, body: str, authorization: str) -> dict[str, str]:
    """对齐官方客户端的请求签名：POST\n路径\n时间戳\nnonce\nbody哈希\n授权头哈希 的 HMAC-SHA256。"""
    timestamp = str(int(time.time() * 1000))
    nonce = secrets.token_hex(16)
    string_to_sign = f"{method}\n{pathname}\n{timestamp}\n{nonce}\n{_sha256_hex(body)}\n{_sha256_hex(authorization)}"
    signature = hmac.new(_sign_secret().encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    return {
        "x-flyai-sign-ver": SIGN_VERSION,
        "x-flyai-sign-alg": SIGN_ALG,
        "x-flyai-ts": timestamp,
        "x-flyai-nonce": nonce,
        "x-flyai-sign": base64.urlsafe_b64encode(signature).decode("ascii").rstrip("="),
    }


def _ff_ctx() -> str:
    """设备指纹头（对齐官方客户端）：指纹 JSON → gzip → AES-256-GCM(sha256(签名密钥)) → base64(版本字节+nonce+密文+tag)。"""
    fingerprint = {
        "machine": {
            "platform": "linux",
            "arch": "x64",
            "cpus": 2,
            "memoryTierGB": 2,
            "osType": "Linux",
            "nodeVersion": "v20.0.0",
            "osReleaseMajor": "5",
        },
        "fingerprint": {
            "language": "zh",
            "platform": "Linux",
            "userAgent": f"flyai-cli/{CLIENT_VERSION} (Node.js v20.0.0; linux x64)",
            "hardwareConcurrency": 2,
            "deviceMemory": 2,
            "clientSurface": "cli",
            "timezoneOffset": -480,
            "deviceId": hashlib.sha256(str(uuid.uuid4()).encode("utf-8")).hexdigest(),
        },
    }
    compressed = gzip.compress(json.dumps(fingerprint, separators=(",", ":")).encode("utf-8"))
    key = hashlib.sha256(_sign_secret().encode("utf-8")).digest()
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, compressed, None)
    return base64.b64encode(bytes([1]) + nonce + ciphertext).decode("ascii")


def _user_agent() -> str:
    return f"flyai-cli/{CLIENT_VERSION} (Node.js v20.0.0; linux x64)"


def _parse_response(response: httpx.Response) -> dict[str, Any] | None:
    """MCP 响应可能是 JSON 或 SSE（data: 行），统一解析出 JSON-RPC 对象。"""
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        payload: dict[str, Any] | None = None
        for line in response.text.splitlines():
            if line.startswith("data:"):
                try:
                    payload = json.loads(line[5:].strip())
                except ValueError:
                    continue
        return payload
    try:
        return response.json()
    except ValueError:
        return None


def _rpc_post(payload: dict[str, Any], headers: dict[str, str]) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """一次 JSON-RPC POST（自动附加官方客户端签名头）；返回 (响应对象, 响应头)。失败返回 (None, {})。"""
    config = get_api_config("fliggy_ai")
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    pathname = urlparse(config.base_url).path or "/"
    request_headers = {
        **headers,
        **_sign_headers("POST", pathname, body, headers.get("Authorization", "")),
        "x-ff-ctx": _ff_ctx(),
        "x-ttid": X_TTID,
        "User-Agent": _user_agent(),
    }
    try:
        response = httpx.post(
            config.base_url,
            content=body.encode("utf-8"),
            headers=request_headers,
            timeout=config.timeout_seconds,
        )
    except Exception:
        return None, {}
    if response.status_code >= 400:
        return None, {}
    return _parse_response(response), dict(response.headers)


def _request_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": _auth_header(api_key),
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }


def call_tool(tool: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    """调用飞猪AI MCP 工具（search_poi / ai_search / ...），返回工具 JSON 结果；任何失败返回 None。

    对齐官方客户端：无会话握手，每次独立 tools/call。
    """
    if not is_ready():
        return None
    cache_key = tool + "|" + json.dumps(arguments, ensure_ascii=False, sort_keys=True)
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]
    config = get_api_config("fliggy_ai")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    data: dict[str, Any] | None = None
    for attempt in range(3):  # 容器 DNS/连接偶发抖动，退避重试
        data, _ = _rpc_post(payload, _request_headers(config.api_key))
        if data:
            break
        time.sleep(0.8 * (attempt + 1))
    if not data:
        return None
    result = data.get("result") or {}
    content = result.get("content") or []
    text = next((c.get("text", "") for c in content if c.get("type") == "text"), "")
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = {"text": text}
    _cache[cache_key] = (now + CACHE_TTL_SECONDS, parsed)
    return parsed


def search_pois(city: str, keyword: str = "景点", size: int = 10) -> list[dict[str, Any]]:
    """景点搜索（含榜单排名 / 飞猪预订链接 / 门票信息）；未启用或失败返回空列表。"""
    data = call_tool("search_poi", {"cityName": city.removesuffix("市"), "keyword": keyword})
    if not isinstance(data, dict):
        return []
    items = (data.get("data") or {}).get("itemList") or []
    result = []
    for item in items:
        if not item.get("name"):
            continue
        result.append(
            {
                "name": item["name"],
                "category": item.get("category") or "",
                "list_rank": item.get("listRank") or "",
                "booking_url": item.get("jumpUrl") or "",
                "ticket_info": item.get("ticketInfo") or "",
                "main_pic": item.get("mainPic") or "",
                "source": "飞猪AI",
            }
        )
    return result
