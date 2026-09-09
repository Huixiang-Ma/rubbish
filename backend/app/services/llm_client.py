import json
import socket
import ssl
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.services.metrics import LLM_CALLS, LLM_TOKENS


def _dechunk(body: bytes) -> bytes:
    """极简 chunked 解码（LLM 网关响应体积小，无需流式解析）。"""
    out = b""
    while True:
        line_end = body.find(b"\r\n")
        if line_end == -1:
            break
        try:
            size = int(body[:line_end].split(b";")[0], 16)
        except ValueError:
            return out + body
        if size == 0:
            break
        out += body[line_end + 2 : line_end + 2 + size]
        body = body[line_end + 2 + size + 2 :]
    return out


class LLMClient:
    """mock-first 的 LLM 封装（httpx 版）。

    real 模式走 OpenAI 兼容 /chat/completions（通义/DeepSeek/OpenAI 均可指向）；
    mock 模式或 real 调用任何失败时返回 None，由调用方落到确定性 mock 模板，
    保证断网、无 key、供应商故障时主链路照常可演示（S7 私有化兜底）。
    httpx 提供连接池与统一超时；重试在 try_generate_json 外层循环实现。
    """

    def __init__(self) -> None:
        settings = Settings()
        self.mode = settings.llm_mode.lower()
        self.base_url = settings.llm_base_url.rstrip("/")
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout_seconds = settings.llm_timeout_seconds
        self.max_retries = settings.llm_max_retries
        self.temperature = settings.llm_temperature

    def try_generate_json(
        self, prompt: str, schema: dict[str, Any] | None = None, max_tokens: int = 1600
    ) -> dict[str, Any] | None:
        """real 模式调用并解析 JSON；mock 模式或任何失败返回 None，由调用方使用 mock 模板。"""
        if self.mode != "real" or not self.api_key:
            return None
        for attempt in range(self.max_retries + 1):
            try:
                content = self._chat_completion(prompt, max_tokens=max_tokens)
                return self._parse_json_object(content)
            except Exception:
                if attempt == self.max_retries:
                    return None
                time.sleep(0.5 * (attempt + 1))
        return None

    def generate_json(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.mode == "mock":
            return {
                "mode": "mock",
                "summary": "已使用 mock LLM 生成结构化内容。",
                "prompt_preview": prompt[:120],
            }
        result = self.try_generate_json(prompt, schema)
        if result is None:
            raise RuntimeError("LLM_MODE=real 调用失败：检查 LLM_API_KEY/LLM_BASE_URL/LLM_MODEL 配置。")
        return result

    def classify(self, text: str, labels: list[str]) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ["ignore previous", "system prompt", "忽略之前", "泄露", "绕过"]):
            return "MALICIOUS" if "MALICIOUS" in labels else labels[-1]
        return labels[0]

    def generate_text(self, prompt: str, system: str = "", max_tokens: int = 1600) -> str:
        """普通文本生成（非 JSON）：real 走 httpx→socket 兜底通道，mock/失败返回空串。

        RAG 问答等自然语言生成统一走此入口，复用与 try_generate_json 相同的
        WAF 兜底链（实测部分网关按 TLS 指纹拒绝 httpx，raw socket 稳定）。
        """
        if self.mode != "real" or not self.api_key:
            return ""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages,
                   "temperature": self.temperature, "max_tokens": max_tokens}
        try:
            return self._chat_via_httpx(payload)
        except Exception:
            try:
                return self._chat_via_socket(payload)
            except Exception:
                return ""

    def _chat_completion(self, prompt: str, max_tokens: int = 1600) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是严谨的 JSON 生成器，只输出一个合法 JSON 对象，不要输出任何多余文字。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,  # 默认 1600 限制 runaway；内容增强等大输出可调高
        }
        try:
            return self._chat_via_httpx(payload)
        except Exception:
            # 容器网络对长连接偶发 19s 空闲切断（实测 httpx 必现、raw socket 稳定），
            # 失败时降级到短连接兜底通道，保证真实 LLM 调用可用。
            return self._chat_via_socket(payload)

    @staticmethod
    def _record_usage(data: dict[str, Any]) -> None:
        """P2 成本治理：从响应 usage 记录 token 消耗；provider 未回 usage 时只计调用数。"""
        try:
            LLM_CALLS.inc()
            usage = data.get("usage") or {}
            for key, kind in (("prompt_tokens", "prompt"), ("completion_tokens", "completion")):
                value = usage.get(key)
                if value:
                    LLM_TOKENS.labels(kind=kind).inc(int(value))
        except Exception:
            pass

    def _chat_via_httpx(self, payload: dict[str, Any]) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        self._record_usage(data)
        return data["choices"][0]["message"]["content"]

    def _chat_via_socket(self, payload: dict[str, Any]) -> str:
        parsed = urlparse(f"{self.base_url}/chat/completions")
        host = parsed.hostname
        ctx = ssl.create_default_context()
        body = json.dumps(payload)
        with ctx.wrap_socket(socket.create_connection((host, 443), timeout=self.timeout_seconds), server_hostname=host) as sock:
            request = (
                f"POST {parsed.path} HTTP/1.1\r\nHost: {host}\r\n"
                f"Authorization: Bearer {self.api_key}\r\nContent-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
            )
            sock.sendall(request.encode())
            # 长生成实测可达 70s+，读超时放宽到 超时+75s
            sock.settimeout(self.timeout_seconds + 75)
            data = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        if not data:
            raise RuntimeError("llm socket fallback: empty response")
        head, _, body_bytes = data.partition(b"\r\n\r\n")
        status_line = head.split(b"\r\n", 1)[0].decode("utf-8", "ignore")
        if " 200" not in status_line:
            raise RuntimeError(f"llm socket fallback: {status_line}")
        if b"transfer-encoding: chunked" in head.lower():
            body_bytes = _dechunk(body_bytes)
        payload_out = json.loads(body_bytes.decode("utf-8", "ignore"))
        self._record_usage(payload_out)
        return payload_out["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_json_object(content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("no json object in llm response")
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else {}
