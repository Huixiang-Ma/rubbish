# -*- coding: utf-8 -*-
"""routes API 端到端验证：create → get → publish → variant → daily-check → 租户隔离"""
import json
import sys
import urllib.request

BASE = "http://localhost:8000"


def call(method: str, path: str, payload: dict | None = None, params: str = ""):
    url = BASE + path + ("" if not params else "?" + params)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def check(name: str, cond: bool, detail=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f"  -- {detail}" if detail and not cond else ""))
    return cond


results = []

ROUTE = {
    "route_id": "e2e-suzhou-2d",
    "tenant_id": "tenant_a",
    "city": "苏州",
    "theme": "园林水乡",
    "days": 2,
    "pace": "适中",
    "audience": "亲子",
    "season": "四季",
    "days_detail": [
        {"day": 1, "title": "古典园林日", "blocks": [
            {"type": "poi", "name": "拙政园", "time": "09:00-12:00"},
            {"type": "poi", "name": "狮子林", "time": "13:30-15:30"},
            {"type": "meal", "name": "平江路晚餐", "time": "18:00-19:30"},
        ]},
        {"day": 2, "title": "水乡古镇日", "blocks": [
            {"type": "poi", "name": "虎丘", "time": "09:00-11:30"},
            {"type": "poi", "name": "山塘街", "time": "13:00-16:00"},
        ]},
    ],
    "variants": {"亲子模式": {"replace": [{"remove": "虎丘", "add": "苏州动物园"}]}},
    "knowledge_refs": ["拙政园"],
}

# 1. create
code, body = call("POST", "/api/routes", ROUTE)
results.append(check("create 返回 200 且 mode=pg", code == 200 and body.get("mode") == "pg", f"{code} {body}"))

# 2. get（enrich 会走 RAG 检索知识卡片）
code, body = call("GET", "/api/routes/e2e-suzhou-2d", params="tenant_id=tenant_a")
ok = code == 200 and body.get("status") == "draft" and len(body.get("days_detail", [])) == 2
results.append(check("get 返回 draft 且 2 天行程", ok, f"{code} {json.dumps(body, ensure_ascii=False)[:200]}"))
knowledge = body.get("_knowledge")
results.append(check("enrich_knowledge 渲染知识卡片", bool(knowledge),
                     f"_knowledge={json.dumps(knowledge, ensure_ascii=False)[:200] if knowledge else knowledge}"))

# 3. publish（人工签发）
code, body = call("POST", "/api/routes/e2e-suzhou-2d/publish", {"tenant_id": "tenant_a", "reviewer": "e2e_tester"})
results.append(check("publish 后 status=published", code == 200 and body.get("status") == "published",
                     f"{code} {json.dumps(body, ensure_ascii=False)[:200]}"))

# 3b. 重复 publish 应幂等（status 已 published 不再变更）
code, body = call("POST", "/api/routes/e2e-suzhou-2d/publish", {"tenant_id": "tenant_a", "reviewer": "e2e_again"})
results.append(check("重复 publish 幂等（reviewer 不变）", code == 200 and body.get("reviewer") == "e2e_tester",
                     f"reviewer={body.get('reviewer')}"))

# 4. variant（亲子模式替换 block）
code, body = call("POST", "/api/routes/e2e-suzhou-2d/variant", {"tenant_id": "tenant_a", "variant": "亲子模式"})
day2 = next((d for d in body.get("days_detail", []) if d.get("day") == 2), {})
names = [b.get("name") for b in day2.get("blocks", [])]
results.append(check("variant 替换 虎丘→苏州动物园 且不动原库", "苏州动物园" in names, f"blocks={names}"))
results.append(check("variant 标记 _active=亲子模式", body.get("variants", {}).get("_active") == "亲子模式"))

# 5. daily-check（出行日校验，逐 POI 检索语料）
code, body = call("GET", "/api/routes/e2e-suzhou-2d/daily-check", params="tenant_id=tenant_a")
ok = code == 200 and isinstance(body.get("warnings"), list)
results.append(check("daily-check 返回告警清单", ok, f"{code} {body}"))
print(f"       daily-check warnings: {json.dumps(body.get('warnings'), ensure_ascii=False)[:300]}")

# 6. 租户隔离：tenant_b 看不到 tenant_a 的线路
code, body = call("GET", "/api/routes/e2e-suzhou-2d", params="tenant_id=tenant_b")
results.append(check("租户隔离：tenant_b 读取返回 404", code == 404, f"{code} {body}"))

# 7. 404：不存在的线路
code, body = call("GET", "/api/routes/not-exist", params="tenant_id=tenant_a")
results.append(check("不存在线路返回 404", code == 404, f"{code} {body}"))

# 8. list 过滤
code, body = call("GET", "/api/routes", params="tenant_id=tenant_a&city=苏州&status=published")
ids = [r.get("route_id") for r in body.get("routes", [])]
results.append(check("list 按城市+状态过滤命中", "e2e-suzhou-2d" in ids, f"routes={ids}"))

print()
print(f"=== 结果: {sum(results)}/{len(results)} 通过 ===")
sys.exit(0 if all(results) else 1)
