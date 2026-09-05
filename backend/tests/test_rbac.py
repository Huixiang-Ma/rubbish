"""RBAC 角色审批控制单测：traveler 403、supervisor 放行、无 token 401。

注意：TestClient 必须用 with 上下文，startup 事件才会启动后台 Worker；
任务需走到 WAITING_* 挂起态才能测审批权限。
"""
import time

from fastapi.testclient import TestClient

from app.main import app
from app.services import auth_service


def _login_tob(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/auth/login", json={"realm": "tob", "username": username, "password": password})
    assert resp.status_code == 200, resp.json()
    return resp.json()


def _make_hold_job(client: TestClient, suffix: str) -> str:
    resp = client.post(
        "/api/plans",
        json={
            "destination": "北京",
            "days": 2,
            "budget": 100,
            "origin": "上海",
            "constraints": [f"rbac-{suffix}-{time.time_ns()}"],
        },
    )
    job_id = resp.json()["job_id"]
    t0 = time.monotonic()
    while time.monotonic() - t0 < 240:
        state = client.get(f"/api/plans/{job_id}").json()
        if state["status"] in ("WAITING_BUDGET_APPROVAL", "WAITING_SAFETY_REVIEW", "COMPLETED"):
            return job_id
        time.sleep(0.3)
    raise AssertionError(f"任务未进入可审批状态: {state}")


def test_role_tokens_issue():
    with TestClient(app) as client:
        supervisor = _login_tob(client, "supervisor", "sv2026")
        consultant = _login_tob(client, "consultant", "ct2026")
    assert supervisor["role"] == "supervisor"
    assert consultant["role"] == "consultant"


def test_traveler_token_forbidden_on_approval():
    with TestClient(app) as client:
        job_id = _make_hold_job(client, "traveler403")
        token = auth_service.issue_token("旅者", "traveler")
        resp = client.post(
            f"/api/plans/{job_id}/approval",
            json={"decision": "approve", "operator": "旅者", "reason": "游客越权尝试", "base_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "FORBIDDEN_ROLE"


def test_missing_token_unauthorized():
    with TestClient(app) as client:
        job_id = _make_hold_job(client, "notoken401")
        resp = client.post(
            f"/api/plans/{job_id}/approval",
            json={"decision": "approve", "operator": "匿名", "reason": "无 token", "base_version": 1},
        )
        assert resp.status_code == 401


def test_supervisor_can_approve():
    with TestClient(app) as client:
        job_id = _make_hold_job(client, "svok")
        token = auth_service.issue_token("supervisor", "supervisor")
        resp = client.post(
            f"/api/plans/{job_id}/approval",
            json={"decision": "approve", "operator": "主管", "reason": "主管放行", "base_version": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()["status"] in ("APPROVED", "RUNNING")


def test_consultant_can_replan_but_not_approve():
    with TestClient(app) as client:
        job_id = _make_hold_job(client, "ctmixed")
        consultant = auth_service.issue_token("consultant", "consultant")
        # 审批：顾问无权
        resp = client.post(
            f"/api/plans/{job_id}/approval",
            json={"decision": "approve", "operator": "顾问", "reason": "顾问越权审批", "base_version": 1},
            headers={"Authorization": f"Bearer {consultant}"},
        )
        assert resp.status_code == 403
        # 重规划：顾问有权
        resp2 = client.post(
            f"/api/plans/{job_id}/replan",
            json={"change_request": "预算改为 5000 元", "base_version": 1},
            headers={"Authorization": f"Bearer {consultant}"},
        )
        assert resp2.status_code == 200, resp2.json()
