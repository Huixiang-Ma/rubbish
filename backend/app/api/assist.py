"""toC 体验增强 API：行程评分 → 知识库攻略沉淀，与 RAG 联网问答助手。

- 评分：`POST /api/plans/{job_id}/rating`（1-5 星 + 评论，登录游客维度，落 DATA_ROOT JSON）；
- 沉淀：`POST /api/plans/{job_id}/rate-ingest` 高分（≥4 星）行程书摄入 RAG 语料
  （job_id 前缀 kb:，与标品语料 cat: 并存），后续 RAG 检索即可引用该攻略；
- 上架：`POST /api/plans/{job_id}/rate-listing` 高分行程一键沉淀为 toB 可售线路方案
  （复用 shop_store.plan_create，写入方案馆覆盖层，游客端商城立即可见）；
- 问答助手：`POST /api/rag/assistant`（同步）与 `POST /api/rag/assistant/chat`（SSE 流式）——
  先走知识库 RAG；未命中（empty/refusal）自动联网搜索（web_search_agent），LLM 有据综合，
  回答标明「知识库 / 联网」来源，两路都不可用时如实拒答不编造。
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Iterator

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api._staff import caller
from app.config import get_settings
from app.services import semantic, shop_store, web_search_agent
from app.services.llm_client import LLMClient
from app.services.paths import DATA_ROOT
from app.services.rag_service import _SYSTEM_PROMPT, _build_prompt, _strip_think
from app.services.semantic import search_similar as _search

router = APIRouter(tags=["体验增强：评分沉淀 / RAG 问答助手"])

_RATINGS_FILE = DATA_ROOT / "plan_ratings.json"
_RATINGS_LOCK = threading.Lock()
_GOOD_THRESHOLD = 4  # 评分 ≥4 星才可沉淀攻略/上架


# ----------------------------------------------------------------------------
# 行程评分
# ----------------------------------------------------------------------------
class RatingRequest(BaseModel):
    score: int = Field(..., ge=1, le=5)
    comment: str = ""
    operator: str | None = None


def _ratings_all() -> dict[str, Any]:
    if not _RATINGS_FILE.exists():
        return {"ratings": {}}
    try:
        return json.loads(_RATINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"ratings": {}}


def _save_ratings(doc: dict[str, Any]) -> None:
    _RATINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _RATINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_RATINGS_FILE)


def _plan_md(job_id: str) -> str:
    from app.services.markdown_reporter import MarkdownReporter

    md, _ = MarkdownReporter().read_result(job_id)
    return md


@router.get("/api/plans/{job_id}/rating")
def get_rating(job_id: str) -> dict[str, Any]:
    """单任务评分汇总（平均分 + 人数 + 明细）。"""
    doc = _ratings_all()
    rows = doc["ratings"].get(job_id) or []
    avg = round(sum(r["score"] for r in rows) / len(rows), 1) if rows else None
    return {"job_id": job_id, "count": len(rows), "avg": avg,
            "can_ingest": bool(rows and avg and avg >= _GOOD_THRESHOLD), "items": rows[-20:]}


@router.post("/api/plans/{job_id}/rating")
def post_rating(job_id: str, payload: RatingRequest, request: Request) -> dict[str, Any]:
    state_dir = DATA_ROOT / job_id
    if not (state_dir / "travel_plan.md").exists():
        raise HTTPException(status_code=404, detail="行程任务不存在")
    user = (caller(request) or {}).get("u") or "guest"
    with _RATINGS_LOCK:
        doc = _ratings_all()
        rows = doc["ratings"].setdefault(job_id, [])
        # 同一用户重复评分：覆盖旧分（演示口径）
        rows[:] = [r for r in rows if r.get("user") != user]
        rows.append({"user": user, "score": payload.score, "comment": payload.comment[:200],
                     "at": time.strftime("%Y-%m-%d %H:%M")})
        _save_ratings(doc)
    avg = round(sum(r["score"] for r in rows) / len(rows), 1)
    return {"ok": True, "avg": avg, "count": len(rows),
            "good": avg >= _GOOD_THRESHOLD,
            "hint": "评分较高，可沉淀为知识库攻略或上架为线路方案" if avg >= _GOOD_THRESHOLD else ""}


# ----------------------------------------------------------------------------
# 高分行程 → 知识库攻略（RAG 语料）
# ----------------------------------------------------------------------------
def _ingest_guide(job_id: str, state_dir: Path, source_note: str) -> dict[str, Any]:
    md = _plan_md(job_id)
    if not md.strip():
        raise HTTPException(status_code=400, detail="行程书内容为空，无法沉淀")
    ui = {}
    try:
        ui = json.loads((state_dir / "state.json").read_text(encoding="utf-8")).get("user_input", {})
    except Exception:
        pass
    head = f"【攻略】{ui.get('destination') or job_id} {ui.get('days', '')}日行程攻略（评分沉淀 · {source_note}）"
    content = f"{head}\n{md[:4000]}"
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
    kb_id = f"kb:{job_id}:{digest}"
    res = semantic.add_chunk(kb_id, content, "default")
    return {"kb_id": kb_id, "mode": res.get("mode"), "embedder": res.get("embedder"),
            "chars": len(content)}


@router.post("/api/plans/{job_id}/rate-ingest")
def rate_ingest(job_id: str, request: Request) -> dict[str, Any]:
    """高分（≥4 星均分）行程书 → RAG 知识库攻略。低分/未评分 400。"""
    doc = _ratings_all()
    rows = doc["ratings"].get(job_id) or []
    if not rows:
        raise HTTPException(status_code=400, detail="请先评分，再沉淀攻略")
    avg = sum(r["score"] for r in rows) / len(rows)
    if avg < _GOOD_THRESHOLD:
        raise HTTPException(status_code=400, detail=f"平均分 {avg:.1f} 低于 {_GOOD_THRESHOLD} 星，暂不满足沉淀条件")
    state_dir = DATA_ROOT / job_id
    if not (state_dir / "travel_plan.md").exists():
        raise HTTPException(status_code=404, detail="行程任务不存在")
    res = _ingest_guide(job_id, state_dir, f"均分 {avg:.1f}")
    return {"ok": True, "avg": round(avg, 1), **res}


@router.post("/api/plans/{job_id}/rate-listing")
def rate_listing(job_id: str, request: Request) -> dict[str, Any]:
    """高分行程一键沉淀为可售线路方案（方案上架，游客端商城可见）。"""
    doc = _ratings_all()
    rows = doc["ratings"].get(job_id) or []
    if not rows:
        raise HTTPException(status_code=400, detail="请先评分，再上架方案")
    avg = sum(r["score"] for r in rows) / len(rows)
    if avg < _GOOD_THRESHOLD:
        raise HTTPException(status_code=400, detail=f"平均分 {avg:.1f} 低于 {_GOOD_THRESHOLD} 星，暂不满足上架条件")
    state_dir = DATA_ROOT / job_id
    if not (state_dir / "travel_plan.md").exists():
        raise HTTPException(status_code=404, detail="行程任务不存在")
    try:
        ui = json.loads((state_dir / "state.json").read_text(encoding="utf-8")).get("user_input", {})
    except Exception:
        ui = {}
    city = str(ui.get("destination") or "苏州")
    days = max(1, int(ui.get("days") or 3))
    budget = int(ui.get("budget") or 0)
    per = max(199, min(9999, (budget // max(1, days)) if budget else days * 580))
    plan = shop_store.plan_create({
        "title": f"{city}{days}日 · 评分甄选线路（{avg:.1f} 分）",
        "city": city, "category": "评分甄选", "days": days,
        "per_price": per, "original_per_price": round(per * 1.15),
        "stock": 20, "min_persons": 2,
        "subtitle": f"由用户真实行程沉淀（评分 {avg:.1f}），路线经过实战检验",
        "badges": [f"评分 {avg:.1f}", "用户甄选"],
    })
    return {"ok": True, "plan_id": plan.get("id"), "title": plan.get("title"), "avg": round(avg, 1)}


# ----------------------------------------------------------------------------
# toB 知识库文档构建：文本/Markdown 文档 → 分块 → 语义摄入（kb: 前缀语料）
# ----------------------------------------------------------------------------
_KB_DOCS_FILE = DATA_ROOT / "kb_docs.json"
_KB_LOCK = threading.Lock()


def _kb_docs() -> dict[str, Any]:
    if not _KB_DOCS_FILE.exists():
        return {"docs": []}
    try:
        return json.loads(_KB_DOCS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"docs": []}


def _save_kb_docs(doc: dict[str, Any]) -> None:
    _KB_DOCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _KB_DOCS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_KB_DOCS_FILE)


def _chunk_text(text: str, size: int = 500, overlap: int = 60) -> list[str]:
    """按段落聚合分块（size 字符上限，overlap 字符重叠）。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 1 <= size:
            buf = f"{buf}\n{p}".strip()
        else:
            if buf:
                chunks.append(buf)
            while len(p) > size:  # 超长段落硬切
                chunks.append(p[:size])
                p = p[size - overlap:]
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


class KbDocRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=30000)
    tags: list[str] = Field(default_factory=list)


@router.get("/api/kb/docs")
def kb_list() -> dict[str, Any]:
    """知识库文档清单（含块数与摄入状态）。"""
    doc = _kb_docs()
    rows = []
    for d in doc.get("docs", []):
        rows.append({k: d.get(k) for k in ("id", "title", "tags", "chunks", "chars", "mode", "embedder", "created_at")})
    total = sum(r.get("chunks", 0) for r in rows)
    return {"total": len(rows), "chunks": total, "docs": rows}


@router.post("/api/kb/docs")
def kb_create(payload: KbDocRequest) -> dict[str, Any]:
    """上传知识库文档：入库 JSON 台账 + 分块摄入语义层（kb: 前缀，RAG 可检索）。"""
    doc_id = "kbdoc_" + hashlib.sha1(f"{payload.title}{time.time()}".encode()).hexdigest()[:10]
    chunks = _chunk_text(payload.content)
    if not chunks:
        raise HTTPException(status_code=400, detail="文档内容解析为空")
    mode, embedder = "memory", None
    with _KB_LOCK:
        for i, c in enumerate(chunks):
            res = semantic.add_chunk(f"{doc_id}#{i + 1}", f"【{payload.title}】{c}", "default")
            mode, embedder = res.get("mode", mode), res.get("embedder", embedder)
    record = {"id": doc_id, "title": payload.title, "tags": payload.tags[:6],
              "chunks": len(chunks), "chars": len(payload.content),
              "mode": mode, "embedder": embedder, "created_at": time.strftime("%Y-%m-%d %H:%M")}
    with _KB_LOCK:
        d = _kb_docs()
        d.setdefault("docs", []).insert(0, record)
        _save_kb_docs(d)
    return {"ok": True, **record}


