"""标品行程组装器（Composer）：RAG 选品 + 确定性排程。

选品即检索（标品使用 RAG 实现的核心落点）：
  - catalog_rag.ensure_corpus() 把标品知识语料（catalog_knowledge.json，与素材库 id 对齐）
    摄入语义检索层（pgvector / 进程内存）；
  - search_by_theme() 用自然语言主题（如「园林 文化 2 日 亲子」）走 hybrid 检索
    （BGE-M3 向量 + BM25 RRF）命中标品知识块，job_id 前缀 cat: 还原为标品 id 与素材库行合并；
  - 检索不可用 / 语料为空时自动降级为分类词面过滤，绝不让组装主链路 5xx。

排程为确定性算法（与前端 tripFactory 同口径）：餐饮占午间、地理就近、节奏密度
（悠闲 3 段/天、标准 4 段、紧凑 5 段）、每个排入块附 RAG 知识背书（enrich_block）。
"""
from __future__ import annotations

import math
import re
from typing import Any

from app.services import material_store
from app.services.catalog_rag import _JOB_PREFIX, ensure_corpus
from app.services.semantic import search_similar

_PACE_SLOTS = {
    "relaxed": ["morning", "afternoon", "evening"],
    "standard": ["morning", "midday", "afternoon", "evening"],
    "tight": ["morning", "midday", "afternoon", "evening", "night"],
}
_SLOT_START = {
    "morning": "08:30", "midday": "11:30",
    "afternoon": "14:00", "evening": "17:30", "night": "21:00",
}
_SLOT_ZH = {"morning": "上午", "midday": "午间", "afternoon": "下午", "evening": "傍晚", "night": "夜游"}
_BUDGET_WEIGHTS = {"transport": 0.18, "lodging": 0.32, "food": 0.28, "tickets": 1.0}


def _product_rows() -> list[dict[str, Any]]:
    """已上架素材行（Composer 目录口径）。"""
    return material_store.product_rows()


def _ticket_of(p: dict[str, Any]) -> int:
    """标品门票成本：skus 最低正价，无 sku 用 price_min。"""
    prices = [int(s.get("price") or 0) for s in (p.get("skus") or []) if int(s.get("price") or 0) > 0]
    if prices:
        return min(prices)
    return int(p.get("price_min") or 0)


def search_products(query: str, top_k: int = 12, city: str = "", category: str = "") -> dict[str, Any]:
    """RAG 选品：主题/需求自然语言 → 语义检索标品知识块 → 对齐素材库行。

    返回 {mode, results:[{product, score, snippet}]}；检索不可用时 mode=keyword，
    按分类/城市词面兜底（保证演示链路永不断供）。
    """
    rows = _product_rows()
    by_id = {p.get("id"): p for p in rows if p.get("id")}
    # 按需补齐租户语料（幂等，进程内只入一次）
    ensure_corpus()

    mode = "rag"
    hits: list[dict[str, Any]] = []
    if query:
        try:
            res = search_similar(query, k=max(top_k * 2, 20), multi=False)
            for r in res.get("results", []):
                pid = str(r.get("job_id", "")).removeprefix(_JOB_PREFIX)
                p = by_id.get(pid)
                if not p:
                    continue
                hits.append({"product": p, "score": float(r.get("rrf") or 0.0),
                             "distance": r.get("distance"), "snippet": (r.get("content") or "")[:90]})
        except Exception:
            hits = []
    if not hits:
        mode = "keyword"
        kw = query or ""
        for p in rows:
            blob = " ".join(str(p.get(f) or "") for f in ("name", "category", "city", "description", "tags"))
            if not kw or any(t and t in blob for t in re.split(r"[\s,，、]+", kw) if t):
                hits.append({"product": p, "score": 1.0, "distance": None, "snippet": ""})

    # 硬过滤（城市/分类）后去重截断
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for h in hits:
        p = h["product"]
        pid = str(p.get("id"))
        if pid in seen:
            continue
        if city and city not in str(p.get("city") or ""):
            continue
        if category and p.get("category") != category:
            continue
        seen.add(pid)
        results.append({"product": p, "score": round(h["score"], 4),
                        "matched_by": mode, "snippet": h["snippet"]})
        if len(results) >= top_k:
            break
    return {"mode": mode, "total": len(results), "results": results}


def enrich_block(product: dict[str, Any]) -> dict[str, Any] | None:
    """行程块知识背书：检索该标品自身语料，命中返回摘要卡片（知识层失败静默降级）。"""
    try:
        res = search_similar(str(product.get("name") or ""), k=1, multi=False)
        rows = res.get("results") or []
        if rows:
            content = str(rows[0].get("content") or "")
            if content:
                return {"content": content[:120] + ("…" if len(content) > 120 else ""),
                        "source": rows[0].get("job_id"), "distance": rows[0].get("distance")}
    except Exception:
        pass
    return None


