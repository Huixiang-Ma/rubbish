"""D 档 · 标品素材库存储：标品素材/POI 目录 = 种子（products_seed.json，mock 契约 1:1）
+ 素材库覆盖层（DATA_ROOT/shop_products_overlay.json：新建/编辑/上下架/删除）。

与方案馆的关系：新建方案的动线由本目录同城已上架素材自动挂载（product_ids 引用此目录 id）。
无 Postgres 用 JSON 落库（与 shop_store 同模式，线程锁 + 原子替换）。
"""
from __future__ import annotations

import copy
import datetime
import json
import os
import random
import threading
from pathlib import Path
from typing import Any

from app.services.paths import DATA_ROOT

_SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "products_seed.json"
_OVERLAY_FILE = DATA_ROOT / "shop_products_overlay.json"
_LOCK = threading.Lock()
_base_cache: list[dict[str, Any]] | None = None

_CAT_EMOJI = {"景点": "📍", "文化": "🏛", "餐饮": "🍜", "住宿": "🏨", "购物": "🛍", "交通": "🚄"}
_CAT_GRAD = {
    "景点": "linear-gradient(135deg,#43e97b 0%,#38f9d7 100%)",
    "文化": "linear-gradient(135deg,#a18cd1 0%,#fbc2eb 100%)",
    "餐饮": "linear-gradient(135deg,#f6d365 0%,#fda085 100%)",
    "住宿": "linear-gradient(135deg,#667eea 0%,#764ba2 100%)",
    "购物": "linear-gradient(135deg,#fccb90 0%,#d57eeb 100%)",
    "交通": "linear-gradient(135deg,#13547a 0%,#80d0c7 100%)",
}
_DEFAULT_GRAD = "linear-gradient(135deg,#f6d365 0%,#fda085 100%)"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _atomic_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _gen_product_id() -> str:
    stamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
    tail = format(random.randrange(4096), "03x")
    return f"pp_{stamp}{tail}"


def _cat_grad(category: str) -> str:
    return _CAT_GRAD.get(category) or _DEFAULT_GRAD


def _prices_of(skus: list[dict[str, Any]]) -> tuple[int, int]:
    prices = [int(s.get("price") or 0) for s in skus or []]
    prices = [x for x in prices if x > 0]
    if not prices:
        return 0, 0
    return min(prices), max(prices)


def _default_cover(category: str, name: str) -> dict[str, Any]:
    return {"emoji": _CAT_EMOJI.get(category, "📍"), "gradient": _cat_grad(category), "caption": name}


def _base_rows() -> list[dict[str, Any]]:
    global _base_cache
    if _base_cache is None:
        doc = _read_json(_SEED_FILE, {"products": []})
        _base_cache = doc.get("products", []) if isinstance(doc, dict) else []
    return _base_cache


def _overlay() -> dict[str, Any]:
    return _read_json(_OVERLAY_FILE, {"overrides": {}, "deleted": []})


def product_rows() -> list[dict[str, Any]]:
    """素材库事实源：种子 + 覆盖层（编辑替换、删除软删）。"""
    ov = _overlay()
    overrides = ov.get("overrides") or {}
    deleted = set(ov.get("deleted") or [])
    base = _base_rows()
    base_by_id = {p.get("id"): p for p in base if p.get("id")}
    rows: list[dict[str, Any]] = []
    for pid in list(base_by_id) + [i for i in overrides if i not in base_by_id]:
        if pid in deleted:
            continue
        src = overrides.get(pid) or base_by_id.get(pid)
        if not src:
            continue
        p = dict(src)
        p.setdefault("listed", True)
        rows.append(p)
    return rows


def find_product(product_id: str) -> dict[str, Any] | None:
    return next((p for p in product_rows() if p.get("id") == product_id), None)


def _store_row(row: dict[str, Any]) -> None:
    with _LOCK:
        ov = _overlay()
        ov.setdefault("overrides", {})[row["id"]] = row
        _atomic_write(_OVERLAY_FILE, ov)


