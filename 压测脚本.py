# -*- coding: utf-8 -*-
"""压力测试：山水有约后端（localhost:8000）
场景：
  S1 读基准   GET /health + GET /（首页 HTML）
  S2 实时窗口 GET /api/services/attraction（高德 POI 实时链路，含 0.4s 限速器）
  S3 生成链路 POST /api/plans（队列+Worker+LLM 真实生成），随后轮询至终态
指标：RPS、P50/P90/P95/P99 延迟、错误率、并发吞吐；S3 额外统计端到端出稿时长。
"""
import asyncio
import json
import statistics
import time
from collections import Counter

import httpx

BASE = "http://localhost:8000"
UA = {"Content-Type": "application/json"}


def pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, round(p / 100 * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def summarize(name: str, latencies_ms: list[float], errors: int, wall_s: float) -> dict:
    n = len(latencies_ms)
    s = sorted(latencies_ms)
    return {
        "scene": name,
        "requests": n + errors,
        "errors": errors,
        "error_rate": round(errors / (n + errors) * 100, 2) if (n + errors) else 0.0,
        "rps": round(n / wall_s, 1) if wall_s > 0 else 0.0,
        "p50_ms": round(pct(s, 50), 1),
        "p90_ms": round(pct(s, 90), 1),
        "p95_ms": round(pct(s, 95), 1),
        "p99_ms": round(pct(s, 99), 1),
        "avg_ms": round(statistics.mean(s), 1) if s else 0.0,
        "max_ms": round(s[-1], 1) if s else 0.0,
    }


async def read_worker(path: str, sem: asyncio.Semaphore,
                       lat: list[float], errors: list[int], deadline: float):
    """独立连接的虚拟用户：真实浏览器是一人一连接，连接池排队会人为抬高 P95。"""
    async with httpx.AsyncClient(timeout=30) as client:
        while time.monotonic() < deadline:
            async with sem:
                if time.monotonic() >= deadline:
                    break
                t0 = time.perf_counter()
                try:
                    r = await client.get(BASE + path)
                    if r.status_code >= 500:
                        errors.append(1)
                except Exception:
                    errors.append(1)
                lat.append((time.perf_counter() - t0) * 1000)


async def services_worker(sem: asyncio.Semaphore,
                          lat: list[float], errors: list[int], codes: Counter, deadline: float):
    """ attractions 窗口；注意后端对高德有 0.4s 全局限速，高并发下会被串行化——这正是要测的行为 """
    cities = ["成都市", "西安市", "杭州市", "北京市"]
    i = 0
    async with httpx.AsyncClient(timeout=30) as client:
      while time.monotonic() < deadline:
        async with sem:
            if time.monotonic() >= deadline:
                break
            city = cities[i % len(cities)]
            i += 1
            t0 = time.perf_counter()
            try:
                r = await client.get(f"{BASE}/api/services/attraction", params={"destination": city})
                codes[r.status_code] += 1
                if r.status_code >= 500:
                    errors.append(1)
            except Exception:
                codes["EXC"] += 1
                errors.append(1)
            lat.append((time.perf_counter() - t0) * 1000)


async def create_plan(client: httpx.AsyncClient, lat: list[float], errors: list[int],
                      codes: Counter, e2e: list[float], job_results: list, idx: int, max_wait: float = 120.0):
    payload = {
        "destination": ["成都市", "西安市", "杭州市", "北京市"][idx % 4],
        "days": 2 + idx % 3,
        "budget": 2000 + (idx % 5) * 500,
        "travelers": 1 + idx % 3,
        "origin": ["重庆市", "上海市", None, "广州市"][idx % 4],
        "mood": "慢悠悠",
        "preferences": ["美食优先"] if idx % 2 else ["自然风光"],
    }
    t_submit = time.perf_counter()
    try:
        r = await client.post(f"{BASE}/api/plans", json=payload, timeout=30)
        codes[r.status_code] += 1
        if r.status_code != 200:
            errors.append(1)
            return
        job_id = r.json()["job_id"]
    except Exception as e:
        codes["EXC"] += 1
        errors.append(1)
        print("submit exc:", type(e).__name__)
        return
    lat.append((time.perf_counter() - t_submit) * 1000)

    # 轮询至终态
    t0 = time.monotonic()
    status = "UNKNOWN"
    while time.monotonic() - t0 < max_wait:
        try:
            s = await client.get(f"{BASE}/api/plans/{job_id}", timeout=15)
            data = s.json()
            status = data.get("status", "UNKNOWN")
            if status in ("COMPLETED", "FAILED", "CORRUPTED"):
                break
        except Exception:
            await asyncio.sleep(1)
            continue
        await asyncio.sleep(1)
    e2e.append(time.monotonic() - t_submit)
    job_results.append({"job_id": job_id, "status": status, "e2e_s": round(e2e[-1], 1)})


async def main():
    results = []
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        # ---------- S1 读基准：50 并发 15s ----------
        print("== S1 读基准 (64 独立连接 / 15s) ==")
        lat1, err1 = [], []
        sem1 = asyncio.Semaphore(50)
        t0 = time.monotonic()
        deadline = t0 + 15
        await asyncio.gather(*[read_worker("/health", sem1, lat1, err1, deadline) for _ in range(64)])
        results.append(summarize("S1 /health 读基准", lat1, len(err1), time.monotonic() - t0))

        lat2, err2 = [], []
        t0 = time.monotonic()
        deadline = t0 + 15
        await asyncio.gather(*[read_worker("/", sem1, lat2, err2, deadline) for _ in range(64)])
        results.append(summarize("S1 首页 HTML", lat2, len(err2), time.monotonic() - t0))

        # ---------- S2 实时窗口：10 并发 30s ----------
        print("== S2 景点实时窗口 (12 独立连接 / 30s) ==")
        lat3, err3, codes3 = [], [], Counter()
        sem2 = asyncio.Semaphore(10)
        t0 = time.monotonic()
        deadline = t0 + 30
        await asyncio.gather(*[services_worker(sem2, lat3, err3, codes3, deadline) for _ in range(12)])
        r3 = summarize("S2 景点POI实时", lat3, len(err3), time.monotonic() - t0)
        r3["status_codes"] = dict(codes3)
        results.append(r3)

        # ---------- S3 生成链路：8 并发提交 + 轮询到终态 ----------
        print("== S3 行程生成链路 (8 并发) ==")
        lat4, err4, codes4, e2e, jobs = [], [], Counter(), [], []
        t0 = time.monotonic()
        await asyncio.gather(*[create_plan(client, lat4, err4, codes4, e2e, jobs, i) for i in range(8)])
        s3 = summarize("S3 生成-提交延迟", lat4, len(err4), time.monotonic() - t0)
        s3["status_codes"] = dict(codes4)
        s3["e2e_avg_s"] = round(statistics.mean(e2e), 1) if e2e else None
        s3["e2e_min_s"] = round(min(e2e), 1) if e2e else None
        s3["e2e_max_s"] = round(max(e2e), 1) if e2e else None
        s3["e2e_p50_s"] = round(statistics.median(e2e), 1) if e2e else None
        s3["jobs"] = jobs
        results.append(s3)

    print(json.dumps(results, ensure_ascii=False, indent=1))
    Path = __import__("pathlib").Path
    Path("压测结果.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


asyncio.run(main())
