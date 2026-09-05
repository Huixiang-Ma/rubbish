from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib import request

lock = threading.Lock()


def percentile(sorted_values: list[float], ratio: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, int(len(sorted_values) * ratio))
    return sorted_values[index]


def submit_one(base_url: str, index: int, latencies: list[float], errors: list[str]) -> None:
    payload = {
        "destination": "北京",
        "days": 3,
        "budget": 5000,
        "preferences": ["亲子"],
        "constraints": [f"qa:loadtest-{index}-{time.time_ns()}"],
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{base_url}/api/plans",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    try:
        with request.urlopen(req, timeout=30) as resp:
            resp.read()
            ok = resp.status == 200
    except Exception as exc:  # noqa: BLE001 - 压测需要统计所有失败
        ok = False
        with lock:
            errors.append(str(exc))
    elapsed = time.perf_counter() - start
    if ok:
        with lock:
            latencies.append(elapsed * 1000)


def main() -> None:
    parser = argparse.ArgumentParser(description="POST /api/plans 提交接口压测")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--total", type=int, default=400)
    parser.add_argument("--concurrency", type=int, default=64)
    args = parser.parse_args()

    latencies: list[float] = []
    errors: list[str] = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for i in range(args.total):
            pool.submit(submit_one, args.base_url, i, latencies, errors)
        pool.shutdown(wait=True)
    elapsed = time.perf_counter() - started

    latencies.sort()
    success = len(latencies)
    rps = success / elapsed if elapsed > 0 else 0.0
    print(f"total={args.total} success={success} errors={len(errors)}")
    print(f"elapsed={elapsed:.2f}s submit_rps={rps:.1f}")
    print(
        "latency_ms p50={:.0f} p95={:.0f} p99={:.0f} max={:.0f}".format(
            percentile(latencies, 0.50),
            percentile(latencies, 0.95),
            percentile(latencies, 0.99),
            latencies[-1] if latencies else 0,
        )
    )
    if errors:
        print("first_errors:", errors[:3])
    print("口径：仅统计 POST /api/plans 提交（含 state.json 原子落盘与入队），不含行程生成。")


if __name__ == "__main__":
    main()