@router.delete("/api/kb/docs/{doc_id}")
def kb_delete(doc_id: str) -> dict[str, Any]:
    """删除知识库文档：台账移除 + 语义层同前缀语料清理（内存/PG 全量重扫）。"""
    with _KB_LOCK:
        d = _kb_docs()
        before = len(d.get("docs", []))
        d["docs"] = [x for x in d.get("docs", []) if x.get("id") != doc_id]
        if len(d["docs"]) == before:
            raise HTTPException(status_code=404, detail="文档不存在")
        _save_kb_docs(d)
    removed = 0
    try:
        rows = semantic.all_chunks(None)
        doomed = [r for r in rows if str(r.get("job_id", "")).startswith(doc_id)]
        removed = len(doomed)
        # 语义层无按 job_id 删除的通用口：PG 模式按 chunk 主键删，内存模式重建桶
        if semantic.pg_mirror.enabled and doomed:
            from sqlalchemy import text as _text

            with semantic.pg_mirror.engine.connect() as conn:
                for r in doomed:
                    conn.execute(_text("DELETE FROM document_chunks WHERE id = :i"), {"i": r.get("id")})
                conn.commit()
        semantic._MEMORY = {t: [c for c in bucket if not str(c.get("job_id", "")).startswith(doc_id)]
                            for t, bucket in semantic._MEMORY.items()}
    except Exception:
        pass
    return {"ok": True, "removed_chunks": removed}


# ----------------------------------------------------------------------------
# toC RAG 问答助手（知识库未命中 → agent 联网搜索）
# ----------------------------------------------------------------------------
_ASSISTANT_SYSTEM = (
    "你是文旅问答助手。请依据下面的资料回答用户问题；资料没有的信息明确说明，禁止编造。"
    "回答简洁准确，引用处标注资料编号如 [1]。"
)


_REFUSAL_MARKS = ("知识库中未找到", "未找到相关内容", "资料中没有", "无法回答", "没有找到与该问题")


def _looks_refusal(answer: str) -> bool:
    return any(mark in (answer or "") for mark in _REFUSAL_MARKS)


