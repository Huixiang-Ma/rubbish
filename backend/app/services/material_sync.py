"""素材/方案数据生产闭环：多来源自动汇入素材库 → 城市素材量达标 → 自动生成方案。

数据来源（三路汇入）：
  1. Researcher 智能体高德/飞猪 POI 检索结果 → sync_pois()
  2. 知识库文档 LLM 抽取结构化候选 → sync_candidates()
  3. 手动 POI 批量拉取（/api/stats/poi-candidates → 前端勾选）→ sync_pois()

自动化策略：
  - 素材：按名称互相包含去重，新条目自动入库（listed=True，挂 cat: 语料）；
  - 方案：城市素材 ≥ 3 条且无在售方案 → 自动 plan_create（listed=False 下架态，toB 审核上架）。
"""
from __future__ import annotations

import json
import time
from typing import Any

from app.services.paths import DATA_ROOT

_SYNC_LOG = DATA_ROOT / "material_sync_log.json"
_LOCK = __import__("threading").Lock()


def _log(entries: list[dict]) -> None:
    try:
        doc = json.loads(_SYNC_LOG.read_text(encoding="utf-8")) if _SYNC_LOG.exists() else {"syncs": []}
        doc["syncs"] = (doc.get("syncs", []) + entries)[-500:]
        tmp = _SYNC_LOG.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(_SYNC_LOG)
    except Exception:
        pass


def _norm_name(name: str) -> str:
    return str(name or "").strip()[:40]


def _find_existing(name: str) -> dict | None:
    from app.services import material_store

    for p in material_store.product_rows():
        pname = str(p.get("name") or "")
        if pname and (pname in name or name in pname):
            return p
    return None


def _city_material_count(city: str) -> int:
    from app.services import material_store

    return sum(1 for p in material_store.product_rows()
               if city.removesuffix("市") in str(p.get("city") or ""))


def _city_has_plan(city: str) -> bool:
    from app.services import shop_store

    for p in shop_store.plans_seed():
        if p.get("listed") is not False and city.removesuffix("市") in str(p.get("city") or ""):
            return True
    for p in shop_store.plan_manage_list({"page": 1, "page_size": 200}).get("items", []):
        if p.get("listed") is not False and city.removesuffix("市") in str(p.get("city") or ""):
            return True
    return False


def sync_pois(pois: list[dict[str, Any]], city: str, source: str = "agent") -> dict[str, Any]:
    """把 POI 列表同步到素材库（自动去重、入库、挂语料），返回同步结果。

    pois 每条至少含 name；可选 lat/lng/ticket_price/visit_minutes/open_time/tags/rating/description。
    source: 来源标签（agent / kb_doc / poi_pull），写入素材 tags 便于追溯。
    城市素材 ≥3 条且无在售方案时，自动生成一个方案草稿（下架态）。
    """
    from app.services import material_store

    city_clean = city.removesuffix("市")
    created, skipped, entries = [], [], []
    for poi in pois:
        name = _norm_name(poi.get("name") or "")
        if not name:
            continue
        if _find_existing(name):
            skipped.append({"name": name, "reason": "已存在"})
            continue
        price = int(poi.get("ticket_price") or poi.get("price_min") or 0)
        tags = [str(t) for t in (poi.get("tags") or [])[:3] if t]
        tags.append(source)
        payload = {
            "name": name, "category": poi.get("category") or "景点",
            "city": city_clean or str(poi.get("city") or "苏州"),
            "price_min": price, "price_max": int(poi.get("price_max") or price),
            "stock": 20, "typical_dwell": poi.get("dwell") or poi.get("typical_dwell") or "2h",
            "rating": float(poi.get("rating") or 4.5),
            "description": str(poi.get("description") or poi.get("note") or f"{name}（{city_clean}）"),
            "tags": tags[:6], "listed": True,
        }
        if poi.get("lat") is not None and poi.get("lng") is not None:
            payload["x"] = poi["lng"]
            payload["y"] = poi["lat"]
        product = material_store.create_product(payload)
        created.append({"id": product["id"], "name": name})
        entries.append({"action": "create_material", "name": name, "source": source, "ts": time.strftime("%H:%M:%S")})

    # 城市素材量达标 → 自动生成方案草稿
    plan_created = None
    if created or _city_material_count(city_clean) >= 3:
        if not _city_has_plan(city_clean):
            plan_created = _auto_plan(city_clean, source)
            entries.append({"action": "auto_plan", "city": city_clean, "plan_id": plan_created, "ts": time.strftime("%H:%M:%S")})

    if entries:
        _log(entries)
    return {"created": len(created), "skipped": len(skipped), "materials": created, "plan_id": plan_created}


def sync_candidates(candidates: list[dict[str, Any]], city: str, doc_title: str = "") -> dict[str, Any]:
    """知识库文档 LLM 抽取的结构化候选 → 素材库（适配 sync_pois 接口）。"""
    pois = []
    for c in (candidates or []):
        if not c.get("name"):
            continue
        pois.append({
            "name": c["name"], "city": c.get("city") or city,
            "ticket_price": c.get("ticket_price") or 0,
            "description": c.get("description") or "",
            "tags": ["知识库抽取", doc_title[:12]] if doc_title else ["知识库抽取"],
        })
    return sync_pois(pois, city, source="kb_doc")


def _auto_plan(city: str, source: str) -> str | None:
    """城市素材 ≥3 条时自动生成方案（下架态，toB 审核上架）。"""
    from app.services import shop_store

    count = _city_material_count(city)
    if count < 3:
        return None
    days = min(3, max(2, count // 4))
    per = max(199, min(9999, days * 580))
    plan = shop_store.plan_create({
        "title": f"{city}{days}日 · 自动生成线路", "city": city, "category": "自动生成",
        "days": days, "per_price": per, "original_per_price": round(per * 1.15),
        "min_persons": 2, "stock": 20, "listed": False,
        "subtitle": f"基于素材库 {count} 条自动编排，待审核上架（来源：{source}）",
        "badges": ["自动生成", source],
    })
    return plan.get("id")
