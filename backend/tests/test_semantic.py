"""语义检索与 Embedding 客户端单元测试（不依赖真实 PG / Ollama）。"""
import pytest

from app.services import embedding as embedding_module
from app.services import semantic


class _StubMirror:
    """内存兜底桩：模拟未配置 DATABASE_URL 的 pg_mirror。"""

    enabled = False

    def add_chunk(self, job_id, content, emb):
        return None

    def search_chunks(self, emb, k):
        return []


@pytest.fixture()
def mock_mode(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    client = embedding_module.EmbeddingClient()
    monkeypatch.setattr(semantic, "embedding_client", client)
    monkeypatch.setattr(semantic, "pg_mirror", _StubMirror())
    semantic._memory_chunks.clear()
    return client


def test_mock_embed_deterministic_and_normalized():
    a = embedding_module.mock_embed("故宫门票")
    b = embedding_module.mock_embed("故宫门票")
    assert a == b
    assert len(a) == embedding_module.MOCK_DIM
    assert abs(sum(v * v for v in a) - 1.0) < 1e-5


def test_memory_roundtrip(mock_mode):
    semantic.add_chunk("job-1", "拙政园门票80元")
    out = semantic.search_similar("拙政园门票")
    assert out["mode"] == "memory"
    assert out["embedder"] == "mock"
    assert out["results"][0]["content"] == "拙政园门票80元"


def test_ollama_embed_calls_api(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("EMBEDDING_DIM", "4")
    calls = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"embeddings": [[0.1, 0.2, 0.3, 0.4]]}

    def fake_post(url, json=None, timeout=None):
        calls["url"], calls["payload"], calls["timeout"] = url, json, timeout
        return _Resp()

    monkeypatch.setattr(embedding_module.httpx, "post", fake_post)
    vec = embedding_module.EmbeddingClient().embed("紫禁城")
    assert vec == [0.1, 0.2, 0.3, 0.4]
    assert calls["url"].endswith("/api/embed")
    assert calls["payload"]["model"].endswith("bge-m3:567m")


def test_ollama_dim_mismatch_raises(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("EMBEDDING_DIM", "4")

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"embeddings": [[0.1, 0.2, 0.3]]}

    monkeypatch.setattr(embedding_module.httpx, "post", lambda *a, **k: _Resp())
    with pytest.raises(RuntimeError, match="维度不符"):
        embedding_module.EmbeddingClient().embed("紫禁城")


def test_ollama_unreachable_raises(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("EMBEDDING_TIMEOUT_SECONDS", "0.2")

    def fake_post(*a, **k):
        raise ConnectionError("refused")

    monkeypatch.setattr(embedding_module.httpx, "post", fake_post)
    with pytest.raises(RuntimeError, match="ollama"):
        embedding_module.EmbeddingClient().embed("紫禁城")


def test_active_dim_follows_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    assert embedding_module.active_dim(embedding_module.Settings()) == embedding_module.MOCK_DIM
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("EMBEDDING_DIM", "1024")
    assert embedding_module.active_dim(embedding_module.Settings()) == 1024
