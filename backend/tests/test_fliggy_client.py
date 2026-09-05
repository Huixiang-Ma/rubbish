"""飞猪AI MCP 客户端（fliggy_client）离线单测：mock httpx，不发真实网络请求。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import fliggy_client


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLIGGY_AI_API_KEY", raising=False)
    fliggy_client._cache.clear()
    yield
    fliggy_client._cache.clear()


def test_call_tool_disabled_without_key() -> None:
    assert fliggy_client.call_tool("search_poi", {"cityName": "南昌"}) is None
    assert fliggy_client.search_pois("南昌市") == []


class _FakeResponse:
    def __init__(self, payload: dict, headers: dict | None = None, sse: bool = False):
        self._payload = payload
        self.headers = {"content-type": "text/event-stream" if sse else "application/json", **(headers or {})}
        self.status_code = 200
        self.text = "data: " + json.dumps(payload)

    def json(self):
        return self._payload


def test_search_pois_full_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """initialize → tools/call 的 MCP 握手解析：正确透传 session 头与工具结果。"""
    monkeypatch.setenv("FLIGGY_AI_API_KEY", "test-key")
    init_resp = {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "flyai"}}}
    tool_resp = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"content": [{"type": "text", "text": json.dumps({
            "status": 0,
            "data": {"itemList": [{"name": "滕王阁", "listRank": "江西历史古迹景点榜第1名", "jumpUrl": "https://router.feizhu.com/x", "category": "历史古迹"}]},
        })}]},
    }
    calls: list[dict] = []

    def fake_post(payload, headers):
        calls.append(payload)
        if payload["method"] == "initialize":
            return init_resp, {"mcp-session-id": "sess-1"}
        if payload["method"] == "notifications/initialized":
            return {"jsonrpc": "2.0"}, {}
        return tool_resp, {}

    monkeypatch.setattr(fliggy_client, "_rpc_post", fake_post)
    pois = fliggy_client.search_pois("南昌市", "景点")
    assert pois and pois[0]["name"] == "滕王阁"
    assert pois[0]["list_rank"] == "江西历史古迹景点榜第1名"
    assert pois[0]["booking_url"] == "https://router.feizhu.com/x"
    # session 头（含 mcp-session-id）被透传到 tools/call
    tool_call = next(c for c in calls if c["method"] == "tools/call")
    assert tool_call["params"]["name"] == "search_poi"
