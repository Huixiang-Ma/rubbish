"""语义检索 v2（rag_lab 验证后回填）：BGE-M3 向量 + BM25(n-gram) RRF 混合 + 租户过滤。

分层铁律（docs/行程规划标品方案.md §五）：本模块=检索知识层；实时状态走 API。
兜底链：DATABASE_URL 未配置 → 进程内存索引；OLLAMA 未配置 → mock 向量（维度自动切换）。
多意图：query_planner.decompose 规则门控 + LLM 拆分 + 实体校验（失败自动回退单路）。
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.services.bm25 import bm25_scores, rrf_fuse
from app.services.embedding import embed_batch
from app.services.pg_mirror import pg_mirror
from app.services.query_planner import decompose

_MEMORY: dict[str, list[dict[str, Any]]] = {}  # tenant → chunks（无 PG 时的内存兜底）
_POOL = 20  # 混合检索每路候选池


def add_chunk(job_id: str, content: str, tenant_id: str = "default") -> dict[str, Any]:
    """入库一块：向量化（批量/缓存）→ pgvector 或内存兜底。"""
    settings = get_settings()
    vector = embed_batch([content], settings)[0]
    pg_mirror._ensure()
    chunk_id = pg_mirror.add_chunk(job_id, content, vector, tenant_id)
    if chunk_id is None:
        bucket = _MEMORY.setdefault(tenant_id, [])
        bucket.append({"id": len(bucket) + 1, "job_id": job_id, "tenant_id": tenant_id,
                       "content": content, "embedding": vector})
        return {"mode": "memory", "embedder": settings.embedding_provider,
                "tenant_id": tenant_id, "id": bucket[-1]["id"]}
    return {"mode": "pg", "embedder": settings.embedding_provider,
            "tenant_id": tenant_id, "id": chunk_id}


def _memory_search(query_vec: list[float], tenant_id: str | None, k: int) -> list[dict[str, Any]]:
    rows = [r for r in _MEMORY.get(tenant_id or "default", []) if len(r["embedding"]) == len(query_vec)]
    scored = []
    for row in rows:
        dot = sum(a * b for a, b in zip(query_vec, row["embedding"]))
        na = sum(a * a for a in query_vec) ** 0.5 or 1.0
        nb = sum(b * b for b in row["embedding"]) ** 0.5 or 1.0
        scored.append({**{k2: row[k2] for k2 in ("id", "job_id", "tenant_id", "content")},
                       "distance": 1 - dot / (na * nb)})
    scored.sort(key=lambda x: x["distance"])
    return scored[:k]


def _memory_all(tenant_id: str | None) -> list[dict[str, Any]]:
    return _MEMORY.get(tenant_id or "default", [])


def all_chunks(tenant_id: str | None = None) -> list[dict[str, Any]]:
    """对外只读全量块（幂等检查用）：PG 已启用查 pgvector，否则查进程内存兜底。"""
    pg_mirror._ensure()
    if pg_mirror.enabled:
        return pg_mirror.all_chunks(tenant_id)
    return _memory_all(tenant_id)


def _search_once(query: str, settings, tenant_id: str | None, k: int) -> list[dict[str, Any]]:
    """单问题混合检索：稠密 top(pool) + BM25 top(pool) → RRF → k。dense 模式仅稠密。

    注意必须显式 _ensure()：enabled 属性只在 _ensure 成功后翻转，
    纯读路径（先 search 后 add）若不触发初始化会永久静默走内存兜底。
    """
    vec = embed_batch([query], settings)[0]
    pg_mirror._ensure()
    if pg_mirror.enabled:
        dense = pg_mirror.search_chunks(vec, k=_POOL, tenant_id=tenant_id)
        corpus = pg_mirror.all_chunks(tenant_id)
    else:
        dense = _memory_search(vec, tenant_id, _POOL)
        corpus = _memory_all(tenant_id)
    if settings.semantic_mode != "hybrid":
        return dense[:k]
    if not dense and not corpus:
        return []
    for rank, hit in enumerate(dense, start=1):
        hit["rrf_rank"] = rank
    bm_ranked = sorted(zip(corpus, bm25_scores(query, corpus)), key=lambda x: -x[1])
    bm_hits = [dict(rec, rrf_rank=rank + 1) for rank, (rec, score) in enumerate(bm_ranked[:_POOL]) if score > 0]
    return rrf_fuse([dense, bm_hits], top_k=k)


def search_similar(
    query: str, k: int = 3, tenant_id: str | None = None, multi: bool | None = None
) -> dict[str, Any]:
    """混合语义检索入口：多意图分解 → 多路 RRF；单意图单路。"""
    settings = get_settings()
    use_multi = settings.multi_intent if multi is None else multi
    subs = decompose(query) if use_multi else [query]

    if len(subs) <= 1:
        results = _search_once(query, settings, tenant_id, k)
    else:
        routes = [_search_once(sub, settings, tenant_id, k) for sub in subs]
        results = rrf_fuse(routes, top_k=k)

    return {
        "mode": "pg" if pg_mirror.enabled else "memory",
        "embedder": settings.embedding_provider,
        "tenant_id": tenant_id,
        "sub_questions": subs,
        "results": results,
    }