def _assistant_answer(message: str, top_k: int, tenant_id: str | None) -> dict[str, Any]:
    """知识库 RAG → 未命中（空命中/超阈值/LLM 拒答式回答）联网搜索 → LLM 综合。"""
    llm = LLMClient()
    kb_sources: list[dict[str, Any]] = []
    kb_answer = ""
    # 1) 知识库优先
    try:
        res = _search(message, k=top_k, tenant_id=tenant_id, multi=True)
        sources = res.get("results", [])
    except Exception:
        sources = []
    kb_sources = [{"n": i + 1, "source": "kb", "title": (s.get("job_id") or "").removeprefix("cat:").removeprefix("kb:"),
                   "content": s.get("content", ""), "distance": s.get("distance")}
                  for i, s in enumerate(sources[:top_k])]
    kb_hit = bool(kb_sources) and kb_sources[0]["distance"] is not None and kb_sources[0]["distance"] <= 0.8
    if kb_hit:
        kb_answer = _strip_think(llm.generate_text(_build_prompt(message, sources[:top_k]), system=_SYSTEM_PROMPT) or "")
        if kb_answer and not _looks_refusal(kb_answer):
            return {"mode": "kb", "answer": kb_answer, "citations": kb_sources, "web": None}
    # 2) 联网兜底（KB 空命中 / 超阈值 / LLM 明确拒答 / LLM 失败）
    web = web_search_agent.web_search(message)
    web_sources = [{"n": i + 1, "source": "web", "title": w["title"], "content": w["snippet"], "url": w["url"]}
                   for i, w in enumerate(web.get("results", []))]
    if web_sources:
        prompt = _build_prompt(message + "\n（以下为实时联网检索结果，请综合回答并在开头注明「据实时联网信息」）",
                               [{"content": f"{s['title']}：{s['content']}"} for s in web_sources])
        answer = _strip_think(llm.generate_text(prompt, system=_ASSISTANT_SYSTEM) or "")
        if answer and not _looks_refusal(answer):
            return {"mode": "web", "answer": answer,
                    "citations": web_sources, "web": {"provider": web.get("provider")}}
        if web.get("results"):
            digest = "\n".join(f"[{s['n']}] {s['title']}：{s['content'][:120]}" for s in web_sources[:4])
            return {"mode": "web_retrieval", "answer": f"据实时联网信息（LLM 综合暂不可用，以下为检索摘要）：\n{digest}",
                    "citations": web_sources, "web": {"provider": web.get("provider")}}
    # 3) 两路都不可用：如实拒答（KB 有参考块时列出供延伸阅读）
    if kb_sources:
        return {"mode": "kb_refusal",
                "answer": kb_answer or ("知识库中未找到与该问题密切相关的内容。以下列出最接近的资料供参考：\n"
                + "\n".join(f"[{s['n']}] {s['content'][:100]}" for s in kb_sources[:3])),
                "citations": kb_sources, "web": {"provider": web.get("provider"), "note": web.get("note")}}
    return {"mode": "empty",
            "answer": "知识库与联网检索都没有找到相关内容，请换个问法试试。",
            "citations": [],
            "web": {"provider": web.get("provider"), "note": web.get("note")}}


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=8)
    tenant_id: str | None = None


@router.post("/api/rag/assistant")
def rag_assistant(payload: AssistantRequest) -> dict[str, Any]:
    return _assistant_answer(payload.message.strip(), payload.top_k, payload.tenant_id)


@router.post("/api/rag/assistant/chat")
def rag_assistant_chat(payload: AssistantRequest):
    """SSE 流式：meta（来源模式）→ token* → done。"""

    def sse() -> Iterator[str]:
        try:
            result = _assistant_answer(payload.message.strip(), payload.top_k, payload.tenant_id)
            yield "data: " + json.dumps({"type": "meta", "mode": result["mode"],
                                          "citations": result["citations"]}, ensure_ascii=False) + "\n\n"
            answer = result.get("answer") or ""
            # 按句切块下发（打字机效果）
            buf = ""
            for ch in answer:
                buf += ch
                if ch in "。！？；\n":
                    yield "data: " + json.dumps({"type": "token", "text": buf}, ensure_ascii=False) + "\n\n"
                    buf = ""
            if buf:
                yield "data: " + json.dumps({"type": "token", "text": buf}, ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps({"type": "done", "mode": result["mode"], "answer": answer,
                                          "citations": result["citations"], "web": result.get("web")},
                                         ensure_ascii=False) + "\n\n"
        except Exception as exc:
            yield "data: " + json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
