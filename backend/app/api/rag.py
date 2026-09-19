"""RAG 问答 API：/api/rag/ask（同步）与 /api/rag/chat（SSE 流式）。

事件口径与 rag_lab 前端一致：meta → token* → done（拒答/空命中短路）。
数据智能闭环：ask 命中自动累计语料引用；拒答/空命中自动生成「语料缺口工单」；
反馈（👍/👎）由前端回传 /feedback。引用统计与缺口清单供治理端消费。
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.services import feedback_store
from app.services.rag_service import RagConfig, ask, stream_ask

router = APIRouter(prefix="/api/rag", tags=["rag"])


def _after_ask(message: str, result: dict[str, Any]) -> dict[str, Any]:
    """ask 后的闭环钩子：命中累计引用；拒答/空命中聚类为缺口工单。"""
    try:
        job_ids = [s.get("job_id") for s in (result.get("sources") or []) if s.get("job_id")]
        feedback_store.record_citations(job_ids)
        if result.get("mode") == "llm":
            # 自动关单：同一 query 此前拒答过，现在已命中 → 工单标记已解决
            feedback_store.resolve_gap(message)
        if result.get("mode") in ("refusal", "empty"):
            top = (result.get("sources") or [{}])[0]
            feedback_store.add_gap(message, top.get("distance"))
    except Exception:
        pass  # 闭环记录失败不阻断问答主链路
    return result


@router.post("/ask")
def rag_ask(payload: dict) -> dict[str, Any]:
    message = str(payload.get("message") or "").strip()
    if not message:
        return {"mode": "empty", "answer": "请输入问题。", "sources": []}
    cfg = RagConfig(
        top_k=int(payload.get("top_k") or 3),
        multi=payload.get("multi") if payload.get("multi") is not None else True,
    )
    return _after_ask(message, ask(message, cfg, tenant_id=payload.get("tenant_id")))


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
            try:
                _after_ask(message, ask(message, cfg, tenant_id=payload.get("tenant_id")))
            except Exception:
                pass
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@router.post("/feedback")
def rag_feedback(payload: dict, request: Request) -> dict[str, Any]:
    """问答反馈：前端对回答点 👍/👎 后回传（公开，游客可反馈）。"""
    from app.api._staff import caller

    query = str(payload.get("query") or "").strip()
    verdict = str(payload.get("verdict") or "")
    job_ids = payload.get("job_ids") or []
    if not query or verdict not in ("up", "down"):
        raise HTTPException(status_code=422, detail="query 与 verdict(up/down) 必填")
    claims = caller(request)
    return feedback_store.add_feedback(query, verdict, job_ids, user=(claims or {}).get("u"))


@router.get("/gaps")
def rag_gaps(request: Request) -> dict[str, Any]:
    """语料缺口工单（staff）：拒答/空命中 query 聚类清单。"""
    from app.api._staff import require_staff

    require_staff(request)
    gaps = feedback_store.gaps()
    return {"total": len(gaps), "items": gaps[:100],
            "note": "同一 query 聚类计数；建议按 count 降序补对应文档"}


@router.get("/citations")
def rag_citations(request: Request) -> dict[str, Any]:
    """语料引用统计（staff）：job_id → 被引用次数（含 kbdoc_/cat:/doc:/kb: 等全部前缀）。"""
    from app.api._staff import require_staff

    require_staff(request)
    cites = feedback_store.citation_stats()
    items = sorted(cites.items(), key=lambda kv: -kv[1])
    return {"total": len(items), "items": [{"job_id": k, "count": v} for k, v in items]}
