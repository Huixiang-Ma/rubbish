from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.main import app


def wait_completed(client: TestClient, job_id: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = client.get(f"/api/plans/{job_id}").json()
        if state["status"] in {"COMPLETED", "FAILED", "CORRUPTED"}:
            assert state["status"] == "COMPLETED", state
            return state
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} not completed in time")


def main() -> None:
    runs = 10
    with TestClient(app) as client:
        parent_payload = {
            "destination": "北京",
            "days": 3,
            "budget": 5000,
            "origin": "上海",
            "preferences": ["亲子", "博物馆"],
            "constraints": [f"bench-parent-{time.time_ns()}"],
        }
        parent = client.post("/api/plans", json=parent_payload).json()["job_id"]
        wait_completed(client, parent)

        full_times = []
        for i in range(runs):
            started = time.perf_counter()
            job_id = client.post(
                "/api/plans",
                json={
                    "destination": "北京",
                    "days": 3,
                    "budget": 5000,
                    "origin": "上海",
                    "preferences": ["亲子", "博物馆"],
                    "constraints": [f"bench-full-{i}-{time.time_ns()}"],
                },
            ).json()["job_id"]
            wait_completed(client, job_id)
            full_times.append(time.perf_counter() - started)

        incremental_times = []
        for i in range(runs):
            started = time.perf_counter()
            child = client.post(
                f"/api/plans/{parent}/replan",
                json={"change_request": f"减少打车-{i}-{time.time_ns()}", "base_version": 1},
            ).json()["job_id"]
            wait_completed(client, child)
            incremental_times.append(time.perf_counter() - started)

    full_avg = sum(full_times) / len(full_times)
    incremental_avg = sum(incremental_times) / len(incremental_times)
    reduction = (1 - incremental_avg / full_avg) * 100 if full_avg else 0.0
    print(f"runs={runs}")
    print(f"全量重算平均耗时: {full_avg * 1000:.0f} ms")
    print(f"增量重算平均耗时: {incremental_avg * 1000:.0f} ms（复用未变更节点）")
    print(f"耗时降低: {reduction:.1f}%")
    print("口径：mock 模式下节点耗时接近毫秒级，差距在 LLM_MODE=real 模式下显著放大（省掉一次真实模型调用）。")


if __name__ == "__main__":
    main()
