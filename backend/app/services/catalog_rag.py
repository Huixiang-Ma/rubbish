"""标品知识化（B 档）：让"标品"内容由知识语料实时检索支撑，而非只读静态文案。

数据源：app/data/catalog_knowledge.json —— 一条 doc 对应一个标品，
        id 与当前标品目录及线路 product_ids 逐一对齐。
摄入：ensure_corpus() 惰性调用 semantic.add_chunk 逐条入库
      （DATABASE_URL 未配 → 进程内存兜底；embedding 不可达 → 自动降级为"无背书"）。
背书：ground_terms() 对站点名做「本体锚定 + BM25」确定性检索——
      只有当检索层存在该站点的**自身语料**且词面证据 >0 才算「知识背书」，
      避免 mock/低质向量把 A 站内容误配到 B 站。snippet 直接取自语料原文（可溯源）。

口径：知识检索失败绝不阻塞商品接口——语料缺失/未摄入时自然返回 matched=False。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services import semantic
from app.services.bm25 import bm25_scores
from app.services.pg_mirror import pg_mirror

_CATALOG_FILE = Path(__file__).resolve().parents[1] / "data" / "catalog_knowledge.json"
_JOB_PREFIX = "cat:"
_booted = False

_NORM_KEEP = re.compile(r"[\u4e00-\u9fff0-9a-zA-Z]+")


def _norm(text: str) -> str:
    """归一名用于本体对齐：只保留中英文与数字（去掉括号/空格/标点）。"""
    return "".join(_NORM_KEEP.findall(text or "")).lower()


def documents() -> list[dict[str, Any]]:
    """读取语料（读失败/文件缺失返回空，绝不抛给调用方）。"""
    try:
        with open(_CATALOG_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
        docs = raw.get("docs", []) if isinstance(raw, dict) else raw
        return [d for d in docs if isinstance(d, dict) and d.get("id")]
    except Exception:
        return []


def _corpus_state() -> dict[str, Any]:
    settings = get_settings()
    return {
        "docs": len(documents()),
        "mode": "pg" if pg_mirror.enabled else "memory",
        "embedder": settings.embedding_provider,
    }


def _ingested_count() -> int:
    """检索层里已摄入的语料块数（按 job_id 前缀统计，用于幂等）。"""
    rows = semantic.all_chunks(None)
    return sum(1 for r in rows if str(r.get("job_id", "")).startswith(_JOB_PREFIX))


def ensure_corpus(force: bool = False) -> dict[str, Any]:
    """幂等摄入语料；embedding 不可达时停止摄入并如实上报（背书自然为空）。"""
    global _booted
    state = _corpus_state()
    if not force and _booted:
        return {**state, "booted": True, "ingested": _ingested_count()}

    docs = documents()
    if not docs:
        _booted = True
        return {**state, "booted": True, "ingested": 0, "note": "catalog 语料缺失或为空"}

    # PG 已落库过同源语料则跳过（重启进程不重复入库）；内存模式靠 _booted + 计数去重
    existing = _ingested_count()
    added = 0
    if existing < len(docs) or force:
        for d in docs:
            try:
                semantic.add_chunk(f"{_JOB_PREFIX}{d['id']}", d["content"], "default")
                added += 1
            except Exception:
                break  # embedding 后端不可用：停止摄入，本轮背书留空、不抛 5xx
    _booted = True
    return {**state, "booted": True, "ingested": _ingested_count(), "existing": existing, "added": added}


def _bm25_to_score(raw: float) -> float:
    """把无界 BM25 分单调映射到 (0,1]：有证据即 >0。"""
    return round(1.0 - 1.0 / (1.0 + raw), 3)


def ground_terms(terms: list[Any], tenant_id: str | None = None) -> dict[str, Any]:
    """对站点名逐一做「本体锚定」语料背书。

    terms 元素可为字符串（站点名，与语料 doc.name 同源）或 {name, city}。
    命中条件 = 检索层存在该站点的自身语料 且 BM25 词面证据 > 0；
    不满足即 matched=False（可能：语料缺失 / 未摄入 / 检索不可用）。

    注：mock embedder 的向量无语义区分度，此处刻意走词面路，
    避免 A 站内容被误配到 B 站；真实 embedder 的别名召回由 RAG ask 等通道承担。
    """
    ensure_corpus()
    docs = documents()
    own_by_norm: dict[str, dict[str, Any]] = {}
    for d in docs:
        own_by_norm.setdefault(_norm(d.get("name", "")), d)

    # 检索层中已摄入的语料行：job_id 前缀 cat: → product_id
    rows = [r for r in semantic.all_chunks(None)
            if str(r.get("job_id", "")).startswith(_JOB_PREFIX)]

    items: list[dict[str, Any]] = []
    for t in terms[:200]:
        if isinstance(t, dict):
            name = str(t.get("name") or t.get("term") or "").strip()
        else:
            name = str(t or "").strip()
        rec: dict[str, Any] = {"term": name, "matched": False, "score": 0.0,
                               "product_id": None, "snippet": None}
        key = _norm(name)
        own = own_by_norm.get(key)
        if name and own:
            row = next((r for r in rows if str(r.get("job_id", "")) == f"{_JOB_PREFIX}{own['id']}"), None)
            if row is not None:
                raw = bm25_scores(name, [row])[0] if row.get("content") else 0.0
                if raw > 0:
                    content = str(row.get("content") or "")
                    rec.update(matched=True, product_id=own["id"], score=_bm25_to_score(raw),
                               snippet=content[:90] + ("…" if len(content) > 90 else ""))
        items.append(rec)

    return {"stats": {**_corpus_state(), "ingested": len(rows)},
            "total": len(items), "matched": sum(1 for i in items if i["matched"]), "items": items}
