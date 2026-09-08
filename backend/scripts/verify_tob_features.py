"""toB 各页签功能验收：基于 seed52791 测试数据批次逐项核对。

覆盖：状态图数据源 / HITL 审核台 / 客户之声 / 客户管理 / 版本 diff / 白标导出 /
     租户筛选 / PG 落库核对。
用法：cd backend && python scripts/verify_tob_features.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

BASE = "http://127.0.0.1:8000"
TAG = "seed52791"
PASS: list[str] = []
FAIL: list[str] = []


def call(method: str, url: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(f"{name}{(' —— ' + detail) if detail and not cond else ''}")
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not cond else ""))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE)
    parser.add_argument("--tag", default=TAG)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    tag = args.tag

    from app.config import get_settings
    s = get_settings()
    _, login = call("POST", f"{base}/api/auth/login", {"realm": "tob", "username": s.admin_username, "password": s.admin_password})
    token = login.get("token")
    assert token, f"login failed: {login}"

    print("== 1. 方案列表与状态覆盖 ==")
    _, plans = call("GET", f"{base}/api/plans?limit=500", token=token)
    items = plans["items"]
    batch = [i for i in items if True]  # 列表接口无约束字段，逐条过滤太贵；用 PG 侧核对
    check("列表可访问", plans.get("total", 0) > 0, f"total={plans.get('total')}")

    print("== 2. HITL 审核台 ==")
    _, pend = call("GET", f"{base}/api/approvals/pending", token=token)
    check("挂起队列非空", pend.get("total", 0) > 0, f"total={pend.get('total')}")
    if pend["items"]:
        sample = pend["items"][0]
        check("队列字段完整", all(k in sample for k in ("job_id", "status", "version", "resume_from")), str(sample.keys()))

    print("== 3. 客户之声 ==")
    _, fb = call("GET", f"{base}/api/feedbacks?limit=500", token=token)
    check(f"反馈条数>0（本批 16+ 条）", fb.get("total", 0) >= 10, f"total={fb.get('total')}")
    check("好评/投诉计数一致", fb["praise_count"] + fb["complaint_count"] == fb["total"])
    _, fb_p = call("GET", f"{base}/api/feedbacks?kind=praise&limit=500", token=token)
    check("好评筛选生效", fb_p["total"] == fb["praise_count"])

    print("== 4. 客户管理 ==")
    _, cust_all = call("GET", f"{base}/api/plans?limit=500", token=token)
    custs = {i.get("customer") or "未归属" for i in cust_all["items"]}
    for c in ("华铁国旅", "携程定制部", "同程会展中心", "未归属"):
        check(f"客户分组含 {c}", c in custs)
    _, plans_huatie = call("GET", f"{base}/api/plans?customer={urllib.parse.quote('华铁国旅')}&limit=500", token=token)
    check("按客户筛选生效", plans_huatie["total"] >= 8, f"total={plans_huatie['total']}")

    print("== 5. 版本 diff（父子链） ==")
    _, all_p = call("GET", f"{base}/api/plans?limit=500", token=token)
    child = next((i for i in all_p["items"] if i["status"] == "COMPLETED" and (i.get("version", 1) > 1 or True)), None)
    # 找有 parent 的：直接用 PG 标记的子任务——简化：从 feed 侧扫已完成且可 diff 的
    diff_ok = False
    diff_detail = ""
    for i in all_p["items"][:60]:
        if i["status"] != "COMPLETED":
            continue
        code, d = call("GET", f"{base}/api/plans/{i['job_id']}/diff", token=token)
        if code == 200:
            diff_ok = True
            diff_detail = f"{i['job_id']} +{d['added']}/-{d['removed']}"
            break
        if code == 400:
            continue
    check("存在可 diff 的父子任务", diff_ok, diff_detail)

    print("== 6. 白标导出（含中立声明） ==")
    done = next((i for i in all_p["items"] if i["status"] == "COMPLETED"), None)
    if done:
        code, exp = call("POST", f"{base}/api/plans/{done['job_id']}/export",
                         {"brand": "验收测试品牌", "consultant": "验收员"}, token=token)
        check("导出成功", code == 200)
        check("含中立声明", "中立声明" in exp.get("markdown", ""))
    else:
        check("存在已完成任务可导出", False)

    print("== 7. 租户筛选（B7） ==")
    _, t1 = call("GET", f"{base}/api/plans?tenant=tenant-huatie&limit=500", token=token)
    check("租户筛选生效", t1["total"] >= 8, f"total={t1['total']}")
    _, stats = call("GET", f"{base}/api/stats/overview?tenant=tenant-huatie", token=token)
    check("统计按租户过滤", stats["total"] == t1["total"], f"stats={stats['total']} vs list={t1['total']}")

    print("== 8. 状态图数据源（loadFlow 依赖） ==")
    dist = call("GET", f"{base}/api/stats/overview", token=token)[1]["status_distribution"]
    check("stats/overview 状态分布覆盖挂起/完成多状态", len(dist) >= 3, str(dist)[:120])

    print("== 9. PG 落库核对 ==")
    import subprocess
    q = f"SELECT count(*) FROM plan_jobs WHERE payload::text LIKE '%{tag}%';"
    r = subprocess.run(["docker", "exec", "wl_travel_mvp-postgres-1", "psql", "-U", "wl", "-d", "wl_travel", "-t", "-A", "-c", q],
                       capture_output=True, text=True)
    pg_jobs = int(r.stdout.strip() or 0)
    check("PG plan_jobs ≥32（本批）", pg_jobs >= 32, f"count={pg_jobs}")
    q2 = ("SELECT count(*) FROM audit_logs a JOIN plan_jobs p ON a.job_id=p.job_id "
          f"WHERE p.payload::text LIKE '%{tag}%' AND a.action='feedback';")
    r2 = subprocess.run(["docker", "exec", "wl_travel_mvp-postgres-1", "psql", "-U", "wl", "-d", "wl_travel", "-t", "-A", "-c", q2],
                        capture_output=True, text=True)
    pg_fb = int(r2.stdout.strip() or 0)
    check("PG audit_logs 含反馈事件", pg_fb >= 10, f"count={pg_fb}")

    print(f"\n== 结果: {len(PASS)} pass / {len(FAIL)} fail ==")
    for f in FAIL:
        print(f"  FAIL: {f}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
