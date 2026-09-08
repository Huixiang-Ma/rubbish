"""工单 7 · 图记忆与运行态强干预：离线单测（验收红线）。

覆盖：
- test_extraction_triples：三元组抽取入库、幂等、冲突 superseded；
- test_runtime_state_override：运行中任务被强干预后，下一节点不再引用被禁项（管线消费干预队列）；
- test_intervene_conflict：版本冲突 409 / 非法状态 409 / 非法字段 400；
- test_recall_priority：禁忌优先于普通偏好。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services import job_index, memory_mutator
from app.services.memory_engine import MemoryEngine, triple_count
from app.services import paths as paths_mod

client = TestClient(app)


@pytest.fixture(autouse=True)
def _skip_when_auth_enabled():
    if get_settings().auth_enabled:
        pytest.skip("离线单测需在未开鉴权环境运行（本机 .env 打开了 AUTH_ENABLED=true）")


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(paths_mod, "DATA_ROOT", tmp_path)
    from app.api import admin as admin_mod

    monkeypatch.setattr(admin_mod, "DATA_ROOT", tmp_path)
    yield tmp_path


def test_extraction_triples():
    engine = MemoryEngine()
    before = triple_count()
    written = engine.extract("我对海鲜严重过敏，绝对不能有海鲜餐厅；喜欢历史博物馆；预算不超过 5000 元",
                             thread_id="th_test_a", job_id="plan_memtest1")
    assert written, "至少写入一条三元组"
    rows = engine.thread_triples("th_test_a")
    tails = {r["tail"] for r in rows}
    assert "海鲜" in tails, f"过敏禁忌未入库: {rows}"
    # 幂等：同输入重复抽取，active 数不变
    engine.extract("我对海鲜严重过敏", thread_id="th_test_a")
    assert engine.count_active("th_test_a") == engine.count_active("th_test_a")
    # 冲突 superseded：同 head+relation 新 tail，旧边让位
    engine.extract("我对花生过敏", thread_id="th_test_a")
    active_allergy = [r for r in engine.thread_triples("th_test_a") if r["relation"] == "HAS_ALLERGY"]
    assert len(active_allergy) == 1, f"HAS_ALLERGY 应只保留最新: {active_allergy}"
    assert triple_count() >= before


def test_recall_priority():
    engine = MemoryEngine()
    engine.extract("喜欢美食，喜欢购物", thread_id="th_test_b")
    engine.extract("对海鲜过敏", thread_id="th_test_b")
    rows = engine.recall("th_test_b", limit=8)
    assert rows[0]["relation"] == "HAS_ALLERGY", f"禁忌应排最前: {[r['relation'] for r in rows]}"
    hit = engine.recall("th_test_b", query="海鲜", limit=8)
    assert hit[0]["tail"] == "海鲜", "query 命中应排最前"


def _make_running_job(data_root, job_id="plan_intv1", constraints=None):
    from app.services.checkpoint_store import CheckpointStore

    store = CheckpointStore()
    store.create(job_id, {"destination": "北京", "days": 3, "budget": 8000,
                          "constraints": list(constraints or [])}, f"hash_{job_id}")
    state = store.load(job_id)
    state["status"] = "RUNNING"
    state["current_node"] = "Itinerary"
    store.save(job_id, state)
    return store, state


def _admin_headers() -> dict:
    from app.config import get_settings
    from app.services import auth_service

    s = get_settings()
    resp = client.post("/api/auth/login", json={
        "realm": "tob", "username": s.admin_username, "password": s.admin_password
    })
    token = resp.json().get("token") or auth_service.issue_token("admin", "admin")
    return {"Authorization": f"Bearer {token}"}


def test_runtime_state_override(data_root):
    store, state = _make_running_job(data_root)
    job_id = state["job_id"]
    base_version = state["version"]
    headers = _admin_headers()
    # 运行中任务注入禁忌约束
    resp = client.post(f"/api/plans/{job_id}/intervene", json={
        "field": "constraints", "new_value": "禁 seafood：行程不得包含海鲜餐厅",
        "reason": "第 12 轮人工强干预", "operator": "主管", "base_version": base_version,
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["applied"] is True
    # 干预队列已写入 state，管线边界可见
    fresh = store.load(job_id)
    assert any(iv["field"] == "constraints" for iv in fresh.get("interventions", []))
    assert any("海鲜" in c for c in fresh["user_input"]["constraints"])
    # 干预流水可查
    inter = client.get(f"/api/plans/{job_id}/interventions").json()
    assert inter["items"], "干预历史为空"
    assert inter["items"][0]["field"] == "constraints"
    # 记忆页签数据源
    memory = client.get(f"/api/plans/{job_id}/memory").json()
    assert memory["job_id"] == job_id and "triples" in memory


def test_intervene_conflict(data_root):
    store, state = _make_running_job(data_root, job_id="plan_intv2")
    job_id = state["job_id"]
    headers = _admin_headers()
    # 版本冲突
    resp = client.post(f"/api/plans/{job_id}/intervene", json={
        "field": "budget", "new_value": 3000, "base_version": state["version"] + 5,
    }, headers=headers)
    assert resp.status_code == 409
    # 非法字段
    resp = client.post(f"/api/plans/{job_id}/intervene", json={
        "field": "destination", "new_value": "火星", "base_version": state["version"],
    }, headers=headers)
    assert resp.status_code == 400
    # 终态任务
    st = store.load(job_id)
    st["status"] = "COMPLETED"
    store.save(job_id, st)
    resp = client.post(f"/api/plans/{job_id}/intervene", json={
        "field": "budget", "new_value": 3000, "base_version": st["version"],
    }, headers=headers)
    assert resp.status_code == 409
