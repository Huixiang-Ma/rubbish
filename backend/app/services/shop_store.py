"""C/D 档 · 商城/方案馆商业域存储：在售方案目录（种子+上架覆盖层）+ 订单 + 收藏。

- 目录事实源：backend/app/data/shop_seed.json（mock 契约 1:1 导出）
  + DATA_ROOT/shop_plans_overlay.json（方案馆上架覆盖层：新建/编辑/上下架/删除）。
- 事务：订单/收藏落 DATA_ROOT（无 Postgres 也可文件持久化；多写用线程锁 + 原子替换）。
- 库存口径：'成团余位' 按该方案"已支付且在履约中"的订单数实算，上架时设置的 stock 为基准。
- 用户隔离：匿名 owner='guest'；登录（traveler）只读写自己的订单/收藏；staff 角色可看全量。
诚实口径：未做支付网关，支付=模拟成功回执（与演示层级一致，页面明示）。
"""
from __future__ import annotations

import datetime
import json
import os
import random
import string
import threading
from pathlib import Path
from typing import Any

from app.services.paths import DATA_ROOT
from app.services import auth_service  # noqa: F401  (转接验证时避免循环 import)

_SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "shop_seed.json"
_PLAN_OVERLAY_FILE = DATA_ROOT / "shop_plans_overlay.json"
_ORDERS_FILE = DATA_ROOT / "shop_orders.json"
_FAVS_FILE = DATA_ROOT / "shop_favs.json"

STAFF_ROLES = {"admin", "supervisor", "consultant"}
ORDER_STATUS_ORDER = ["UNPAID", "PAID", "USED", "CANCELLED", "REFUNDED"]
ACTIVE_STATUSES = ("PAID", "USED")
_LOCK = threading.Lock()
_tax_cache: list[dict[str, Any]] | None = None


# ---------------- 基础存取 ----------------
def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _day_ago(days: int) -> str:
    return (datetime.date.today() - datetime.timedelta(days=days)).isoformat() + "T10:00:00"


def _fmt_day(offset: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=offset)).isoformat()


def _voucher() -> str:
    alphabet = string.ascii_uppercase + string.digits
    grp = lambda: "".join(random.choices(alphabet, k=4))  # noqa: E731
    return f"VC{grp()}-{grp()}"


def _order_no() -> str:
    now = datetime.datetime.now()
    tail = "".join(random.choices(string.digits, k=4))
    return f"TR{now:%Y%m%d%H%M%S}{tail}"


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


# ---------------- 目录（种子 + D 档方案馆覆盖层） ----------------
def _seed_doc() -> dict[str, Any]:
    global _tax_cache
    data = _read_json(_SEED_FILE, {"plans": [], "tax": []})
    if isinstance(data, dict):
        _tax_cache = data.get("tax", []) or []
        return data
    return {"plans": [], "tax": []}


def _plan_overlay() -> dict[str, Any]:
    return _read_json(_PLAN_OVERLAY_FILE, {"overrides": {}, "deleted": []})


def _plans_merged_all() -> list[dict[str, Any]]:
    """游客目录与方案馆管理共用一个事实源：种子 + 工作台覆盖层（合并/替换/软删）。"""
    doc = _seed_doc()
    ov = _plan_overlay()
    overrides = ov.get("overrides") or {}
    deleted = set(ov.get("deleted") or [])
    base = doc.get("plans", []) or []
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
        # 兼容『含它的方案』检索：种子未显式带 product_ids 时从动线回填
        if not p.get("product_ids") and isinstance(p.get("itinerary"), list):
            ids = []
            for day in p["itinerary"]:
                for blk in day.get("blocks") or []:
                    pid2 = (blk.get("product") or {}).get("id")
                    if pid2 and pid2 not in ids:
                        ids.append(pid2)
            p["product_ids"] = ids
        rows.append(p)
    return rows


def plans_seed() -> list[dict[str, Any]]:
    """公共在售目录：合并后处于上架（listed）状态的方案。"""
    return [p for p in _plans_merged_all() if p.get("listed") is not False]


def plans_all() -> list[dict[str, Any]]:
    """方案馆全量（含下架/草稿，不含已删除）：管理后台事实源。"""
    return _plans_merged_all()


def tax_rows() -> list[dict[str, Any]]:
    _seed_doc()
    return list(_tax_cache or [])


