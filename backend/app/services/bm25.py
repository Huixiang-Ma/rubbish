"""BM25 关键词打分（字符 n-gram 分词，零依赖）——rag_lab 验证后回填。

混合检索的关键词路：精确专名/字面匹配强项，与稠密向量互补后 RRF 融合。
分词决策（DECISIONS §3）：中文 unigram+bigram + 英文数字词；jieba 为可选升级。
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any


def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens: list[str] = []
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        tokens.extend(seg)
        tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
    tokens.extend(re.findall(r"[a-z0-9]+", text))
    return tokens


def bm25_scores(
    query: str, records: list[dict[str, Any]], content_key: str = "content",
    k1: float = 2.5, b: float = 0.75,
) -> list[float]:
    """对记录列表打 BM25 分（与 query 的相关性，无界分数，仅用于排序）。"""
    n = len(records)
    if n == 0:
        return []
    doc_tokens = [tokenize(r.get(content_key, "")) for r in records]
    avgdl = (sum(len(t) for t in doc_tokens) / n) or 1.0
    df: Counter = Counter()
    for toks in doc_tokens:
        df.update(set(toks))
    q_tokens = tokenize(query)
    scores: list[float] = []
    for toks in doc_tokens:
        tf = Counter(toks)
        dl = len(toks) or 1
        score = 0.0
        for term in q_tokens:
            if term not in tf:
                continue
            idf = math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1)
            score += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * dl / avgdl))
        scores.append(score)
    return scores


def rrf_fuse(rank_lists: list[list[dict[str, Any]]], k: int = 60, top_k: int = 3,
             key_field: str = "content") -> list[dict[str, Any]]:
    """多路排名列表 → RRF 融合（按 1/(k+rank) 聚合，同记录跨路叠加）。"""
    fused: dict[Any, dict[str, Any]] = {}
    scores: dict[Any, float] = {}
    for hits in rank_lists:
        for rank, hit in enumerate(hits, start=1):
            key = hit.get(key_field)
            fused.setdefault(key, hit)
            scores[key] = scores.get(key, 0.0) + 1 / (k + rank)
    ordered = sorted(scores, key=lambda x: -scores[x])[:top_k]
    return [dict(fused[key], rrf=round(scores[key], 4)) for key in ordered]
