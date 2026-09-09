"""RAG 问答服务（rag_lab 已验证口径回填）：检索 → 有据生成 → 拒答 → 引用溯源。

分层铁律：本服务=知识层；实时状态（票价/客流/天气）走 API，不经此处。
拒答两层防线（rag_lab BENCHMARKS v3+）：距离阈值 + prompt 强制"资料没有就说没找到"。
生成走 LLMClient（real=云模型 / mock=演示模板），LLM 失败不抛错——返回检索块兜底。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Iterator

from app.services.llm_client import LLMClient
from app.services.semantic import search_similar

_THINK_RE = re.compile(r"<think>.*?</think>", re.S)

GEN_SCORE_MAX = 0.8  # 最佳命中距离超过此值 → 拒答（宁可不答不编造）

_SYSTEM_PROMPT = (
    "你是文旅行程助手。请只依据下面的资料回答用户问题；"
    "资料中没有的信息，请明确回答\"知识库中未找到相关内容\"，禁止编造。\n"
    "回答简洁准确，在引用处标注资料编号，如 [1]。"
)


@dataclass
class RagConfig:
    top_k: int = 3
    score_max: float = GEN_SCORE_MAX
    multi: bool = True
    # 云 API 不可达时回退本地 Ollama（标品可用性：问答永不断供）
    fallback_model: str = "qwen2.5:1.5b-instruct"


def _build_prompt(question: str, sources: list[dict[str, Any]]) -> str:
    blocks = [f"[{i}] {s['content']}" for i, s in enumerate(sources, start=1)]
    return _SYSTEM_PROMPT + "\n\n【资料】\n" + ("\n\n".join(blocks) if blocks else "（无）") + f"\n\n【问题】{question}\n【回答】"


def _strip_think(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def ask(question: str, cfg: RagConfig | None = None, tenant_id: str | None = None,
        llm: LLMClient | None = None) -> dict[str, Any]:
    """同步问答：检索 → 生成/拒答。返回 {mode, answer, sources, sub_questions}。"""
    cfg = cfg or RagConfig()
    llm = llm or LLMClient()
    result = search_similar(question, k=cfg.top_k, tenant_id=tenant_id, multi=cfg.multi)
    sources = result["results"]
    sub_questions = result.get("sub_questions", [question])

    if not sources:
        return {"mode": "empty", "answer": "知识库中还没有与这个问题相关的内容。",
                "sources": [], "sub_questions": sub_questions}
    if sources[0]["distance"] > cfg.score_max:
        return {"mode": "refusal",
                "answer": f"知识库中未找到与该问题密切相关的内容（最接近块距离 {sources[0]['distance']:.2f}）。以下列出最接近的资料供参考。",
                "sources": sources, "sub_questions": sub_questions}

    answer = _generate(llm, _build_prompt(question, sources), fallback_model=cfg.fallback_model)
    if answer:
        return {"mode": "llm", "answer": answer, "sources": sources, "sub_questions": sub_questions}
    return {"mode": "retrieval", "answer": "", "sources": sources, "sub_questions": sub_questions}


def _generate(llm: LLMClient, prompt: str, fallback_model: str = "") -> str:
    """生成文本：LLMClient 统一通道（云 API real→httpx 失败自动降级 raw socket，
    实测部分网关 WAF 按 TLS 指纹拒绝 httpx 连接）→ 仍失败回退本地 Ollama → 空串（兜底检索模式）。"""
    mode = getattr(llm, "mode", "mock")
    if mode == "real" and getattr(llm, "api_key", ""):
        text = llm.generate_text(prompt, system=_SYSTEM_PROMPT)
        if text:
            return text
    if fallback_model:
        try:
            from app.config import get_settings

            ollama_url = get_settings().embedding_ollama_url
            import httpx

            resp = httpx.post(
                ollama_url.rstrip("/") + "/api/chat",
                json={"model": fallback_model, "messages": [{"role": "user", "content": prompt}],
                      "stream": False, "options": {"temperature": 0.1}},
                timeout=120.0,
            )
            resp.raise_for_status()
            content = (resp.json().get("message") or {}).get("content", "")
            text = _strip_think(content)
            if text:
                return text
        except Exception:
            pass
    return ""


def stream_ask(question: str, cfg: RagConfig | None = None, tenant_id: str | None = None,
               llm: LLMClient | None = None) -> Iterator[dict[str, Any]]:
    """流式问答：meta → token* → done（对齐 rag_lab SSE 事件口径，拒答/空命中短路）。

    real 模式下经 Ollama/OpenAI 兼容流式；mock 模式直接落 done（检索模式）。
    """
    cfg = cfg or RagConfig()
    llm = llm or LLMClient()
    result = search_similar(question, k=cfg.top_k, tenant_id=tenant_id, multi=cfg.multi)
    sources = result["results"]
    sub_questions = result.get("sub_questions", [question])
    yield {"type": "meta", "sources": sources, "sub_questions": sub_questions}

    if not sources:
        yield {"type": "done", "mode": "empty", "answer": "知识库中还没有与这个问题相关的内容。",
               "sources": [], "metrics": None}
        return
    if sources[0]["distance"] > cfg.score_max:
        yield {"type": "done", "mode": "refusal", "metrics": None, "sources": sources,
               "answer": f"知识库中未找到与该问题密切相关的内容（最接近块距离 {sources[0]['distance']:.2f}）。"}
        return

    prompt = _build_prompt(question, sources)
    pieces: list[str] = []
    try:
        for delta in _stream_generate(llm, prompt, fallback_model=cfg.fallback_model):
            pieces.append(delta)
            yield {"type": "token", "text": delta}
    except Exception:
        pass  # 流式失败不中断：落 done 兜底
    full = "".join(pieces).strip()
    if not full:
        yield {"type": "done", "mode": "retrieval", "answer": "", "sources": sources, "metrics": None}
        return
    yield {"type": "done", "mode": "llm", "answer": full, "sources": sources, "metrics": None}


def _stream_generate(llm: LLMClient, prompt: str, fallback_model: str = "") -> Iterator[str]:
    """流式生成。

    实测上游网关按 TLS 指纹拦截 httpx 流式长连接（SSL 瞬断必现），故 real 模式
    直接走 LLMClient 的 raw-socket 短连接通道一次生成，再把答案切分为 token 事件
    发出——对外事件口径（meta → token* → done）与真流式一致。
    """
    mode = getattr(llm, "mode", "mock")
    if mode != "real" or not getattr(llm, "api_key", ""):
        return iter(())  # 空流 → done 兜底为 retrieval 模式

    text = llm.generate_text(prompt, system=_SYSTEM_PROMPT)
    if not text:
        # 云通道整体失败 → 回退本地 Ollama（同样一次生成，切块下发）
        if fallback_model:
            text = _generate(llm, prompt, fallback_model=fallback_model)
    text = _strip_think(text)
    if not text:
        return iter(())
    # 按自然块切分：先句、再固定长度，保证前端有打字机效果
    pieces: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in "。！？；\n":
            pieces.append(buf)
            buf = ""
    if buf:
        pieces.append(buf)
    return iter(pieces)