_PACE_ZH = {"leisure": "悠闲节奏", "standard": "适中节奏", "compact": "紧凑节奏"}
_GRADS = [
    "linear-gradient(135deg,#f6d365 0%,#fda085 100%)",
    "linear-gradient(135deg,#84fab0 0%,#8fd3f4 100%)",
    "linear-gradient(135deg,#a18cd1 0%,#fbc2eb 100%)",
    "linear-gradient(135deg,#fccb90 0%,#d57eeb 100%)",
]


def find_plan_any(plan_id: str) -> dict[str, Any] | None:
    """管理视角：找任意方案（含下架），不含已删除。"""
    return next((p for p in plans_all() if p.get("id") == plan_id), None)


def _write_plan_overlay(plan: dict[str, Any]) -> None:
    with _LOCK:
        ov = _plan_overlay()
        ov.setdefault("overrides", {})[plan["id"]] = plan
        _atomic_write(_PLAN_OVERLAY_FILE, ov)


def _pool_products(city: str) -> list[dict[str, Any]]:
    """新建方案自动挂载素材：优先同城已上架标品，无则退回全量（保证动线非空）。"""
    try:
        from app.services.material_store import product_rows
        rows = [p for p in product_rows() if p.get("listed") is not False]
    except Exception:
        rows = []
    exact = [p for p in rows if str(p.get("city") or "") == city]
    return exact or rows


def _prod_ref(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": p.get("id"), "name": p.get("name"), "category": p.get("category"),
        "city": p.get("city"), "badges": p.get("badges") or [], "tags": p.get("tags") or [],
        "price_min": _to_int(p.get("price_min"), 0), "level": p.get("level") or "-",
        "coords": p.get("coords"), "cover": p.get("cover"),
    }


def _gen_plan_id() -> str:
    stamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
    tail = format(random.randrange(4096), "03x")
    return f"tpl_{stamp}{tail}"


