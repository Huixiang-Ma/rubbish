"""工单 7 · 共享图记忆引擎：实体三元组抽取、upsert 幂等与冲突 superseded。

存储双模：
- 配置 DATABASE_URL 时写 PG（memory_entities / memory_triples，复用 pg_mirror 引擎）；
- 未配置时进程内存兜底（dict），演示口径不受影响，接口完全一致。

抽取双模：
- LLM real：try_generate_json 结构化抽取（schema 强校验，失败返回 None）；
- mock 兜底：关键词/正则规则（过敏、不吃、预算、带老人等），离线可跑。
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from typing import Any

from app.services.llm_client import LLMClient
from app.services.pg_mirror import pg_mirror

_DDL = [
    """
    CREATE TABLE IF NOT EXISTS memory_entities (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        etype TEXT NOT NULL DEFAULT 'concept',
        tenant TEXT,
        job_id TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (name, etype, tenant)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_triples (
        id BIGSERIAL PRIMARY KEY,
        head_id BIGINT NOT NULL REFERENCES memory_entities(id) ON DELETE CASCADE,
        relation TEXT NOT NULL,
        tail_id BIGINT NOT NULL REFERENCES memory_entities(id) ON DELETE CASCADE,
        thread_id TEXT,
        job_id TEXT,
        source_round INTEGER,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_triples_head ON memory_triples(head_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_triples_thread ON memory_triples(thread_id, status)",
]

# 内存兜底：{tenant: {entity_key: id}} / {id: entity} / triples 列表
_mem_lock = threading.Lock()
_mem_entities: dict[str, dict[int, dict[str, Any]]] = {}
_mem_entity_seq = 0
_mem_triples: list[dict[str, Any]] = []
_triple_seq = 0

# mock 抽取规则：(正则, relation, 实体类型)
_MOCK_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"(?:对|严重)?(海鲜|芒果|花生|酒精|花粉)[过敏忌]"), "HAS_ALLERGY", "allergen"),
    (re.compile(r"不吃?(辣|香菜|羊肉|生冷)"), "DISLIKES", "food_taboo"),
    (re.compile(r"(?:带|有)(?:老人|孕妇|婴儿|小孩|娃)"), "TRAVELS_WITH", "companion"),
    (re.compile(r"避免?早起|不想早起|睡到自然醒"), "PREFERS_AVOID", "constraint"),
    (re.compile(r"预算[不超过上限在]*\s*(\d{3,6})\s*元?"), "BUDGET_CAP", "budget"),
    (re.compile(r"(?:喜欢|偏爱|想)(历史|美食|博物馆|亲子|摄影|自然风光|购物|夜游)"), "PREFERS", "preference"),
]

_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "triples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "head": {"type": "string"},
                    "relation": {"type": "string"},
                    "tail": {"type": "string"},
                    "tail_type": {"type": "string"},
                },
                "required": ["head", "relation", "tail"],
            },
        }
    },
    "required": ["triples"],
}
_ALLOWED_RELATIONS = {
    "HAS_ALLERGY", "DISLIKES", "TRAVELS_WITH", "PREFERS", "PREFERS_AVOID",
    "BUDGET_CAP", "VISITS", "CONSTRAINT_ON", "AVOIDS",
}


