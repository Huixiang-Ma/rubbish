"""Regression coverage for the toB workbench APIs."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.services import auth_service
from app.services import paths as paths_mod
from app.services.checkpoint_store import CheckpointStore

client = TestClient(app)


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(paths_mod, "DATA_ROOT", tmp_path)
    from app.api import admin as admin_mod

    monkeypatch.setattr(admin_mod, "DATA_ROOT", tmp_path)
    return tmp_path


def make_job(job_id: str, user_input: dict, **extra) -> dict:
    store = CheckpointStore()
    store.create(job_id, user_input, f"hash_{job_id}")
    state = store.load(job_id)
    state.update(extra)
    store.save(job_id, state)
    return state


def test_status_exposes_parent_and_completed_nodes(data_root):
    make_job("plan_parent001", {"destination": "北京"}, status="COMPLETED")
    make_job(
        "plan_child001",
        {"destination": "北京"},
        status="RUNNING",
        parent_job_id="plan_parent001",
        completed_nodes=["Researcher", "Planner"],
    )

    resp = client.get("/api/plans/plan_child001")

    assert resp.status_code == 200
    assert resp.json()["parent_job_id"] == "plan_parent001"
    assert resp.json()["completed_nodes"] == ["Researcher", "Planner"]


def test_replan_persists_parent_job_id(data_root):
    make_job("plan_parent002", {"destination": "北京", "days": 3}, status="COMPLETED", version=1)

    # RBAC 生效后：管理类端点需带 admin token（与 toB 前端 admin.html 的 auth() 行为一致）
    from app.services.auth_service import issue_token

    headers = {"Authorization": f"Bearer {issue_token('admin', 'admin')}"}
    resp = client.post(
        "/api/plans/plan_parent002/replan",
        json={"change_request": "预算改为 3000 元，减少打车", "base_version": 1},
        headers=headers,
    )

    assert resp.status_code == 200
    child_state = CheckpointStore().load(resp.json()["job_id"])
    assert child_state["parent_job_id"] == "plan_parent002"


def test_plan_diff_line_level(data_root):
    make_job("plan_diffpa", {"destination": "北京"}, status="COMPLETED")
    make_job("plan_diffch", {"destination": "北京"}, status="COMPLETED", parent_job_id="plan_diffpa")
    (paths_mod.DATA_ROOT / "plan_diffpa" / "travel_plan.md").write_text("行一\n行二\n行三\n", encoding="utf-8")
    (paths_mod.DATA_ROOT / "plan_diffch" / "travel_plan.md").write_text("行一\n行二改\n行三\n行四\n", encoding="utf-8")

    resp = client.get("/api/plans/plan_diffch/diff")

    assert resp.status_code == 200
    body = resp.json()
    assert body["parent_job_id"] == "plan_diffpa"
    assert (body["added"], body["removed"], body["unchanged"]) == (2, 1, 2)
    assert [row["type"] for row in body["lines"]].count("add") == 2


def test_plan_diff_without_parent_returns_400(data_root):
    make_job("plan_noparent", {"destination": "北京"}, status="COMPLETED")

    resp = client.get("/api/plans/plan_noparent/diff")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "NOT_A_REPLAN：该任务无父版本，无法对比"


def test_feedbacks_aggregates_from_audit(data_root):
    make_job("plan_fb0001", {"destination": "北京"}, status="COMPLETED", customer="客户甲")
    make_job("plan_fb0002", {"destination": "上海"}, status="COMPLETED", customer="客户乙")
    store = CheckpointStore()
    store.append_audit("plan_fb0001", {"action": "feedback", "kind": "praise", "operator": "顾问A", "content": "行程很贴心"})
    store.append_audit("plan_fb0002", {"action": "feedback", "kind": "complaint", "operator": "顾问B", "content": "第二天太赶"})

    # P0 安全基线后 AUTH_ENABLED=true：admin 路由组（含客户之声聚合）需要管理员 token
    headers = {"Authorization": f"Bearer {auth_service.issue_token('admin', 'admin')}"}
    resp = client.get("/api/feedbacks", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["praise_count"] == 1
    assert body["complaint_count"] == 1
    assert {item["customer"] for item in body["items"]} == {"客户甲", "客户乙"}

    only_praise = client.get("/api/feedbacks", params={"kind": "praise"}, headers=headers).json()
    assert only_praise["total"] == 1
    assert only_praise["complaint_count"] == 0


def test_export_contains_neutral_claim(data_root):
    make_job("plan_export1", {"destination": "北京"}, status="COMPLETED")
    (paths_mod.DATA_ROOT / "plan_export1" / "travel_plan.md").write_text("# 行程书\n内容", encoding="utf-8")

    resp = client.post(
        "/api/plans/plan_export1/export",
        json={"brand": "示例文旅科技有限公司", "consultant": "顾问A"},
    )

    assert resp.status_code == 200
    assert "中立声明：本方案由中立规划引擎生成，不绑定任何供应链、不参与返佣分成，推荐结果不受库存利益影响。" in resp.json()["markdown"]
