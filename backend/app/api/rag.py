"""RAG 问答 API：/api/rag/ask（同步）与 /api/rag/chat（SSE 流式）。

事件口径与 rag_lab 前端一致：meta → token* → done（拒答/空命中短路）。
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.rag_service import RagConfig, ask, stream_ask

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/ask")
def rag_ask(payload: dict) -> dict[str, Any]:
    message = str(payload.get("message") or "").strip()
    if not message:
        return {"mode": "empty", "answer": "请输入问题。", "sources": []}
    cfg = RagConfig(
        top_k=int(payload.get("top_k") or 3),
        multi=payload.get("multi") if payload.get("multi") is not None else True,
    )
    return ask(message, cfg, tenant_id=payload.get("tenant_id"))


@router.post("/chat")
def rag_chat(payload: dict):
    message = str(payload.get("message") or "").strip()
    if not message:
        return {"type": "error", "message": "请输入问题。"}
    cfg = RagConfig(
        top_k=int(payload.get("top_k") or 3),
        multi=payload.get("multi") if payload.get("multi") is not None else True,
    )

    def sse():
        try:
            for event in stream_ask(message, cfg, tenant_id=payload.get("tenant_id")):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
