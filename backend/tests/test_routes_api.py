"""标品线路 API 冒烟测试（TestClient，不依赖 pgvector；pg 未启用时验证路由/校验/404）。"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_routes_list_when_pg_disabled():
    """pg_mirror 未启用（DATABASE_URL 空）时，线路列表返回空——不报错。"""
    r = client.get("/api/routes", params={"tenant_id": "default"})
    assert r.status_code == 200
    assert r.json() == {"routes": []}


def test_routes_create_missing_required_422():
    r = client.post("/api/routes", json={"route_id": "r-1"})  # 缺 city/days_detail
    assert r.status_code == 422


def test_routes_get_nonexistent_404():
    r = client.get("/api/routes/nonexist", params={"tenant_id": "default"})
    assert r.status_code == 404


def test_routes_create_ok_when_pg_disabled():
    """pg 未启用时 create 返回 memory 模式（不抛错），route_id 回显。"""
    payload = {
        "route_id": "suzhou-classic-2d", "city": "苏州", "days": 2,
        "days_detail": [{"day": 1, "blocks": [{"slot": "09:00", "type": "poi", "name": "拙政园"}]}],
    }
    r = client.post("/api/routes", json=payload)
    assert r.status_code == 200
    assert r.json()["route_id"] == "suzhou-classic-2d"


def test_routes_publish_nonexistent_404():
    r = client.post("/api/routes/nonexist/publish", json={"tenant_id": "default", "reviewer": "tester"})
    assert r.status_code == 404