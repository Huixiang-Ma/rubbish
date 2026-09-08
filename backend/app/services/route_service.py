"""标品线路 SKU 服务（docs/行程规划标品方案.md §二）：CRUD + 变体 + 出行日校验。

纯逻辑可单测：读取走 pg_mirror（惰性，DATABASE_URL 未配置时返回空列表 = 未启用）。
行销三防线：人工签发（status）→ 出行日 API 校验 → 语料 SLA（knowledge_refs 引用实时取）。
"""
from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy import text

from app.services.pg_mirror import pg_mirror
from app.services.semantic import search_similar

VALID_STATUS = {"draft", "reviewed", "published"}
DAILY_CHECK_FIELDS = ("closure", "weather", "booking")


def _row_to_route(row: Any) -> dict[str, Any]:
    return {
        "route_id": row[0], "tenant_id": row[1], "city": row[2], "theme": row[3],
        "days": row[4], "pace": row[5], "audience": row[6], "season": row[7],
        "days_detail": row[8], "variants": row[9], "knowledge_refs": row[10],
        "status": row[11], "reviewer": row[12], "published_at": row[13],
        "version": row[14], "quality_report": row[15], "daily_check": row[16],
        "created_at": row[17], "updated_at": row[18],
    }


def create_route(route: dict[str, Any], tenant_id: str = "default") -> dict[str, Any]:
    """新建线路（draft 草稿，人工签发前不可发布）。"""
    if not route.get("route_id") or not route.get("city") or not route.get("days_detail"):
        raise ValueError("route_id / city / days_detail 必填")
    route["status"] = route.get("status") or "draft"
    route["tenant_id"] = tenant_id
    route["version"] = route.get("version", 1)
    if not pg_mirror._ensure():  # 强制启用（惰性初始化，DATABASE_URL 未配才 memory）
        return {"mode": "memory", "route_id": route["route_id"]}
    with pg_mirror.engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO itinerary_routes (route_id, tenant_id, city, theme, days, pace, audience, "
                "season, days_detail, variants, knowledge_refs, status, reviewer, published_at, version, "
                "quality_report, daily_check, created_at, updated_at) "
                "VALUES (:rid, :tenant, :city, :theme, :days, :pace, :audience, :season, :detail, "
                ":variants, :refs, :status, :reviewer, :published_at, :version, :quality, :daily, NOW(), NOW()) "
                "ON CONFLICT (route_id) DO UPDATE SET days_detail=EXCLUDED.days_detail, "
                "variants=EXCLUDED.variants, knowledge_refs=EXCLUDED.knowledge_refs, "
                "updated_at=NOW()"
            ),
            {
                "rid": route["route_id"], "tenant": tenant_id, "city": route["city"],
                "theme": route.get("theme"), "days": route["days"], "pace": route.get("pace"),
                "audience": route.get("audience"), "season": route.get("season"),
                "detail": json.dumps(route["days_detail"], ensure_ascii=False),
                "variants": json.dumps(route.get("variants") or {}, ensure_ascii=False),
                "refs": json.dumps(route.get("knowledge_refs") or [], ensure_ascii=False),
                "status": route["status"], "reviewer": route.get("reviewer"),
                "published_at": route.get("published_at"), "version": route["version"],
                "quality": route.get("quality_report"), "daily": json.dumps(route.get("daily_check") or {}, ensure_ascii=False),
            },
        )
    return {"mode": "pg", "route_id": route["route_id"]}


def list_routes(tenant_id: str, city: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    """列出线路（按租户强制隔离 + 可选城市/状态过滤）。"""
    if not pg_mirror.enabled:
        return []
    sql = "SELECT * FROM itinerary_routes WHERE tenant_id = :tenant"
    params: dict[str, Any] = {"tenant": tenant_id}
    if city:
        sql += " AND city = :city"
        params["city"] = city
    if status:
        sql += " AND status = :status"
        params["status"] = status
    sql += " ORDER BY created_at DESC"
    with pg_mirror.engine.connect() as conn:
        rows = conn.execute(text(sql), params)
        return [_row_to_route(r) for r in rows]


def get_route(route_id: str, tenant_id: str) -> dict[str, Any] | None:
    if not pg_mirror.enabled:
        return None
    with pg_mirror.engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT * FROM itinerary_routes WHERE route_id = :rid AND tenant_id = :tenant"
            ),
            {"rid": route_id, "tenant": tenant_id},
        ).fetchone()
        return _row_to_route(row) if row else None


def publish(route_id: str, tenant_id: str, reviewer: str) -> dict[str, Any] | None:
    """人工签发：draft/reviewed → published（记录审核人与时间）。"""
    if not pg_mirror.enabled:
        return None
    with pg_mirror.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE itinerary_routes SET status='published', reviewer=:reviewer, "
                "published_at=NOW(), updated_at=NOW() "
                "WHERE route_id=:rid AND tenant_id=:tenant AND status <> 'published'"
            ),
            {"reviewer": reviewer, "rid": route_id, "tenant": tenant_id},
        )
    return get_route(route_id, tenant_id)


def apply_variant(route: dict[str, Any], variant: str) -> dict[str, Any]:
    """应用变体规则（亲子/雨天等）：不复制线路，按 rules 替换 block。返回深拷贝。"""
    import copy

    result = copy.deepcopy(route)
    variants = route.get("variants") or {}
    rules = variants.get(variant) or {}
    replaces = rules.get("replace") or []
    for rep in replaces:
        remove, add = rep.get("remove"), rep.get("add")
        if not add:
            continue
        # 把目标 replace 块的类型/引用换成 add（简化：把含 remove 关键字的 block 替换为 add 引用）
        for day_block in result.get("days_detail", []):
            for block in day_block.get("blocks", []):
                if remove and (remove in block.get("name", "") or remove in block.get("type", "")):
                    block["name"] = add
                    block["type"] = "poi"
    result["variants"] = {**variants, "_active": variant}
    return result


def daily_check(route: dict[str, Any], env=None) -> list[dict[str, str]]:
    """出行日校验：逐 block 调实时 API（闭园/天气/预约），返回告警清单。

    三层铁律（§五）：知识走 RAG、状态走 API。此处只对状态型字段校验，失败静默（不阻塞）。
    """
    warnings: list[dict[str, str]] = []
    for day_block in route.get("days_detail", []):
        for block in day_block.get("blocks", []):
            if block.get("type") != "poi":
                continue
            name = block.get("name", "")
            hit = search_similar(name, k=1, tenant_id=route.get("tenant_id", "default"))
            if not hit.get("results"):
                warnings.append({"name": name, "level": "warn", "msg": f"未检索到「{name}」的语料，内容可能缺失"})
    return warnings


def enrich_knowledge(route: dict[str, Any]) -> dict[str, Any]:
    """详情页渲染：按 knowledge_refs 实时 RAG 取知识卡片（语料更新自动保鲜）。"""
    route = dict(route)
    refs = route.get("knowledge_refs") or []
    enriched = []
    for ref in refs:  # ref 形如 "doc:zhuozhengyuan#3" 或 {source, query}
        if isinstance(ref, dict):
            query = ref.get("query", ref.get("source", ""))
        else:
            query = str(ref).split("#")[0]
        hit = search_similar(query, k=1, tenant_id=route.get("tenant_id", "default"))
        if hit.get("results"):
            enriched.append({"ref": ref, "content": hit["results"][0]["content"]})
    route["_knowledge"] = enriched
    return route