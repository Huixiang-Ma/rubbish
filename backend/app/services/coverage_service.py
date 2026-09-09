"""标品覆盖率分析（toB RAG Lab 看板数据源）。

口径：覆盖率 = 已入库语料标品数 / 素材库在售标品数，按分类聚合；
趋势 = 近 N 天标品语料摄入量与检索命中（演示级：以当前快照回放形态给出，
无历史埋点时不编造——如实标注 snapshot）。top_missing = 在售但暂无语料的标品清单。
"""
from __future__ import annotations

import datetime
from typing import Any

from app.services import material_store
from app.services.catalog_rag import _JOB_PREFIX, ensure_corpus
from app.services.semantic import all_chunks


def _corpus_ids() -> set[str]:
    ensure_corpus()
    rows = all_chunks(None)
    return {str(r.get("job_id", "")).removeprefix(_JOB_PREFIX)
            for r in rows if str(r.get("job_id", "")).startswith(_JOB_PREFIX)}


def overview() -> dict[str, Any]:
    """覆盖率总览：总/命中/缺失 + 分分类命中率 + top_missing（真实口径，无随机数）。"""
    rows = [p for p in material_store.product_rows() if p.get("listed") is not False]
    have = _corpus_ids()
    hit_rows = [p for p in rows if p.get("id") in have]
    miss_rows = [p for p in rows if p.get("id") not in have]

    cats: dict[str, list[dict[str, Any]]] = {}
    for p in rows:
        cats.setdefault(str(p.get("category") or "其他"), []).append(p)
    coverage_by_category = {c: round(len([p for p in ps if p.get("id") in have]) / len(ps), 2)
                            for c, ps in sorted(cats.items())}

    total = len(rows)
    hit = len(hit_rows)
    return {
        "total_plans": total,
        "rag_hit_plans": hit,
        "rag_miss_plans": total - hit,
        "hit_rate": round(hit / total, 2) if total else 0.0,
        # 拒答/空命中为运行态指标（rag ask 日志口径）；此处给结构性口径，不编造
        "refusal_rate": 0.0,
        "empty_rate": 0.0,
        "avg_distance": 0.0,
        "coverage_by_category": coverage_by_category,
        "top_missing": [{"name": p.get("name"), "product_id": p.get("id"),
                         "category": p.get("category"), "city": p.get("city"), "count": 1}
                        for p in miss_rows],
        "snapshot_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def trend(days: int = 14) -> dict[str, Any]:
    """摄入趋势：近 N 天按日统计语料块累计（真实摄入计数，缺数日如实为 0 增量）。"""
    days = max(7, min(60, days))
    rows = all_chunks(None)
    have = [r for r in rows if str(r.get("job_id", "")).startswith(_JOB_PREFIX)]
    # 语料行无逐日时间戳：以"当前累计 + 单日陡增"的诚实口径呈现（不随机造曲线）
    today = datetime.date.today()
    trend_rows = []
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        trend_rows.append({
            "date": d.isoformat()[5:10],
            "hit_rate": (len(have) / max(1, len(_corpus_ids()))) if i == 0 else 0.0,
            "refusal_rate": 0.0,
            "empty_rate": 0.0,
            "corpus_count": len(have) if i == 0 else 0,
        })
    return {"trend": trend_rows, "corpus_total": len(have),
            "note": "无历史埋点：曲线仅末日快照为真实累计值，其余为 0，不做虚构回放"}


def missing() -> dict[str, Any]:
    ov = overview()
    return {"total": len(ov["top_missing"]), "items": ov["top_missing"]}
