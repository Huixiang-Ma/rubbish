"""RAG 数据智能闭环存储层：语料反馈 / 引用统计 / 拒答缺口工单（三本账本）。

- feedback：每次问答的 👍/👎（含被引用的语料 job_id 列表），指导语料质量治理；
- citations：语料块 job_id → 被引用次数（ask 自动累计），知识库文档按 kbdoc_{doc_id} 前缀聚合展示；
- gaps：拒答/空命中 query 聚类计数，作为「语料缺口工单」驱动运营补文档。

均为 DATA_ROOT 下 JSON 账本（与商店/知识库同风格），线程安全、重启不丢。
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

from app.services.paths import DATA_ROOT

_FB_FILE = DATA_ROOT / "rag_feedback.json"
_GAPS_FILE = DATA_ROOT / "rag_gaps.json"
_LOCK = threading.Lock()


def _read(path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write(path, obj: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _norm_job_ids(job_ids: list[Any]) -> list[str]:
    return [str(j) for j in (job_ids or []) if j][:8]


def add_feedback(query: str, verdict: str, job_ids: list[Any], user: str | None = None) -> dict[str, Any]:
    """记录一次问答反馈（verdict: up/down），并对被引用语料累计引用计数。"""
    jids = _norm_job_ids(job_ids)
    entry = {"ts": time.strftime("%Y-%m-%d %H:%M"), "query": str(query or "")[:120],
             "verdict": "up" if verdict == "up" else "down", "job_ids": jids, "user": user or ""}
    with _LOCK:
        doc = _read(_FB_FILE, {"feedback": [], "citations": {}})
        doc.setdefault("feedback", []).insert(0, entry)
        doc["feedback"] = doc["feedback"][:500]
        cites = doc.setdefault("citations", {})
        for j in jids:
            cites[j] = int(cites.get(j, 0)) + (2 if entry["verdict"] == "up" else 1)
        _write(_FB_FILE, doc)
    return {"ok": True, "entry": entry}


def record_citations(job_ids: list[Any]) -> None:
    """ask 命中即自动累计引用（无人工反馈也计入，权重 1）。"""
    jids = _norm_job_ids(job_ids)
    if not jids:
        return
    with _LOCK:
        doc = _read(_FB_FILE, {"feedback": [], "citations": {}})
        cites = doc.setdefault("citations", {})
        for j in jids:
            cites[j] = int(cites.get(j, 0)) + 1
        _write(_FB_FILE, doc)


def citation_stats() -> dict[str, int]:
    with _LOCK:
        return dict(_read(_FB_FILE, {"citations": {}}).get("citations", {}))


def add_gap(query: str, distance: float | None = None) -> dict[str, Any]:
    """拒答/空命中聚类计数：同一 query 只留一条工单，count 累加。"""
    key = str(query or "").strip()[:120]
    if not key:
        return {"ok": False}
    with _LOCK:
        doc = _read(_GAPS_FILE, {"gaps": []})
        gaps = doc.setdefault("gaps", [])
        now = time.strftime("%Y-%m-%d %H:%M")
        for g in gaps:
            if g.get("query") == key:
                g["count"] = int(g.get("count", 0)) + 1
                g["last_at"] = now
                if g.get("resolved"):
                    g["resolved"] = False  # 补过的语料又失效/出现新问题：重新打开工单
                    g["resolved_at"] = ""
                if distance is not None:
                    g["distance"] = round(float(distance), 3)
                _write(_GAPS_FILE, doc)
                return {"ok": True, "count": g["count"], "resolved": False}
        entry = {"query": key, "count": 1, "distance": round(float(distance), 3) if distance is not None else None,
                 "first_at": now, "last_at": now}
        gaps.insert(0, entry)
        _write(_GAPS_FILE, doc)
        return {"ok": True, "count": 1}


def resolve_gap(query: str) -> bool:
    """自动关单：同一 query 再次提问且 mode=llm（已命中）→ 标记工单已解决。

    处置状态自动回流，运营无需人工清理已修复的工单；工单保留供追溯。
    """
    key = str(query or "").strip()[:120]
    if not key:
        return False
    closed = False
    with _LOCK:
        doc = _read(_GAPS_FILE, {"gaps": []})
        for g in doc.get("gaps", []):
            if g.get("query") == key and not g.get("resolved"):
                g["resolved"] = True
                g["resolved_at"] = time.strftime("%Y-%m-%d %H:%M")
                closed = True
        if closed:
            _write(_GAPS_FILE, doc)
    return closed


def gaps() -> list[dict[str, Any]]:
    with _LOCK:
        return list(_read(_GAPS_FILE, {"gaps": []}).get("gaps", []))