def _build_plan_itinerary(city: str, days: int, pool: list[dict[str, Any]]) -> dict[str, Any]:
    refs = [_prod_ref(p) for p in pool]
    n = len(refs)
    per = max(1, (n + days - 1) // max(1, days)) if n else 0
    if per > 4:
        per = 4
    blocks_all: list[dict[str, Any]] = []
    product_ids: list[str] = []
    day_titles: list[str] = []
    cursor = 0
    times = {"morning": "08:30", "midday": "11:30", "afternoon": "14:30", "evening": "17:30"}
    slot_keys = ["morning", "midday", "afternoon", "evening"]
    for d in range(days):
        pick = min(per, n - cursor) if (d < days - 1 or n == cursor) else max(1, min(per, n - cursor))
        chunk = refs[cursor:cursor + pick]
        cursor += len(chunk)
        if cursor >= n and d < days - 1:
            cursor = 0  # 素材耗尽则循环复用，保证多日行程不断档
        day_blocks: list[dict[str, Any]] = []
        for idx, prod in enumerate(chunk):
            period = slot_keys[min(idx, 3)]
            tag = ""
            if prod.get("category") == "餐饮" and period == "midday":
                tag = "午餐"
            elif d == 0 and idx == 0:
                tag = "去程"
            if prod.get("id") and prod["id"] not in product_ids:
                product_ids.append(prod["id"])
            day_blocks.append({
                "key": f"b{d + 1}_{idx + 1}", "period": period, "start": times[period],
                "tag": tag, "product": prod,
            })
        blocks_all.append({"day": d + 1, "title": f"Day{d + 1}", "blocks": day_blocks})
        titles = [b.get("product", {}).get("name", "") for b in day_blocks]
        day_titles.append(f"第{d + 1}天 · {city}{' · '.join([''] + titles[:2])}".rstrip("· ")[:30])
    return {"itinerary": blocks_all, "product_ids": product_ids, "day_titles": day_titles}


def plan_create(payload: dict[str, Any]) -> dict[str, Any]:
    days = max(1, min(7, _to_int(payload.get("days"), 2)))
    per = max(0, _to_int(payload.get("per_price"), 0))
    orig = max(per, _to_int(payload.get("original_per_price"), per))
    city = str(payload.get("city") or "苏州")
    category = str(payload.get("category") or "自由行")
    cover = payload.get("cover") or {}
    emoji = str(cover.get("emoji") or "📍")
    gradient = cover.get("gradient") or _GRADS[len(city) % len(_GRADS)]
    tags = [str(x) for x in (payload.get("tags") or []) if x]
    if not tags:
        tags = [f"{category}", f"{city} · {days}日"]
    pool = _pool_products(city)
    itin = _build_plan_itinerary(city, days, pool)
    badge_default = [f"{days}日游", "成团保障"]
    plan_id = _gen_plan_id()
    plan = {
        "id": plan_id, "kind": "plan", "title": str(payload.get("title") or f"{city}{category}{days}日游"),
        "category": category, "city": city, "city_tag": f"{city} · {days}日",
        "days": days, "theme": f"{category} · {city}",
        "pace": str(payload.get("pace") or "standard"),
        "pace_zh": _PACE_ZH.get(str(payload.get("pace") or "standard"), "适中节奏"),
        "audience": "家庭 / 朋友", "season": "四季", "cover": {"emoji": emoji, "gradient": gradient},
        "product_ids": itin["product_ids"], "day_titles": itin["day_titles"],
        "subtitle": str(payload.get("subtitle") or f"{days} 日把 {city} 的{category}安排明白，精华点一个不落"),
        "tags": tags,
        "badges": [str(x) for x in (payload.get("badges") or badge_default)][:3],
        "per_price": per, "original_per_price": orig, "original_total": per,
        "min_persons": max(1, _to_int(payload.get("min_persons"), 2)),
        "stock": max(0, _to_int(payload.get("stock"), 20)), "sales": 0, "rating": 4.7,
        "review_count": 0, "poi_count": len(itin["product_ids"]),
        "intro": str(payload.get("intro") or f"{days} 日 {city}{category}私享团：本地司导、轻车简从、随走随停。"),
        "include": ["全程车辆与司导服务", f"{days} 日核心景点门票", "可选包餐（下单备注）"],
        "exclude": ["个人消费", "往返大交通", "单房差"],
        "pickup": f"{city}市区酒店/高铁站集合（下单后客服确认）",
        "refund_policy": "出行前 48 小时外可免费取消，48 小时内按 30% 扣费",
        "available_from": "可订未来 90 天团期",
        "itinerary": itin["itinerary"],
        "listed": bool(payload.get("listed", True)), "source": "manual",
        "created_at": _now_iso(), "updated_at": _now_iso(),
    }
    _write_plan_overlay(plan)
    # 数据智能闭环：新方案自动生成 plan: 语料入检索层（RAG 问答可推荐在售方案）
    try:
        from app.services import semantic

        text = (
            f"在售线路方案：{plan.get('title')}。{plan.get('subtitle') or ''}"
            f"{city}{days} 日游，人均 {per} 元（原价 {orig}），{plan.get('pace_zh') or ''}，"
            f"余位 {plan.get('stock')}，评分 {plan.get('rating')}。"
            f"亮点：{('、'.join(plan.get('badges') or [])[:2]) or category}。"
            f"每日安排：{('；'.join(str(t) for t in plan.get('day_titles') or []))[:120]}。"
        )
        semantic.add_chunk(f"plan:{plan.get('id')}", text, "default")
    except Exception:
        pass  # 语义层不可用不阻断方案上架
    return plan


def plan_update(plan_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    cur = find_plan_any(plan_id)
    if not cur:
        raise LookupError("行程方案不存在")
    merged = {k: v for k, v in dict(cur).items() if k not in ("id", "kind", "created_at", "source")}
    for k, v in patch.items():
        if v is None or k in ("id", "created_at"):
            continue
        merged[k] = v
    if "days" in patch:
        merged["days"] = max(1, min(7, _to_int(patch.get("days"), 2)))
    if "pace" in patch:
        merged["pace_zh"] = _PACE_ZH.get(str(patch.get("pace")), "适中节奏")
    merged["per_price"] = _to_int(merged.get("per_price"), 0)
    merged["original_per_price"] = max(merged["per_price"], _to_int(merged.get("original_per_price"), merged["per_price"]))
    merged["stock"] = max(0, _to_int(merged.get("stock"), 0))
    merged["updated_at"] = _now_iso()
    merged["id"] = plan_id
    _write_plan_overlay(merged)
    return merged


def plan_set_listed(plan_id: str, listed: bool) -> dict[str, Any]:
    cur = find_plan_any(plan_id)
    if not cur:
        raise LookupError("行程方案不存在")
    cur = dict(cur)
    cur["listed"] = bool(listed)
    cur["updated_at"] = _now_iso()
    _write_plan_overlay(cur)
    return cur


def plan_remove(plan_id: str) -> None:
    if not find_plan_any(plan_id):
        raise LookupError("行程方案不存在")
    with _LOCK:
        ov = _plan_overlay()
        ov.setdefault("deleted", [])
        if plan_id not in ov["deleted"]:
            ov["deleted"].append(plan_id)
        ov.get("overrides", {}).pop(plan_id, None)
        _atomic_write(_PLAN_OVERLAY_FILE, ov)


def plan_manage_list(params: dict[str, Any]) -> dict[str, Any]:
    """方案馆管理列表：全量（含下架/自建），每行带实算余位。"""
    rows = [dict(p) for p in plans_all()]
    kw = params.get("keyword")
    if kw:
        k = str(kw).casefold()
        rows = [p for p in rows if any(k in str(p.get(f) or "").casefold()
                for f in ("title", "city", "category", "theme", "subtitle"))]
    total = len(rows)
    page = max(1, _to_int(params.get("page"), 1))
    page_size = min(200, max(1, _to_int(params.get("page_size"), 60)))
    start = (page - 1) * page_size
    rows = rows[start:start + page_size]
    for p in rows:
        p["stock"] = _plan_remaining(p)
    return {"total": total, "page": page, "page_size": page_size,
            "has_more": start + len(rows) < total, "items": rows}


def find_plan(plan_id: str) -> dict[str, Any] | None:
    return next((p for p in plans_seed() if p.get("id") == plan_id and p.get("listed") is not False), None)


def plan_summary(p: dict[str, Any], extra: dict | None = None) -> dict[str, Any]:
    out = {
        "id": p.get("id"), "kind": p.get("kind") or "plan", "name": p.get("title"),
        "category": p.get("category"), "city": p.get("city"), "city_tag": p.get("city_tag"),
        "days": p.get("days"), "theme": p.get("theme"), "pace": p.get("pace"),
        "pace_zh": p.get("pace_zh"), "cover": p.get("cover"), "badges": p.get("badges") or [],
        "tags": p.get("tags") or [], "per_price": p.get("per_price"),
        "original_per_price": p.get("original_per_price"), "min_persons": p.get("min_persons"),
        "stock": _plan_remaining(p), "poi_count": p.get("poi_count"), "rating": p.get("rating"),
        "review_count": p.get("review_count"), "sales": p.get("sales"),
        "subtitle": p.get("subtitle"), "listed": p.get("listed"), "source": p.get("source"),
    }
    if extra:
        out.update(extra)
    return out


def _active_reservations(plan_id: str) -> int:
    """已支付/在履约（未退款未取消）的成团位占用数：每订单占 1 位。"""
    rows = _read_json(_ORDERS_FILE, [])
    return sum(
        1 for o in rows
        if o.get("status") in ACTIVE_STATUSES
        and any(it.get("kind") == "plan" and it.get("product_id") == plan_id for it in o.get("items") or [])
    )


def _plan_remaining(p: dict[str, Any]) -> int:
    base = int(p.get("stock") or 0)
    return max(0, base - _active_reservations(p.get("id") or ""))


def plan_skus(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """方案可选种类（套餐规格）：默认全包整订 + 按方案特征派生的可选 SKU。

    - 含住宿的方案：基础（不含酒店）/ 含酒店 两档；
    - 全部方案：双人成团价（默认）、单房差补、儿童价（不占床）。
    价格口径以 per_price 为基准增减，演示级；后续 SKU 可由 toB 上架表单自定义。
    """
    days = int(plan.get("days") or 1)
    per = int(plan.get("per_price") or 0)
    orig = int(plan.get("original_per_price") or per)
    skus = [{
        "sku_id": f"{plan['id']}_full", "label": "标准整订",
        "spec": f"{days} 日 · 全包", "price": per, "original_price": orig,
        "note": "门票 + 餐饮推荐 + 全程导览",
        "default": True,
    }]
    has_hotel = any(
        (b.get("product") or {}).get("category") == "住宿"
        for d in (plan.get("itinerary") or []) for b in (d.get("blocks") or [])
    )
    if has_hotel:
        skus.append({
            "sku_id": f"{plan['id']}_nohotel", "label": "纯玩不含宿",
            "spec": f"{days} 日 · 不含住宿", "price": max(99, per - days * 260),
            "original_price": max(99, orig - days * 260),
            "note": "自行安排住宿，其余同标准",
        })
        skus.append({
            "sku_id": f"{plan['id']}_single", "label": "单房差",
            "spec": f"{days} 日 · 独立房间", "price": per + days * 220,
            "original_price": orig + days * 220,
            "note": "1 人一间，免拼房",
        })
    skus.append({
        "sku_id": f"{plan['id']}_child", "label": "儿童价",
        "spec": f"{days} 日 · 不占床", "price": max(59, int(per * 0.6)),
        "original_price": max(59, int(orig * 0.6)),
        "note": "1.2m 以下儿童，不占床不含早",
    })
    return skus


def plan_item_of(plan_id: str, persons: int, sku_id: str = "") -> dict[str, Any] | None:
    """方案 → 订单条目（整体预订，以人计）。sku_id 空时取默认种类。"""
    p = find_plan(plan_id)
    if not p:
        return None
    days = int(p.get("days") or 1)
    per = int(p.get("per_price") or 0)
    orig = int(p.get("original_per_price") or per)
    sku = next((s for s in plan_skus(p) if s["sku_id"] == sku_id), None) or {}
    unit = int(sku.get("price") or per)
    unit_orig = int(sku.get("original_price") or orig)
    label = sku.get("label") or f"{days} 日行程 · 整订"
    spec = sku.get("spec") or f"{days} 日 · 人均 ¥{per}"
    return {
        "kind": "plan", "product_id": p["id"], "name": p.get("title"),
        "category": p.get("category"), "city": p.get("city"), "cover": p.get("cover"),
        "days": days, "plan_days": days, "title": p.get("title"),
        "sku_id": sku.get("sku_id") or f"{p['id']}_full", "sku_label": label,
        "spec": spec, "unit_price": unit, "original_price": unit_orig,
        "qty": persons, "travelers": persons,
        "pickup": p.get("pickup") or "行程起点集合（下单后客服确认具体点位）",
        "refund": p.get("refund_policy") or "出行前 48 小时外可免费取消，48 小时内按 30% 扣费",
    }


def catalog_categories() -> dict[str, Any]:
    pubs = [p for p in plans_seed() if p.get("listed") is not False]
    themes = []
    for t in tax_rows():
        themes.append({**t, "count": sum(1 for p in pubs if p.get("category") == t.get("name"))})
    city_map: dict[str, int] = {}
    for p in pubs:
        c = p.get("city") or ""
        city_map[c] = city_map.get(c, 0) + 1
    return {"themes": themes, "cities": [{"name": k, "count": v} for k, v in city_map.items()], "total": len(pubs)}


def catalog_list(params: dict[str, Any]) -> dict[str, Any]:
    """列表：过滤/排序/分页语义与 mock planShopMock.list(admin 除外) 对齐。"""
    pubs = [p for p in plans_seed() if p.get("listed") is not False]
    if params.get("category"):
        pubs = [p for p in pubs if p.get("category") == params["category"]]
    if params.get("city"):
        c = params["city"]
        pubs = [p for p in pubs if c in (p.get("city") or "")]
    if params.get("days"):
        pubs = [p for p in pubs if p.get("days") == _to_int(params.get("days"))]
    if params.get("pace"):
        pubs = [p for p in pubs if p.get("pace") == params["pace"]]
    kw = params.get("keyword")
    if kw:
        k = kw.casefold()
        pubs = [p for p in pubs if any(k in str(p.get(f) or "").casefold() for f in ("title", "city", "theme", "category", "subtitle"))]
    sort = params.get("sort") or "default"
    key_map = {
        "price_asc": lambda p: p.get("per_price") or 0,
        "price_desc": lambda p: -(p.get("per_price") or 0),
        "rating": lambda p: -(p.get("rating") or 0),
        "sales": lambda p: -(p.get("sales") or 0),
        "days": lambda p: p.get("days") or 0,
        "default": lambda p: -((p.get("sales") or 0) * (p.get("rating") or 0)),
    }
    pubs = sorted(pubs, key=key_map.get(sort, key_map["default"]))
    page = max(1, _to_int(params.get("page"), 1))
    page_size = min(60, max(1, _to_int(params.get("page_size"), 12)))
    start = (page - 1) * page_size
    rows = pubs[start:start + page_size]
    return {
        "total": len(pubs), "page": page, "page_size": page_size,
        "has_more": start + len(rows) < len(pubs),
        "items": [plan_summary(p) for p in rows],
    }


def catalog_detail(plan_id: str) -> dict[str, Any]:
    p = find_plan(plan_id)
    if not p:
        raise LookupError("行程方案不存在或已下架")
    pubs = [x for x in plans_seed() if x.get("listed") is not False and x.get("id") != plan_id]
    related = [plan_summary(x) for x in pubs if x.get("category") == p.get("category") or x.get("city") == p.get("city")][:3]
    detail = {**p, "stock": _plan_remaining(p), "skus": plan_skus(p)}
    return {"plan": detail, "related": related}


def catalog_featured(limit: int = 8) -> list[dict[str, Any]]:
    pubs = sorted(plans_seed(), key=lambda p: -((p.get("sales") or 0) * (p.get("rating") or 0)))[:limit]
    return [plan_summary(p) for p in pubs]


def catalog_top(limit: int = 10) -> list[dict[str, Any]]:
    pubs = sorted(plans_seed(), key=lambda p: -(p.get("sales") or 0))[:limit]
    return [{"rank": i + 1, **plan_summary(p)} for i, p in enumerate(pubs)]


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ---------------- 订单 ----------------
def orders_all() -> list[dict[str, Any]]:
    return _read_json(_ORDERS_FILE, [])


def _ensure_seed_orders() -> None:
    """guest 空账本时种 6 单演示数据（与 mock 种子口径一致，首访可见）。"""
    with _LOCK:
        rows = orders_all()
        if rows:
            return
        seeds = [
            ("rt_suzhou_2d", 2, "UNPAID", 0), ("rt_beijing_3d", 3, "PAID", 1),
            ("rt_suzhou_1d", 2, "PAID", 2), ("rt_beijing_culture", 2, "USED", 4),
            ("rt_suzhou_2d", 2, "USED", 7), ("rt_suzhou_1d", 4, "CANCELLED", 9),
        ]
        for plan_id, persons, status, days_ago in seeds:
            item = plan_item_of(plan_id, persons)
            if not item:
                continue
            total = item["unit_price"] * item["qty"]
            order = _new_order(
                owner="guest", items=[item], contact={"name": "苏小姐", "phone": "138****0421"},
                status=status, total=total,
                use_date=_fmt_day(1 if status in ("UNPAID", "PAID") else 0),
                created_at=_day_ago(days_ago), pay_method="" if status == "UNPAID" else "微信支付",
            )
            if status in ("PAID", "USED"):
                order["vouchers"] = [_voucher()]
                order["paid_at"] = _day_ago(days_ago)
            if status == "USED":
                order["used_at"] = _fmt_day(0) + "T12:30:00"
            if status == "CANCELLED":
                order["cancelled_at"] = _day_ago(days_ago - 1)
            rows.append(order)
        _atomic_write(_ORDERS_FILE, rows)


def _new_order(owner: str, items: list[dict], contact: dict, status: str,
               total: float, use_date: str, created_at: str, pay_method: str = "") -> dict[str, Any]:
    subtotal = sum(int(it.get("unit_price") or 0) * int(it.get("qty") or 1) for it in items)
    return {
        "id": "o_" + datetime.datetime.now().strftime("%y%m%d%H%M%S") + format(random.randrange(4096), "03x"),
        "order_no": _order_no(), "status": status, "items": items,
        "subtotal": subtotal, "discount": 0, "total": int(total or subtotal),
        "contact": contact, "travelers": [{"name": contact.get("name") or ""}],
        "use_date": use_date, "start_date": use_date, "use_slot": "",
        "vouchers": [], "pay_method": pay_method, "remark": "", "source": "mall",
        "owner": owner, "created_at": created_at,
        "paid_at": None, "used_at": None, "cancelled_at": None, "refunded_at": None, "refund_amount": 0,
    }


def _order_api(o: dict[str, Any]) -> dict[str, Any]:
    """契约兼容输出：mock 以 total/subtotal/vouchers 为准；另带前端历史用别名。"""
    out = dict(o)
    out["amount"] = o.get("total")
    out["voucher_no"] = (o.get("vouchers") or [None])[0]
    out["start_date"] = o.get("use_date")
    return out


def _is_staff(payload: dict[str, Any] | None) -> bool:
    return bool(payload and payload.get("r") in STAFF_ROLES)


def _scope_orders(payload: dict[str, Any] | None) -> str:
    return payload.get("u") if payload and payload.get("u") else "guest"


def create_order(payload: dict[str, Any], caller: dict[str, Any] | None) -> dict[str, Any]:
    _ensure_seed_orders()
    product_id = str(payload.get("product_id") or "").strip()
    plan = find_plan(product_id)
    if not plan:
        raise LookupError("行程方案不存在或已下架")
    persons = _to_int(payload.get("persons") or payload.get("qty"), 1)
    if persons < _to_int(plan.get("min_persons"), 2):
        raise ValueError(f"该方案至少 {plan.get('min_persons') or 2} 人成行")
    if _plan_remaining(plan) <= 0:
        raise ValueError("该方案余位不足，可换个出发日期")
    use_date = str(payload.get("use_date") or payload.get("start_date") or "").strip()
    if not use_date:
        raise ValueError("请选择出发日期")
    item = plan_item_of(product_id, persons, str(payload.get("sku_id") or ""))
    if not item:
        raise LookupError("行程方案不存在或已下架")
    contact = payload.get("contact") or {}
    owner = _scope_orders(caller)
    order = _new_order(
        owner=owner, items=[item],
        contact={"name": str(contact.get("name") or "未填写"), "phone": str(contact.get("phone") or "")},
        status="UNPAID", total=int(item["unit_price"]) * int(item["qty"] or persons), use_date=use_date,
        created_at=_now_iso(),
    )
    with _LOCK:
        rows = orders_all()
        rows.insert(0, order)
        _atomic_write(_ORDERS_FILE, rows)
    return _order_api(order)


def _find_order(order_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    rows = orders_all()
    o = next((x for x in rows if x.get("id") == order_id), None)
    if not o:
        raise LookupError("订单不存在")
    if not _is_staff(caller) and o.get("owner") != _scope_orders(caller):
        raise LookupError("订单不存在")
    return o


def _save_order(o: dict[str, Any]) -> None:
    with _LOCK:
        rows = orders_all()
        for i, x in enumerate(rows):
            if x.get("id") == o.get("id"):
                rows[i] = o
                break
        _atomic_write(_ORDERS_FILE, rows)


def order_detail(order_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    return _order_api(_find_order(order_id, caller))


def list_orders(params: dict[str, Any], caller: dict[str, Any] | None) -> dict[str, Any]:
    _ensure_seed_orders()
    rows = orders_all()
    if not _is_staff(caller):
        rows = [o for o in rows if o.get("owner") == _scope_orders(caller)]
    status = params.get("status")
    if status and status != "all":
        rows = [o for o in rows if o.get("status") == status]
    kw = params.get("keyword")
    if kw:
        k = str(kw).casefold()
        rows = [o for o in rows if
                k in str(o.get("order_no") or "").casefold()
                or k in str((o.get("contact") or {}).get("name") or "").casefold()
                or any(k in str(it.get("name") or "").casefold() for it in o.get("items") or [])]
    rows.sort(key=lambda o: str(o.get("created_at") or ""), reverse=True)
    items = []
    for o in rows:
        a = _order_api(o)
        items.append({k: a.get(k) for k in (
            "id", "order_no", "status", "items", "total", "amount", "subtotal", "discount",
            "contact", "pay_method", "use_date", "created_at", "vouchers", "voucher_no", "source")})
    return {"total": len(items), "items": items}


def order_pay(order_id: str, method: str, use_date: str | None, caller: dict[str, Any] | None) -> dict[str, Any]:
    o = _find_order(order_id, caller)
    if o.get("status") != "UNPAID":
        return _order_api(o)
    o.update(status="PAID", vouchers=[_voucher() for _ in o.get("items") or []],
             pay_method=method or "微信支付", paid_at=_now_iso())
    if use_date:
        o["use_date"] = use_date
        o["start_date"] = use_date
    _save_order(o)
    return _order_api(o)


def order_cancel(order_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    o = _find_order(order_id, caller)
    if o.get("status") != "UNPAID":
        raise ValueError("仅待支付订单可取消")
    o.update(status="CANCELLED", cancelled_at=_now_iso())
    _save_order(o)
    return _order_api(o)


def order_complete(order_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    o = _find_order(order_id, caller)
    if o.get("status") != "PAID":
        raise ValueError("仅已支付订单可核销")
    o.update(status="USED", used_at=_now_iso())
    _save_order(o)
    return _order_api(o)


def order_refund(order_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    o = _find_order(order_id, caller)
    if o.get("status") not in ("PAID", "USED"):
        raise ValueError("当前状态不可退款")
    o.update(status="REFUNDED", refunded_at=_now_iso(), refund_amount=o.get("total") or 0)
    _save_order(o)
    return _order_api(o)


def order_stats(caller: dict[str, Any] | None) -> dict[str, Any]:
    _ensure_seed_orders()
    rows = orders_all()
    if not _is_staff(caller):
        rows = [o for o in rows if o.get("owner") == _scope_orders(caller)]
    by = {s: 0 for s in ORDER_STATUS_ORDER}
    gmv = 0
    for o in rows:
        by[o.get("status")] = by.get(o.get("status"), 0) + 1
        if o.get("status") in ACTIVE_STATUSES:
            gmv += int(o.get("total") or 0)
    days = []
    for i in range(6, -1, -1):
        key = _fmt_day(-i)
        paid = [o for o in rows if o.get("status") in ACTIVE_STATUSES
                and str(o.get("paid_at") or o.get("created_at") or "").startswith(key)]
        days.append({"date": key[5:], "count": len(paid),
                     "gmv": sum(int(o.get("total") or 0) for o in paid)})
    return {
        "by_status": by, "total_orders": len(rows), "gmv": int(gmv),
        "avg": int(gmv / max(1, by.get("PAID", 0) + by.get("USED", 0))) if rows else 0,
        "days": days,
        "today_new": sum(1 for o in rows if str(o.get("created_at") or "").startswith(_fmt_day(0))),
    }


# ---------------- 收藏 ----------------
def _favs() -> dict[str, list[str]]:
    return _read_json(_FAVS_FILE, {})


def _owner_fav_ids(owner: str) -> list[str]:
    favs = _favs()
    if owner in favs:
        return list(favs[owner])
    # guest 首访种 3 个默认收藏（在售方案前 3），与 mock 首访种子对齐
    if owner == "guest":
        ids = [p.get("id") for p in plans_seed()[:3] if p.get("id")]
        with _LOCK:
            favs = _favs()
            favs["guest"] = ids
            _atomic_write(_FAVS_FILE, favs)
        return list(ids)
    return []


def _write_fav(owner: str, ids: list[str]) -> None:
    with _LOCK:
        favs = _favs()
        favs[owner] = ids
        _atomic_write(_FAVS_FILE, favs)


def fav_list(caller: dict[str, Any] | None) -> dict[str, Any]:
    owner = _scope_orders(caller)
    items = []
    for pid in _owner_fav_ids(owner):
        p = find_plan(pid)
        if p:
            items.append(plan_summary(p))
    return {"total": len(items), "items": items}


def fav_add(product_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    owner = _scope_orders(caller)
    ids = _owner_fav_ids(owner)
    if product_id not in ids:
        ids.insert(0, product_id)
        _write_fav(owner, ids)
    return {"ok": True, "liked": True, "count": len(ids)}


def fav_remove(product_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    owner = _scope_orders(caller)
    ids = [i for i in _owner_fav_ids(owner) if i != product_id]
    _write_fav(owner, ids)
    return {"ok": True, "liked": False, "count": len(ids)}


def fav_toggle(product_id: str, caller: dict[str, Any] | None) -> dict[str, Any]:
    owner = _scope_orders(caller)
    ids = _owner_fav_ids(owner)
    liked = product_id not in ids
    ids = [i for i in ids if i != product_id]
    if liked:
        ids.insert(0, product_id)
    _write_fav(owner, ids)
    return {"ok": True, "liked": liked, "count": len(ids)}
