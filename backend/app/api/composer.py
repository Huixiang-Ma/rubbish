"""标品组装与覆盖率 API：/api/composer/*、/api/plans/{id}/swap-product/*、/api/stats/product-coverage*。

- Composer：RAG 选品（/products、/search）→ 确定性排程（/from-products）→ 拖拽预览（/preview）；
- 标品替换：读取行程块上下文，按 RAG 检索给候选 + 影响评估（时段错配 / 游览时长差 / 点间距），
  实际写回当前为演示级返回（不落 checkpoint，diff 直接回给前端渲染）；
- 覆盖率：素材库在售标品 vs 已入库语料的真实口径统计。
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import catalog_rag, composer_service, coverage_service, material_store
from app.services.checkpoint_store import CheckpointStore
from app.services.paths import job_dir

router = APIRouter(tags=["composer"])
store = CheckpointStore()


# ---------- Composer ----------
class ComposeRequest(BaseModel):
    product_ids: list[str] = Field(default_factory=list)
    days: int = Field(default=2, ge=1, le=7)
    pace: str = "standard"  # relaxed | standard | tight
    budget: int | None = None
    anchor: dict[str, Any] | None = None  # {city: ...}


class PreviewSlot(BaseModel):
    slot: str = ""
    product_id: str = ""


class PreviewRequest(BaseModel):
    slots: list[PreviewSlot] = Field(default_factory=list)


@router.get("/api/composer/products")
def composer_products(category: str = "", city: str = "", q: str = "") -> dict[str, Any]:
    """标品目录：默认全量已上架素材；带 q 时走 RAG 检索选品。"""
    if q.strip():
        res = composer_service.search_products(q.strip(), top_k=24, city=city, category=category)
        products = [r["product"] for r in res["results"]]
        return {"total": len(products), "mode": res["mode"], "categories": _category_keys(),
                "products": products}
    rows = [p for p in composer_service._product_rows() if p.get("listed") is not False]
    if category:
        rows = [p for p in rows if p.get("category") == category]
    if city:
        rows = [p for p in rows if city in str(p.get("city") or "")]
    return {"total": len(rows), "mode": "all", "categories": _category_keys(), "products": rows}


@router.get("/api/composer/search")
def composer_search(q: str, top_k: int = 12, city: str = "", category: str = "") -> dict[str, Any]:
    """RAG 选品检索：自然语言主题 → 语义命中标品（含匹配分与语料摘要）。"""
    if not q.strip():
        raise HTTPException(status_code=422, detail="q 不能为空")
    return composer_service.search_products(q.strip(), top_k=top_k, city=city, category=category)


@router.post("/api/composer/from-products")
def composer_from_products(payload: ComposeRequest) -> dict[str, Any]:
    """确定性排程：选中标品 → 逐日行程（含 RAG 知识背书）+ 预算分项 + 覆盖率。"""
    if not payload.product_ids:
        raise HTTPException(status_code=422, detail="请至少选择一个标品")
    anchor = payload.anchor or {}
    return composer_service.compose(
        payload.product_ids, days=payload.days, pace=payload.pace,
        budget=payload.budget, city=str(anchor.get("city") or ""),
    )


@router.post("/api/composer/preview")
def composer_preview(payload: PreviewRequest) -> dict[str, Any]:
    return composer_service.preview(payload.model_dump())


def _category_keys() -> list[str]:
    return ["景点", "餐饮", "住宿", "交通", "购物", "文化"]


# ---------- 行程中标品替换 ----------
class SwapRequest(BaseModel):
    day: int = Field(..., ge=1)
    slot_index: int = Field(..., ge=0)
    new_product_id: str = Field(..., min_length=1)
    reason: str = ""


def _load_job_state(job_id: str) -> dict[str, Any]:
    try:
        return store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc


def _itinerary_of(job_id: str) -> list[dict[str, Any]]:
    state = _load_job_state(job_id)
    rel = state.get("agent_outputs", {}).get("Itinerary")
    if not rel:
        return []
    try:
        output = json.loads((job_dir(job_id) / rel).read_text(encoding="utf-8"))
        return output.get("payload", {}).get("itinerary") or []
    except (OSError, ValueError, AttributeError):
        return []


def _day_blocks(itin: list[dict[str, Any]], day: int) -> list[dict[str, Any]]:
    """兼容两种行程结构：管线版 {day, items:[{spot,title,...}]} 与组装器版 {day, blocks:[...]}。"""
    d = next((x for x in itin if int(x.get("day", -1)) == day), None)
    if not d:
        return []
    blocks = d.get("blocks")
    if isinstance(blocks, list) and blocks:
        return blocks
    items = d.get("items")
    if isinstance(items, list):
        # 管线版归一化：product_id 以 spot 名对齐素材库，slot 按序号
        norm = []
        for i, it in enumerate(items):
            spot = it.get("spot") or {}
            name = str(spot.get("name") or it.get("title") or "")
            norm.append({
                "slot": str(it.get("slot") or ""), "slot_index": i,
                "start": str(it.get("time") or ""), "title": name,
                "product_name": name, "product_id": None,  # 运行时按名解析
            })
        return norm
    return []


def _resolve_product(block: dict[str, Any]) -> dict[str, Any] | None:
    """块 → 素材库标品：优先 product_id，否则按名精确匹配。"""
    pid = block.get("product_id")
    if pid:
        p = material_store.find_product(str(pid))
        if p:
            return p
    name = str(block.get("product_name") or block.get("title") or "").strip()
    if name:
        exact = [p for p in material_store.product_rows()
                 if str(p.get("name") or "").strip() == name
                 or name in str(p.get("name") or "")]
        if exact:
            return exact[0]
    return None


def _swap_candidate(p: dict[str, Any]) -> dict[str, Any] | None:
    """按替换产品名做 RAG 检索：命中语料即视为知识背书通过。"""
    try:
        res = catalog_rag.ground_terms([str(p.get("name") or "")])
        items = res.get("items") or []
        if items and items[0].get("matched"):
            return {"matched": True, "score": items[0].get("score"), "snippet": items[0].get("snippet")}
    except Exception:
        pass
    return None


def _swap_impact(old_p: dict[str, Any] | None, new_p: dict[str, Any], slot: str) -> dict[str, Any] | None:
    if not old_p:
        return None

    def _dwell(p: dict[str, Any]) -> float:
        m = re.findall(r"\d+(?:\.\d+)?", str(p.get("typical_dwell") or "0"))
        return float(m[0]) if m else 2.0

    old_price = composer_service._ticket_of(old_p)
    new_price = composer_service._ticket_of(new_p)
    dist_m = composer_service._haversine_m(old_p.get("coords"), new_p.get("coords"))
    warnings: list[str] = []
    if new_p.get("best_slot") and slot and new_p.get("best_slot") != slot:
        warnings.append(f"最佳时段不匹配（库内建议 {new_p.get('best_slot')}，当前为 {slot}）")
    return {
        "time_delta": f"{_dwell(new_p) - _dwell(old_p):+.1f}h",
        "cost_delta": new_price - old_price,
        "distance_delta": f"{dist_m:.0f} m" if dist_m else "0 m",
        "warnings": warnings,
        "old": {"id": old_p.get("id"), "name": old_p.get("name")},
        "new": {"id": new_p.get("id"), "name": new_p.get("name")},
    }


@router.post("/api/plans/{job_id}/swap-product/inspect")
def swap_inspect(job_id: str, payload: SwapRequest) -> dict[str, Any]:
    """替换影响预检：不落盘，返回 RAG 背书 + 时长/费用/距离 diff + 警示。"""
    new_p = material_store.find_product(payload.new_product_id)
    if not new_p:
        raise HTTPException(status_code=404, detail=f"标品不存在：{payload.new_product_id}")
    itin = _itinerary_of(job_id)
    blocks = _day_blocks(itin, payload.day)
    old_block = blocks[payload.slot_index] if payload.slot_index < len(blocks) else None
    if not old_block:
        raise HTTPException(status_code=404, detail=f"第 {payload.day} 天第 {payload.slot_index + 1} 时段不存在")
    old_p = _resolve_product(old_block)
    grounding = _swap_candidate(new_p)
    impact = _swap_impact(old_p, new_p, str(old_block.get("slot") or ""))
    candidates: list[dict[str, Any]] = []
    try:
        res = composer_service.search_products(
            f"{new_p.get('city') or ''} {new_p.get('category') or ''}", top_k=6, city=str(new_p.get("city") or ""))
        candidates = [{"id": r["product"]["id"], "name": r["product"]["name"],
                       "category": r["product"]["category"], "matched_by": res["mode"]}
                      for r in res["results"]]
    except Exception:
        pass
    return {"ok": True, "job_id": job_id, "day": payload.day, "slot_index": payload.slot_index,
            "old_title": old_block.get("title"), "grounding": grounding, "diff": impact,
            "candidates": candidates,
            "warnings": (impact or {}).get("warnings", [])}


@router.post("/api/plans/{job_id}/swap-product")
def swap_product(job_id: str, payload: SwapRequest) -> dict[str, Any]:
    """标品替换：RAG 校验 + 影响评估后，将替换写回行程（演示级：返回 diff 供前端渲染）。"""
    new_p = material_store.find_product(payload.new_product_id)
    if not new_p:
        raise HTTPException(status_code=404, detail=f"标品不存在：{payload.new_product_id}")
    itin = _itinerary_of(job_id)
    blocks = _day_blocks(itin, payload.day)
    old_block = blocks[payload.slot_index] if payload.slot_index < len(blocks) else None
    if not old_block:
        raise HTTPException(status_code=404, detail=f"第 {payload.day} 天第 {payload.slot_index + 1} 时段不存在")
    old_p = _resolve_product(old_block)
    grounding = _swap_candidate(new_p)
    impact = _swap_impact(old_p, new_p, str(old_block.get("slot") or ""))
    knowledge = composer_service.enrich_block(new_p)
    log_event_safe("swap_product", job_id=job_id, day=payload.day, slot=payload.slot_index,
                   new_product_id=payload.new_product_id, rag_matched=bool(grounding))
    return {"ok": True, "job_id": job_id, "day": payload.day, "slot_index": payload.slot_index,
            "old_title": old_block.get("title"),
            "old_product_id": (old_p or {}).get("id"), "new_product_id": payload.new_product_id,
            "grounding": grounding, "diff": impact, "knowledge": knowledge,
            "warnings": (impact or {}).get("warnings", []),
            "swap_id": f"swap_{payload.day}_{payload.slot_index}",
            "note": "替换结果以本次返回的 diff 为准（演示级，不落 checkpoint）"}


def log_event_safe(event: str, **kw: Any) -> None:
    try:
        from app.services.jsonlog import log_event
        log_event(event, **kw)
    except Exception:
        pass


# ---------- 标品覆盖率 ----------
@router.get("/api/stats/product-coverage")
def coverage_overview() -> dict[str, Any]:
    return coverage_service.overview()


@router.get("/api/stats/product-coverage/trend")
def coverage_trend(days: int = 14) -> dict[str, Any]:
    return coverage_service.trend(days)


@router.get("/api/stats/product-coverage/missing")
def coverage_missing() -> dict[str, Any]:
    return coverage_service.missing()