class MemoryEngine:
    """三元组抽取与图记忆读写（PG 优先，内存兜底）。"""

    def __init__(self) -> None:
        self.llm = LLMClient()

    # ---------- 抽取 ----------

    def extract(self, text: str, thread_id: str, job_id: str | None = None,
                tenant: str | None = None, source_round: int | None = None) -> list[dict[str, Any]]:
        """从一段对话/输入抽取三元组并落库，返回写入的三元组列表。"""
        triples = self._llm_extract(text) or self._mock_extract(text)
        written = []
        for t in triples:
            head = (t.get("head") or "").strip()[:40] or "user"
            relation = (t.get("relation") or "").strip().upper()
            tail = (t.get("tail") or "").strip()[:60]
            tail_type = (t.get("tail_type") or "concept").strip()
            if not relation or not tail:
                continue
            if relation not in _ALLOWED_RELATIONS:
                relation = "CONSTRAINT_ON"
            hid = self._ensure_entity(head, "user", tenant, job_id)
            tid = self._ensure_entity(tail, tail_type, tenant, job_id)
            row = self._upsert_triple(hid, relation, tid, thread_id, job_id, source_round)
            if row:
                written.append(row)
        return written

    def _llm_extract(self, text: str) -> list[dict[str, Any]] | None:
        if self.llm.mode != "real" or not self.llm.api_key:
            return None
        prompt = (
            "从旅行对话中抽取实体约束三元组。relation 限定：HAS_ALLERGY/DISLIKES/TRAVELS_WITH/"
            "PREFERS/PREFERS_AVOID/BUDGET_CAP/VISITS/CONSTRAINT_ON/AVOIDS。"
            '输出 JSON：{"triples": [{"head": "user", "relation": "HAS_ALLERGY", "tail": "海鲜", "tail_type": "allergen"}]}。'
            "只抽取明确表达的约束，不要推测。\n对话：" + text[:800]
        )
        result = self.llm.try_generate_json(prompt, schema=_EXTRACTION_SCHEMA)
        triples = result.get("triples") if isinstance(result, dict) else None
        if not isinstance(triples, list):
            return None
        return [t for t in triples if isinstance(t, dict) and t.get("relation") and t.get("tail")]

    @staticmethod
    def _mock_extract(text: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for pattern, relation, etype in _MOCK_RULES:
            m = pattern.search(text)
            if not m:
                continue
            if relation == "BUDGET_CAP":
                out.append({"head": "user", "relation": relation, "tail": m.group(1), "tail_type": etype})
            else:
                out.append({"head": "user", "relation": relation, "tail": m.group(1), "tail_type": etype})
        return out

    # ---------- 实体与边 ----------

    def _ensure_entity(self, name: str, etype: str, tenant: str | None, job_id: str | None) -> int:
        global _mem_entity_seq
        if pg_mirror.enabled:
            with pg_mirror.engine.begin() as conn:
                row = conn.execute(
                    __import__("sqlalchemy").text(
                        "INSERT INTO memory_entities (name, etype, tenant, job_id) "
                        "VALUES (:n, :t, :tn, :j) "
                        "ON CONFLICT (name, etype, tenant) DO UPDATE SET job_id = EXCLUDED.job_id "
                        "RETURNING id"
                    ),
                    {"n": name, "t": etype, "tn": tenant, "j": job_id},
                )
                return row.scalar_one()
        with _mem_lock:
            store = _mem_entities.setdefault(tenant or "", {})
            key = (name, etype)
            for eid, ent in store.items():
                if (ent["name"], ent["etype"]) == key:
                    return eid
            _mem_entity_seq += 1
            store[_mem_entity_seq] = {"id": _mem_entity_seq, "name": name, "etype": etype}
            return _mem_entity_seq

    def _upsert_triple(self, head_id: int, relation: str, tail_id: int,
                       thread_id: str, job_id: str | None, source_round: int | None) -> dict[str, Any] | None:
        """同 (head, relation, tail, thread) 幂等；同 head+relation 出现新 tail 时旧边 superseded。"""
        global _triple_seq
        if pg_mirror.enabled:
            import sqlalchemy

            with pg_mirror.engine.begin() as conn:
                exists = conn.execute(
                    sqlalchemy.text(
                        "SELECT id FROM memory_triples WHERE head_id=:h AND relation=:r AND tail_id=:t "
                        "AND COALESCE(thread_id,'')=COALESCE(:th,'') AND status='active'"
                    ),
                    {"h": head_id, "r": relation, "t": tail_id, "th": thread_id},
                ).first()
                if exists:
                    return None
                conn.execute(
                    sqlalchemy.text(
                        "UPDATE memory_triples SET status='superseded' "
                        "WHERE head_id=:h AND relation=:r AND status='active' AND tail_id<>:t"
                    ),
                    {"h": head_id, "r": relation, "t": tail_id},
                )
                row = conn.execute(
                    sqlalchemy.text(
                        "INSERT INTO memory_triples (head_id, relation, tail_id, thread_id, job_id, source_round) "
                        "VALUES (:h, :r, :t, :th, :j, :sr) RETURNING id"
                    ),
                    {"h": head_id, "r": relation, "t": tail_id, "th": thread_id, "j": job_id, "sr": source_round},
                )
                return {"id": row.scalar_one(), "head_id": head_id, "relation": relation, "tail_id": tail_id}
        with _mem_lock:
            for t in _mem_triples:
                if t["head_id"] == head_id and t["relation"] == relation and t["tail_id"] == tail_id \
                        and t["thread_id"] == thread_id and t["status"] == "active":
                    return None
            for t in _mem_triples:
                if t["head_id"] == head_id and t["relation"] == relation and t["status"] == "active" and t["tail_id"] != tail_id:
                    t["status"] = "superseded"
            _triple_seq += 1
            row = {"id": _triple_seq, "head_id": head_id, "relation": relation,
                   "tail_id": tail_id, "thread_id": thread_id, "job_id": job_id,
                   "source_round": source_round, "status": "active"}
            _mem_triples.append(row)
            return row

    # ---------- 读取 ----------

    def thread_triples(self, thread_id: str) -> list[dict[str, Any]]:
        """某会话全部 active 三元组（head/relation/tail 已解析为名称）。"""
        if pg_mirror.enabled:
            import sqlalchemy

            with pg_mirror.engine.connect() as conn:
                rows = conn.execute(
                    sqlalchemy.text(
                        "SELECT he.name AS head, t.relation, te.name AS tail, te.etype AS tail_type "
                        "FROM memory_triples t "
                        "JOIN memory_entities he ON he.id=t.head_id "
                        "JOIN memory_entities te ON te.id=t.tail_id "
                        "WHERE t.thread_id=:th AND t.status='active' ORDER BY t.id"
                    ),
                    {"th": thread_id},
                ).mappings().all()
                return [dict(r) for r in rows]
        with _mem_lock:
            ents = {e["id"]: e for store in _mem_entities.values() for e in store.values()}
            return [
                {"head": ents[t["head_id"]]["name"], "relation": t["relation"],
                 "tail": ents[t["tail_id"]]["name"], "tail_type": ents[t["tail_id"]]["etype"]}
                for t in _mem_triples if t["thread_id"] == thread_id and t["status"] == "active"
            ]

    def count_active(self, thread_id: str) -> int:
        return sum(1 for t in self.thread_triples(thread_id))

    def recall(self, thread_id: str, query: str = "", limit: int = 8) -> list[dict[str, Any]]:
        """多层级检索第一层：thread 内全部 active 三元组，禁忌/约束优先。
        query 命中（tail/head/类型包含）的排到最前——供决策前精准召回。"""
        weight = {"HAS_ALLERGY": 0, "DISLIKES": 1, "PREFERS_AVOID": 2, "AVOIDS": 2,
                  "BUDGET_CAP": 3, "CONSTRAINT_ON": 4, "TRAVELS_WITH": 5, "PREFERS": 6}
        rows = self.thread_triples(thread_id)
        if query:
            q = query.lower()
            hits = [r for r in rows if q in (r["tail"] + r["head"] + r["tail_type"]).lower()]
            rest = [r for r in rows if r not in hits]
            rows = hits + rest
        rows.sort(key=lambda r: weight.get(r["relation"], 9))
        return rows[:limit]


def new_thread_id() -> str:
    return f"thread_{uuid.uuid4().hex[:12]}"


def triple_count() -> int:
    if pg_mirror.enabled:
        import sqlalchemy

        with pg_mirror.engine.connect() as conn:
            return conn.execute(sqlalchemy.text("SELECT count(*) FROM memory_triples WHERE status='active'")).scalar_one()
    with _mem_lock:
        return sum(1 for t in _mem_triples if t["status"] == "active")
