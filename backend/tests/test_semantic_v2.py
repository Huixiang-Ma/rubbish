"""WL 侧语义检索回填单测：bm25/query_planner/chunker/semantic（HTTP 全 monkeypatch，内存兜底链）。"""
import pytest

from app.config import get_settings
from app.services import bm25, chunker, query_planner, semantic


def test_bm25_scores_favors_matching_doc():
    records = [
        {"content": "西安大明宫国家遗址公园开放时间08:30"},
        {"content": "杭州西湖景区全年免费开放"},
        {"content": "苏州拙政园始建于明代"},
    ]
    scores = bm25.bm25_scores("大明宫 开放时间", records)
    assert scores[0] > scores[1] and scores[0] > scores[2]


def test_rrf_fuse_merges_two_routes():
    a = [{"content": "三亚大东海旅游区"}, {"content": "丽江古城"}]
    b = [{"content": "丽江古城"}, {"content": "三亚鹿回头"}]
    fused = bm25.rrf_fuse([a, b], top_k=2)
    assert len(fused) == 2
    assert fused[0]["content"] == "丽江古城"  # 两路都上榜 → 得分最高


def test_chunker_paragraph_integrity():
    paras = [f"第{i}段：" + "园林知识" * 10 for i in range(8)]
    chunks = chunker.chunk_text("\n\n".join(paras), size=400, overlap=80)
    joined = "\n".join(chunks)
    for para in paras:
        assert para in joined


def test_decompose_single_intent_passthrough():
    assert query_planner.decompose("拙政园是谁建的") == ["拙政园是谁建的"]


def test_decompose_multi_intent_but_llm_none_returns_original(monkeypatch):
    # 多意图规则命中，但 LLM 失败 → 安全回退原问题
    monkeypatch.setattr(query_planner.LLMClient, "try_generate_json", lambda self, p: None)
    assert query_planner.decompose("三亚和丽江都适合度假吗？") == ["三亚和丽江都适合度假吗？"]


def test_decompose_entity_guard_drops_bad_split(monkeypatch):
    monkeypatch.setattr(
        query_planner.LLMClient, "try_generate_json",
        lambda self, p: {"sub_questions": ["三亚适合度假吗？"]},  # 丽江实体丢失
    )
    assert query_planner.decompose("三亚和丽江都适合度假吗？") == ["三亚和丽江都适合度假吗？"]


def test_semantic_memory_add_and_search(monkeypatch):
    # 内存兜底链：pg_mirror 桩（enabled=False → 走内存），embedding 用 mock
    from app.services.embedding import mock_embed

    class _StubMirror:
        enabled = False

        def add_chunk(self, *a, **k):
            return None

        def search_chunks(self, *a, **k):
            return []

        def all_chunks(self, *a, **k):
            return []

    monkeypatch.setattr(semantic, "_MEMORY", {})
    monkeypatch.setattr(semantic, "pg_mirror", _StubMirror())
    monkeypatch.setattr(
        semantic, "embed_batch",
        lambda texts, settings: [mock_embed(t) for t in texts],
    )
    semantic.add_chunk("doc", "拙政园始建于明正德四年，王献臣所建。", "t-1")
    semantic.add_chunk("doc", "杭州西湖景区全年免费开放。", "t-2")
    out = semantic.search_similar("拙政园是谁建的", k=1, tenant_id="t-1")
    assert out["mode"] == "memory"
    assert out["tenant_id"] == "t-1"
    assert "拙政园" in out["results"][0]["content"]
    # 租户隔离：t-2 桶只有西湖内容，拙政园（t-1 桶的）绝不可能出现在 t-2 结果里
    out2 = semantic.search_similar("拙政园是谁建的", k=1, tenant_id="t-2")
    assert all("拙政园" not in r["content"] for r in out2["results"])


def test_semantic_add_returns_mode_and_tenant(monkeypatch):
    from app.services.embedding import mock_embed

    class _StubMirror:
        enabled = False

        def add_chunk(self, *a, **k):
            return None

    monkeypatch.setattr(semantic, "_MEMORY", {})
    monkeypatch.setattr(semantic, "pg_mirror", _StubMirror())
    monkeypatch.setattr(
        semantic, "embed_batch",
        lambda texts, settings: [mock_embed(t) for t in texts],
    )
    r = semantic.add_chunk("job", "内容", "t-1")
    assert r["tenant_id"] == "t-1"
    assert r["mode"] == "memory"