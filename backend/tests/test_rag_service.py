"""RAG 问答服务单测（检索桩 + LLM 桩，不联网、不依赖 pg）。"""
import pytest

from app.services import rag_service
from app.services.llm_client import LLMClient
from app.services.rag_service import RagConfig, _build_prompt, ask, stream_ask

_SOURCES = [
    {"job_id": "doc:x", "content": "拙政园始建于明正德四年，王献臣所建。", "distance": 0.25},
    {"job_id": "doc:y", "content": "西湖全年免费。", "distance": 0.6},
]


@pytest.fixture()
def stub_search(monkeypatch):
    monkeypatch.setattr(
        rag_service, "search_similar",
        lambda q, k=3, tenant_id=None, multi=None: {"results": _SOURCES, "sub_questions": [q]},
    )


def _stub_llm(real_text: str | None):
    class _LLM:
        mode = "real"
        api_key = "sk-test"
        base_url = "https://example.com/v1"
        model = "test-model"

    return _LLM()


def test_build_prompt_marks_sources():
    prompt = _build_prompt("问题", _SOURCES)
    assert "[1] 拙政园始建于明正德四年" in prompt and "禁止编造" in prompt


def test_ask_llm_mode(stub_search, monkeypatch):
    monkeypatch.setattr(rag_service, "_generate", lambda llm, p, fallback_model="": "王献臣所建 [1]")
    out = ask("拙政园是谁建的", RagConfig(), llm=_stub_llm("x"))
    assert out["mode"] == "llm" and "[1]" in out["answer"]
    assert out["sources"][0]["job_id"] == "doc:x"


def test_ask_refusal_on_far_distance(stub_search):
    out = ask("无关问题", RagConfig(score_max=0.1), llm=_stub_llm("x"))
    assert out["mode"] == "refusal" and out["sources"]


def test_ask_empty(stub_search, monkeypatch):
    monkeypatch.setattr(
        rag_service, "search_similar",
        lambda *a, **k: {"results": [], "sub_questions": ["q"]},
    )
    out = ask("任何", RagConfig(), llm=_stub_llm("x"))
    assert out["mode"] == "empty"


def test_ask_retrieval_fallback_when_llm_empty(stub_search, monkeypatch):
    monkeypatch.setattr(rag_service, "_generate", lambda llm, p, fallback_model="": "")
    out = ask("拙政园", RagConfig(), llm=_stub_llm("x"))
    assert out["mode"] == "retrieval"  # LLM 失败不编造，落检索模式


def test_stream_ask_events(stub_search, monkeypatch):
    monkeypatch.setattr(
        rag_service, "_stream_generate", lambda llm, p, fallback_model="": iter(["回答", "正文"])
    )
    events = list(stream_ask("拙政园", RagConfig(), llm=_stub_llm("x")))
    types = [e["type"] for e in events]
    assert types == ["meta", "token", "token", "done"]
    assert events[-1]["mode"] == "llm" and events[-1]["answer"] == "回答正文"


def test_stream_ask_refusal_short_circuit(stub_search):
    events = list(stream_ask("无关", RagConfig(score_max=0.1), llm=_stub_llm("x")))
    assert [e["type"] for e in events] == ["meta", "done"]
    assert events[-1]["mode"] == "refusal"