def _norm_row(base_row: dict[str, Any] | None, payload: dict[str, Any], pid: str) -> dict[str, Any]:
    """把前台产物补全为契约可渲染行：缺失字段从原型/分类默认补齐。"""
    proto = base_row or (find_product(str(payload.get("category") or "")) or {})
    category = str(payload.get("category") or proto.get("category") or "景点")
    name = str(payload.get("name") or proto.get("name") or "新素材")
    skus = list(payload.get("skus") or [])
    for i, s in enumerate(skus):
        if not isinstance(s, dict):
            continue
        s.setdefault("label", str(s.get("label") or "标准票"))
        s.setdefault("spec", str(s.get("spec") or ""))
        s.setdefault("price", _to_int(s.get("price"), 0))
        s.setdefault("original_price", _to_int(s.get("original_price"), s.get("price")))
        s.setdefault("stock", _to_int(s.get("stock"), 0))
        s.setdefault("limit_per_user", _to_int(s.get("limit_per_user"), 10))
        s.setdefault("sku_id", f"{pid}_sku{i + 1}")
    price_min, price_max = _prices_of(skus)
    cover = payload.get("cover") or proto.get("cover") or {}
    if not isinstance(cover, dict) or not cover.get("emoji"):
        cover = _default_cover(category, name)
    refund_key = payload.get("refund_policy") if payload.get("refund_policy") else payload.get("refund")
    row = dict(proto)
    row.update({k: v for k, v in payload.items() if v is not None and k != "refund"})
    row["id"] = pid
    row["name"] = name
    row["category"] = category
    row["cover"] = cover
    row["skus"] = skus
    row["price_min"] = price_min if price_min else _to_int(row.get("price_min"), 0)
    row["price_max"] = price_max if price_max else _to_int(row.get("price_max"), 0)
    if refund_key is not None:
        row["refund_policy"] = str(refund_key)
    row.setdefault("city", str(payload.get("city") or proto.get("city") or "苏州"))
    row.setdefault("level", str(payload.get("level") or proto.get("level") or "-"))
    row.setdefault("open", str(payload.get("open") or proto.get("open") or "全天"))
    row.setdefault("typical_dwell", str(payload.get("typical_dwell") or proto.get("typical_dwell") or "2h"))
    row.setdefault("best_slot", str(payload.get("best_slot") or proto.get("best_slot") or "morning"))
    row.setdefault("description", str(payload.get("description") or proto.get("description") or name))
    row.setdefault("tags", list(payload.get("tags") or proto.get("tags") or []))
    row.setdefault("badges", list(payload.get("badges") or proto.get("badges") or []))
    row.setdefault("sales", _to_int(payload.get("sales"), _to_int(proto.get("sales"), 0)))
    row.setdefault("source", "manual")
    row.setdefault("listed", bool(payload.get("listed", True)))
    row["updated_at"] = _now_iso()
    return row


def create_product(payload: dict[str, Any]) -> dict[str, Any]:
    pid = _gen_product_id()
    row = _norm_row(None, payload, pid)
    row.setdefault("created_at", _now_iso())
    _store_row(row)
    return row


def update_product(product_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    cur = find_product(product_id)
    if not cur:
        raise LookupError("素材不存在")
    row = _norm_row(cur, {**cur, **{k: v for k, v in patch.items() if v is not None}}, product_id)
    _store_row(row)
    return row


def set_product_status(product_id: str, listed: bool) -> dict[str, Any]:
    cur = find_product(product_id)
    if not cur:
        raise LookupError("素材不存在")
    cur = dict(cur)
    cur["listed"] = bool(listed)
    cur["updated_at"] = _now_iso()
    _store_row(cur)
    return {"listed": bool(listed)}


def delete_product(product_id: str) -> None:
    if not find_product(product_id):
        raise LookupError("素材不存在")
    with _LOCK:
        ov = _overlay()
        ov.setdefault("deleted", [])
        if product_id not in ov["deleted"]:
            ov["deleted"].append(product_id)
        ov.get("overrides", {}).pop(product_id, None)
        _atomic_write(_OVERLAY_FILE, ov)


def manage_products(params: dict[str, Any]) -> dict[str, Any]:
    rows = [copy.deepcopy(p) for p in product_rows()]
    kw = params.get("keyword")
    if kw:
        k = str(kw).casefold()
        rows = [p for p in rows if any(k in str(p.get(f) or "").casefold()
                for f in ("name", "category", "city", "description"))]
    if params.get("category"):
        rows = [p for p in rows if p.get("category") == params["category"]]
    total = len(rows)
    page = max(1, _to_int(params.get("page"), 1))
    page_size = min(1000, max(1, _to_int(params.get("page_size"), 300)))
    start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size,
            "has_more": start + len(rows) < total, "items": rows[start:start + page_size]}


def public_list(params: dict[str, Any]) -> dict[str, Any]:
    rows = [p for p in product_rows() if p.get("listed") is not False]
    if params.get("category"):
        rows = [p for p in rows if p.get("category") == params["category"]]
    kw = params.get("keyword")
    if kw:
        k = str(kw).casefold()
        rows = [p for p in rows if k in str(p.get("name") or "").casefold() or k in str(p.get("city") or "").casefold()]
    total = len(rows)
    page_size = min(100, max(1, _to_int(params.get("page_size"), 24)))
    page = max(1, _to_int(params.get("page"), 1))
    start = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size,
            "has_more": start + len(rows) < total, "items": rows[start:start + page_size]}


def public_detail(product_id: str) -> dict[str, Any]:
    p = find_product(product_id)
    if not p or p.get("listed") is False:
        raise LookupError("素材不存在或已下架")
    return p


def product_categories() -> dict[str, Any]:
    rows = product_rows()
    by: dict[str, int] = {}
    for p in rows:
        c = str(p.get("category") or "其他")
        by[c] = by.get(c, 0) + 1
    return {"items": [{"name": k, "count": v} for k, v in by.items()], "total": len(rows)}