def _haversine_m(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b:
        return 0.0
    lon1, lat1, lon2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def compose(product_ids: list[str], days: int = 2, pace: str = "standard",
            city: str = "", budget: int | None = None) -> dict[str, Any]:
    """确定性排程：选中标品 → 逐日逐时段行程（含 RAG 知识背书）+ 预算分项 + 覆盖率。"""
    rows = _product_rows()
    by_id = {p.get("id"): p for p in rows if p.get("id")}
    # 兼容知识库 id（与素材库对齐）+ 容错未知 id
    selected = [by_id[i] for i in product_ids if i in by_id]

    slots = _PACE_SLOTS.get(pace, _PACE_SLOTS["standard"])
    per_day = len(slots)
    days = max(1, min(7, days))

    # 排程：餐饮尽量占午间（midday），其余按选择顺序填空位；同城相邻优先（地理就近排序起点）
    ordered = selected
    if city:
        ordered = sorted(selected, key=lambda p: 0 if city in str(p.get("city") or "") else 1)
    queue = list(ordered)
    food = [p for p in queue if p.get("category") == "餐饮"]
    others = [p for p in queue if p.get("category") != "餐饮"]

    itinerary: list[dict[str, Any]] = []
    used = 0
    for d in range(1, days + 1):
        blocks: list[dict[str, Any]] = []
        for slot in slots:
            if slot == "midday" and food:
                p = food.pop(0)
            elif others:
                p = others.pop(0)
            elif food:
                p = food.pop(0)
            else:
                continue
            used += 1
            block = {
                "slot": slot, "slot_zh": _SLOT_ZH.get(slot, slot), "start": _SLOT_START.get(slot, ""),
                "duration": p.get("typical_dwell") or "2h",
                "product_id": p.get("id"), "title": p.get("name"), "type": p.get("category"),
                "note": f"{p.get('city')} · {'、'.join(p.get('tags') or []) or '推荐打卡'}",
            }
            knowledge = enrich_block(p)
            if knowledge:
                block["knowledge"] = knowledge
            blocks.append(block)
        itinerary.append({"day": d, "blocks": blocks})

    missing_slots = max(0, len(selected) - used)
    tickets_total = sum(_ticket_of(p) for p in selected)
    budget_estimate = {
        "tickets": tickets_total,
        "transport": round(tickets_total * _BUDGET_WEIGHTS["transport"]),
        "lodging": round(tickets_total * _BUDGET_WEIGHTS["lodging"]),
        "food": round(tickets_total * _BUDGET_WEIGHTS["food"]),
    }
    budget_estimate["total"] = sum(budget_estimate.values())
    warnings: list[str] = []
    if missing_slots:
        warnings.append(f"仍有 {missing_slots} 个标品未排入，建议增加天数或减少节奏密度")
    if budget and budget_estimate["total"] > budget:
        warnings.append(f"估算总预算 ¥{budget_estimate['total']} 超出给定预算 ¥{budget}")
    coverage = round(min(1.0, used / max(1, days * per_day)), 2)
    job_id = f"compose_{int(__import__('time').time())}"
    return {"job_id": job_id, "days": days, "pace": pace, "itinerary": itinerary,
            "budget_estimate": budget_estimate, "coverage_score": coverage,
            "missing_slots": missing_slots, "warnings": warnings,
            "product_ids": [p.get("id") for p in selected], "city": city or None}


def preview(body: dict[str, Any]) -> dict[str, Any]:
    """拖拽过程预览：按时段校验 best_slot 错配 + 相邻点间距估算总路程。"""
    slots = body.get("slots") or []
    rows = _product_rows()
    by_id = {p.get("id"): p for p in rows if p.get("id")}
    conflicts = 0
    total_m = 0.0
    duration = 0.0
    prev: dict[str, Any] | None = None
    for s in slots:
        p = by_id.get(str(s.get("product_id") or ""))
        if not p:
            continue
        slot = str(s.get("slot") or "")
        if p.get("best_slot") and slot and p.get("best_slot") != slot:
            conflicts += 1
        duration += float(re.findall(r"\d+(?:\.\d+)?", str(p.get("typical_dwell") or "0"))[0] or 0)
        if prev:
            total_m += _haversine_m(prev.get("coords"), p.get("coords"))
        prev = p
    return {"conflicts": conflicts,
            "estimated_duration": f"{duration:.1f}h",
            "total_distance": f"{total_m / 1000:.1f} km" if total_m else "0 m",
            "checked": len(slots)}
