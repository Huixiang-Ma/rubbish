# toB 企业端工作台改造 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 按规格 `docs/superpowers/specs/2026-09-03-tob-workbench-design.md` 完成 toB 工作台改造——去 AI 味专业后台风 + 侧边栏信息架构 + 方案详情抽屉（行程书/决策溯源/审计）+ 改单与版本 diff + 客户管理 + 客户之声 + 待审角标，以及后端 4 处最小改动。

**架构：** 后端沿用 FastAPI 分层，只加两个只读聚合接口（`GET /api/feedbacks`、`GET /api/plans/{id}/diff`）和三处小改（replan 落盘 parent_job_id、状态响应补字段、白标导出加中立声明）。前端保持原生单文件 `admin.html`（规格明确不做框架迁移），以 CSS 变量 tokens + 右侧抽屉 + 弹窗 + toast 组织，全部接口走 `apiFetch`（带 Bearer）。

**技术栈：** Python 3.12 + FastAPI + Pydantic v2；pytest（离线单测，monkeypatch DATA_ROOT）；原生 HTML/CSS/JS + ECharts vendor。

**重要前提：**
- 本项目**尚未初始化 git 仓库**，因此计划中不含 commit 步骤，以"运行验证命令并确认输出"作为每任务的完成门。如需入库，先由用户执行 `git init`。
- 测试运行口径：在 `backend/` 目录下、默认环境变量（内存队列、`AUTH_ENABLED` 未开启）执行；若本机 `.env` 打开了 `AUTH_ENABLED=true`，鉴权相关断言会 401，属环境问题而非代码问题。
- 行号引用基于 2026-09-03 的文件状态，若实现时有偏移，以锚点代码为准。

**文件结构（职责边界）：**

| 文件 | 职责 | 动作 |
|---|---|---|
| `backend/tests/test_tob_workbench.py` | 本批全部后端行为的离线单测（每任务先写失败用例） | 新建 |
| `backend/app/models/schemas.py` | `PlanStatusResponse` 补 `parent_job_id`/`completed_nodes` | 修改 |
| `backend/app/api/plans.py` | 状态端点透出新字段；replan 落盘 parent；`GET /{job_id}/diff`；导出中立声明 | 修改 |
| `backend/app/api/admin.py` | `GET /api/feedbacks` 聚合 | 修改 |
| `frontend/admin.html` | 全量重构（CSS tokens / 侧边栏 / 抽屉 / 弹窗 / toast / 8 页签） | 修改 |
| `README.md`、`接口文档.md` | 新接口与演示脚本同步 | 修改 |

---

### 任务 1：状态响应补 `parent_job_id` 与 `completed_nodes`

**文件：**
- 修改：`backend/app/models/schemas.py:57-64`
- 修改：`backend/app/api/plans.py:204-219`（`get_plan_status`）
- 测试：`backend/tests/test_tob_workbench.py`（新建）

- [ ] **步骤 1：新建测试文件，写失败用例**

创建 `backend/tests/test_tob_workbench.py`：

```python
"""toB 工作台改造（2026-09-03 规格）：状态字段 / parent 落盘 / diff / feedbacks / 中立声明 离线单测。"""
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
from app.services import paths as paths_mod
from app.services.checkpoint_store import CheckpointStore

client = TestClient(app)


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    """把 DATA_ROOT 指到临时目录（plans 经 paths.job_dir 动态解析；admin.py 是导入期绑定，需单独打补丁）。"""
    monkeypatch.setattr(paths_mod, "DATA_ROOT", tmp_path)
    from app.api import admin as admin_mod

    monkeypatch.setattr(admin_mod, "DATA_ROOT", tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _skip_when_auth_enabled():
    if get_settings().auth_enabled:
        pytest.skip("本机 .env 开启 AUTH_ENABLED=true，离线单测需在未开鉴权环境运行")


def _make_job(job_id: str, user_input: dict, **extra) -> dict:
    store = CheckpointStore()
    store.create(job_id, user_input, f"hash_{job_id}")
    state = store.load(job_id)
    state.update(extra)
    store.save(job_id, state)
    return state


def test_status_exposes_parent_and_completed_nodes(data_root):
    _make_job("plan_parent001", {"destination": "北京"}, status="COMPLETED")
    _make_job(
        "plan_child001",
        {"destination": "北京"},
        status="RUNNING",
        parent_job_id="plan_parent001",
        completed_nodes=["Researcher", "Planner"],
    )
    resp = client.get("/api/plans/plan_child001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["parent_job_id"] == "plan_parent001"
    assert body["completed_nodes"] == ["Researcher", "Planner"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py -v`
预期：FAIL——`assert body["parent_job_id"] == "plan_parent001"` 处 `KeyError: 'parent_job_id'`（响应模型没有该字段）。

- [ ] **步骤 3：schemas 补字段**

`backend/app/models/schemas.py` 的 `PlanStatusResponse`（第 57-64 行）末尾追加两个字段：

```python
class PlanStatusResponse(BaseModel):
    job_id: str
    status: str
    current_agent: str | None = None
    progress: int = 0
    resume_from: str | None = None
    version: int = 1
    error: str | None = None
    parent_job_id: str | None = Field(default=None, description="重规划子任务指向的父任务")
    completed_nodes: list[str] | None = Field(default=None, description="已完成 Agent 节点（含增量复用）")
```

- [ ] **步骤 4：状态端点透出**

`backend/app/api/plans.py` 的 `get_plan_status` 返回值追加两个参数：

```python
    return PlanStatusResponse(
        job_id=job_id,
        status=state["status"],
        current_agent=state.get("current_node"),
        progress=state.get("progress", 0),
        resume_from=state.get("resume_from"),
        version=state.get("version", 1),
        error=state.get("error"),
        parent_job_id=state.get("parent_job_id"),
        completed_nodes=state.get("completed_nodes"),
    )
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py -v`
预期：1 passed。

---

### 任务 2：replan 把 `parent_job_id` 落盘到子任务 state

**文件：**
- 修改：`backend/app/api/plans.py:324`（`replan` 内 `store.create(new_job_id, new_input, digest)` 之后）
- 测试：`backend/tests/test_tob_workbench.py`

- [ ] **步骤 1：追加失败用例**

在 `backend/tests/test_tob_workbench.py` 末尾追加：

```python
def test_replan_persists_parent_job_id(data_root):
    _make_job("plan_parent002", {"destination": "北京", "days": 3}, status="COMPLETED", version=1)
    resp = client.post(
        "/api/plans/plan_parent002/replan",
        json={"change_request": "预算改为 3000 元，减少打车", "base_version": 1},
    )
    assert resp.status_code == 200
    child = resp.json()["job_id"]
    state = CheckpointStore().load(child)
    assert state["parent_job_id"] == "plan_parent002"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py::test_replan_persists_parent_job_id -v`
预期：FAIL——`KeyError: 'parent_job_id'`。

- [ ] **步骤 3：replan 落盘 parent**

`replan` 中 `store.create(new_job_id, new_input, digest)` 一行后插入（仿照 `create_plan` 补写 customer 的模式）：

```python
    store.create(new_job_id, new_input, digest)
    child_state = store.load(new_job_id)
    child_state["parent_job_id"] = job_id
    store.save(new_job_id, child_state)
```

注意：后续"增量复用"分支内部是 `new_state = store.load(new_job_id)` 后 `store.save`，基于已保存 state 修改，`parent_job_id` 自然保留，无需再改。

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py -v`
预期：2 passed。

---

### 任务 3：`GET /api/plans/{job_id}/diff` 行级版本对比

**文件：**
- 修改：`backend/app/api/plans.py`（导入区 + `replan` 之前任意合适位置新增端点）
- 测试：`backend/tests/test_tob_workbench.py`

- [ ] **步骤 1：追加失败用例**

```python
def test_plan_diff_line_level(data_root):
    _make_job("plan_diffpa", {"destination": "北京"}, status="COMPLETED")
    _make_job("plan_diffch", {"destination": "北京"}, status="COMPLETED", parent_job_id="plan_diffpa")
    (paths_mod.DATA_ROOT / "plan_diffpa" / "travel_plan.md").write_text(
        "行一\n行二\n行三\n", encoding="utf-8"
    )
    (paths_mod.DATA_ROOT / "plan_diffch" / "travel_plan.md").write_text(
        "行一\n行二改\n行三\n行四\n", encoding="utf-8"
    )
    resp = client.get("/api/plans/plan_diffch/diff")
    assert resp.status_code == 200
    body = resp.json()
    assert body["parent_job_id"] == "plan_diffpa"
    assert (body["added"], body["removed"], body["unchanged"]) == (2, 1, 2)
    types = [row["type"] for row in body["lines"]]
    assert types.count("add") == 2 and types.count("del") == 1 and types.count("same") == 2


def test_plan_diff_without_parent_returns_400(data_root):
    _make_job("plan_noparent", {"destination": "北京"}, status="COMPLETED")
    resp = client.get("/api/plans/plan_noparent/diff")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "NOT_A_REPLAN：该任务无父版本，无法对比"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py -k diff -v`
预期：两条 FAIL（404 Not Found——路由不存在）。

- [ ] **步骤 3：实现 diff 端点**

`backend/app/api/plans.py` 导入区加 `import difflib`；在 `replan` 定义之前新增：

```python
@router.get("/{job_id}/diff")
def get_plan_diff(job_id: str, base: str | None = None) -> dict:
    """版本对比：子任务 vs 父任务 travel_plan.md 行级 diff（difflib，上限 2000 行）。"""
    try:
        state = store.load(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="job not found") from exc
    parent_job_id = base or state.get("parent_job_id")
    if not parent_job_id:
        raise HTTPException(status_code=400, detail="NOT_A_REPLAN：该任务无父版本，无法对比")
    child_path = job_dir(job_id) / "travel_plan.md"
    parent_path = job_dir(parent_job_id) / "travel_plan.md"
    if not child_path.exists() or not parent_path.exists():
        raise HTTPException(status_code=404, detail="travel_plan.md 尚未生成，无法对比")
    parent_lines = parent_path.read_text(encoding="utf-8").splitlines()
    child_lines = child_path.read_text(encoding="utf-8").splitlines()
    matcher = difflib.SequenceMatcher(a=parent_lines, b=child_lines, autojunk=False)
    rows: list[dict] = []
    added = removed = unchanged = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            for line in parent_lines[i1:i2]:
                rows.append({"type": "del", "text": line})
                removed += 1
        if tag in ("insert", "replace"):
            for line in child_lines[j1:j2]:
                rows.append({"type": "add", "text": line})
                added += 1
        if tag == "equal":
            for line in parent_lines[i1:i2]:
                rows.append({"type": "same", "text": line})
                unchanged += 1
    return {
        "job_id": job_id,
        "parent_job_id": parent_job_id,
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "truncated": len(rows) > 2000,
        "lines": rows[:2000],
    }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py -v`
预期：4 passed。

---

### 任务 4：`GET /api/feedbacks` 客户之声聚合

**文件：**
- 修改：`backend/app/api/admin.py`（`export_audit_csv` 之后新增）
- 测试：`backend/tests/test_tob_workbench.py`

- [ ] **步骤 1：追加失败用例**

```python
def test_feedbacks_aggregates_from_audit(data_root):
    _make_job("plan_fb0001", {"destination": "北京"}, status="COMPLETED", customer="客户甲")
    _make_job("plan_fb0002", {"destination": "上海"}, status="COMPLETED", customer="客户乙")
    store = CheckpointStore()
    store.append_audit("plan_fb0001", {"action": "feedback", "kind": "praise", "operator": "顾问A", "content": "行程很贴心"})
    store.append_audit("plan_fb0002", {"action": "feedback", "kind": "complaint", "operator": "顾问B", "content": "第二天太赶"})
    resp = client.get("/api/feedbacks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["praise_count"] == 1 and body["complaint_count"] == 1
    assert body["items"][0]["job_id"] == "plan_fb0002"
    assert body["items"][1]["customer"] == "客户甲"

    only_praise = client.get("/api/feedbacks", params={"kind": "praise"}).json()
    assert only_praise["total"] == 1 and only_praise["complaint_count"] == 0
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py::test_feedbacks_aggregates_from_audit -v`
预期：FAIL——404（路由不存在）。

- [ ] **步骤 3：实现聚合端点**

`backend/app/api/admin.py` 的 `export_audit_csv` 之后新增（复用其审计聚合模式）：

```python
@router.get("/feedbacks")
def list_feedbacks(kind: str | None = None, customer: str | None = None, limit: int = 100) -> dict:
    """客户之声：从各任务审计日志聚合反馈事件（好评/投诉），演示级口径。"""
    items: list[dict] = []
    praise = complaint = 0
    for state in _iter_states():
        job_id = state.get("job_id")
        audit_path = DATA_ROOT / str(job_id) / "audit.log"
        if not job_id or not audit_path.exists():
            continue
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("action") != "feedback":
                continue
            event_kind = event.get("kind", "praise")
            if kind and event_kind != kind:
                continue
            if customer and state.get("customer") != customer:
                continue
            if event_kind == "praise":
                praise += 1
            else:
                complaint += 1
            items.append(
                {
                    "job_id": job_id,
                    "created_at": event.get("created_at", ""),
                    "kind": event_kind,
                    "operator": event.get("operator", "-"),
                    "content": event.get("content", ""),
                    "customer": state.get("customer"),
                    "destination": (state.get("user_input") or {}).get("destination"),
                }
            )
    items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    items = items[: max(1, min(limit, 500))]
    return {"total": len(items), "praise_count": praise, "complaint_count": complaint, "items": items}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py -v`
预期：5 passed。

---

### 任务 5：白标导出加中立声明

**文件：**
- 修改：`backend/app/api/plans.py:175-178`（`export_branded_plan` 的 `branded = "\n".join((...))` 头部块）
- 测试：`backend/tests/test_tob_workbench.py`

- [ ] **步骤 1：追加失败用例**

```python
NEUTRAL_CLAIM = "中立声明：本方案由中立规划引擎生成，不绑定任何供应链、不参与返佣分成，推荐结果不受库存利益影响。"


def test_export_contains_neutral_claim(data_root):
    _make_job("plan_export1", {"destination": "北京"}, status="COMPLETED")
    (paths_mod.DATA_ROOT / "plan_export1" / "travel_plan.md").write_text("# 行程书\n内容", encoding="utf-8")
    resp = client.post(
        "/api/plans/plan_export1/export",
        json={"brand": "示例文旅科技有限公司", "consultant": "顾问A"},
    )
    assert resp.status_code == 200
    assert NEUTRAL_CLAIM in resp.json()["markdown"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py::test_export_contains_neutral_claim -v`
预期：FAIL——`assert ... in markdown` 为 False。

- [ ] **步骤 3：插入声明行**

在 `export_branded_plan` 的 `branded = "\n".join((...))` 头部块内、`f"企业品牌：{payload.brand}"` 行之后插入一个元素：

```python
            "> 中立声明：本方案由中立规划引擎生成，不绑定任何供应链、不参与返佣分成，推荐结果不受库存利益影响。",
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend && python -m pytest tests/test_tob_workbench.py -v`
预期：6 passed。

---

### 任务 6：后端全量回归

**文件：** 无新改动；验证门。

- [ ] **步骤 1：编译与全量单测**

```bash
cd backend
python -m compileall app scripts
python -m pytest tests -q
```
预期：compileall 无输出错误；pytest 全绿（既有套件 + 新增 6 条）。

- [ ] **步骤 2：smoke 六链路回归**

```bash
PYTHONIOENCODING=utf-8 python scripts/smoke_test.py
```
预期：全部通过（确认新字段/新路由未破坏正常生成、安全挂起、预算审批、409、增量重规划、断点恢复）。

---

### 任务 7：admin.html 视觉 tokens 与页面骨架重构

**文件：**
- 修改：`frontend/admin.html`（`<style>` 整块替换；`<body>` 内 `#adminApp` 骨架整块替换；登录门 `#adminGate` 内联样式部分替换）

- [ ] **步骤 1：整块替换 `<style>...</style>`（第 8-239 行）**

```css
:root {
  --bg: #f7f7f5;
  --surface: #ffffff;
  --border: #e4e4e0;
  --ink: #1c1c1a;
  --ink-2: #6f6f6a;
  --accent: #2f5d50;
  --accent-hover: #254a40;
  --accent-soft: #eaf1ef;
  --danger: #b04a3a;
  --warn: #9a6b2f;
  --warn-soft: #f6eedd;
  --ok: #3d6b4f;
  --ok-soft: #e7f0e9;
  --sidebar-bg: #16211d;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: var(--bg);
  color: var(--ink);
  font-size: 14px;
}
/* ---- 布局骨架 ---- */
#app { display: flex; min-height: 100vh; }
.sidebar {
  width: 208px; flex: 0 0 208px; background: var(--sidebar-bg); color: #e8ebe9;
  display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh;
}
.sidebar .brand { padding: 20px 18px 16px; border-bottom: 1px solid rgba(255,255,255,.08); }
.sidebar .brand .mark {
  width: 34px; height: 34px; background: #2f5d50; color: #fff; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  font-family: "Songti SC", "SimSun", serif; font-weight: 700; font-size: 14px; letter-spacing: 1px;
}
.sidebar .brand h1 { font-size: 15px; margin: 10px 0 2px; font-weight: 600; letter-spacing: .5px; }
.sidebar .brand p { margin: 0; font-size: 12px; color: #93a29b; }
.sidebar nav { display: flex; flex-direction: column; padding: 10px 0; flex: 1; }
.sidebar nav button {
  background: transparent; border: 0; color: #c4cdc9; text-align: left;
  padding: 10px 18px; font-size: 14px; cursor: pointer; position: relative;
  border-left: 3px solid transparent;
}
.sidebar nav button:hover { color: #fff; background: rgba(255,255,255,.04); }
.sidebar nav button.active { color: #fff; border-left-color: #2f5d50; background: rgba(47,93,80,.25); }
.nav-badge {
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
  background: var(--danger); color: #fff; border-radius: 9px; font-size: 11px;
  min-width: 18px; height: 18px; line-height: 18px; text-align: center; padding: 0 5px;
  display: none;
}
.nav-badge.show { display: block; }
.sidebar .foot { padding: 14px 18px; border-top: 1px solid rgba(255,255,255,.08); }
.sidebar .foot a { color: #93a29b; font-size: 13px; display: block; margin: 6px 0; text-decoration: none; }
.sidebar .foot a:hover { color: #fff; }
.main-col { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 14px 28px; display: flex; align-items: center; gap: 14px;
}
.topbar h1 { font-size: 16px; margin: 0; flex: 1; font-weight: 600; }
.topbar .who { color: var(--ink-2); font-size: 13px; }
.topbar a { color: var(--accent); font-size: 13px; text-decoration: none; }
main { max-width: 1180px; width: 100%; margin: 0 auto; padding: 24px 28px 60px; }
.page { display: none; }
.page.active { display: block; }
/* ---- 组件 ---- */
.panel {
  background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
  padding: 20px; margin-bottom: 18px;
}
h2 { margin: 0 0 6px; font-size: 16px; font-weight: 600; }
.panel > .muted { margin-top: 0; }
label { display: inline-block; margin: 10px 8px 0 0; font-weight: 600; font-size: 13px; color: var(--ink-2); }
input, select, textarea {
  border: 1px solid var(--border); border-radius: 4px; padding: 7px 10px;
  font-size: 14px; margin-right: 8px; background: #fff; color: var(--ink);
  font-family: inherit;
}
textarea { width: 100%; min-height: 72px; resize: vertical; }
button.act {
  border: 0; border-radius: 4px; background: var(--accent); color: #fff;
  padding: 8px 15px; font-size: 14px; cursor: pointer;
}
button.act:hover { background: var(--accent-hover); }
button.act.secondary { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
button.act.danger { background: transparent; color: var(--danger); border: 1px solid var(--danger); }
button.act.link { background: transparent; color: var(--accent); border: 0; padding: 2px 6px; text-decoration: underline; }
button.act:disabled { background: #b9c4c0; cursor: not-allowed; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--border); }
th { background: #fafaf8; color: var(--ink-2); font-weight: 600; font-size: 13px; }
td { font-variant-numeric: tabular-nums; }
tr.clickable { cursor: pointer; }
tr.clickable:hover td { background: #fafaf8; }
.status {
  display: inline-block; border-radius: 4px; padding: 2px 8px;
  font-size: 12px; font-weight: 600; background: #eef0ee; color: var(--ink-2);
}
.status.WAITING_BUDGET_APPROVAL, .status.WAITING_SAFETY_REVIEW { background: var(--warn-soft); color: var(--warn); }
.status.COMPLETED { background: var(--ok-soft); color: var(--ok); }
.status.FAILED, .status.CORRUPTED { background: #f5e4e1; color: var(--danger); }
.status.RUNNING { background: var(--accent-soft); color: var(--accent); }
.muted { color: var(--ink-2); font-size: 13px; }
.err-text { color: var(--danger); font-weight: 600; }
pre {
  white-space: pre-wrap; background: #20261f; color: #e6e9e3; border-radius: 6px;
  padding: 14px; max-height: 460px; overflow: auto; font-size: 13px;
}
.chart { width: 100%; height: 320px; }
.card { border: 1px solid var(--border); border-radius: 6px; padding: 14px; margin-bottom: 12px; background: var(--surface); }
.card .row { margin: 6px 0; }
.ok { color: var(--ok); font-weight: 600; }
.hidden { display: none !important; }
.kpi-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0 4px; }
.kpi { background: #fafaf8; border: 1px solid var(--border); border-radius: 6px; padding: 8px 16px; font-size: 13px; color: var(--ink-2); }
.kpi strong { display: block; font-size: 19px; color: var(--ink); margin-top: 2px; font-variant-numeric: tabular-nums; }
.table-wrap { overflow-x: auto; }
#approvalList { display: grid; grid-template-columns: repeat(auto-fill, minmax(430px, 1fr)); gap: 12px; }
@media (max-width: 980px) { #approvalList { grid-template-columns: 1fr; } }
.empty { padding: 28px 0; text-align: center; color: var(--ink-2); }
/* ---- 抽屉 ---- */
.drawer-overlay, .modal-overlay {
  position: fixed; inset: 0; background: rgba(28,28,26,.4); z-index: 2000; display: none;
}
.drawer-overlay.show, .modal-overlay.show { display: block; }
.drawer {
  position: fixed; top: 0; right: -680px; width: 660px; max-width: 94vw; height: 100vh;
  background: var(--surface); z-index: 2100; transition: right .22s ease;
  display: flex; flex-direction: column; border-left: 1px solid var(--border);
}
.drawer.show { right: 0; }
.drawer-head { padding: 16px 20px 0; border-bottom: 1px solid var(--border); }
.drawer-head h3 { margin: 0 0 10px; font-size: 15px; }
.drawer-tabs { display: flex; gap: 2px; }
.drawer-tabs button {
  background: transparent; border: 0; padding: 10px 14px; font-size: 14px;
  color: var(--ink-2); cursor: pointer; border-bottom: 2px solid transparent;
}
.drawer-tabs button.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.drawer-body { padding: 16px 20px 40px; overflow-y: auto; flex: 1; }
/* ---- 决策溯源 ---- */
.steps { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 16px; }
.step { border: 1px solid var(--border); border-radius: 4px; padding: 4px 10px; font-size: 12px; color: var(--ink-2); background: #fafaf8; }
.step.done { background: var(--accent-soft); color: var(--accent); border-color: var(--accent); font-weight: 600; }
.step.running { border-color: var(--warn); color: var(--warn); }
.trace-section { margin-bottom: 18px; }
.trace-section h4 { margin: 0 0 8px; font-size: 13px; color: var(--ink-2); font-weight: 600; }
.debate-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.debate-cols .col { border: 1px solid var(--border); border-radius: 6px; padding: 10px; font-size: 13px; }
.debate-cols .col h5 { margin: 0 0 6px; font-size: 13px; }
/* ---- 时间线 ---- */
.timeline { list-style: none; margin: 0; padding: 0; }
.timeline li { position: relative; padding: 0 0 14px 20px; border-left: 1px solid var(--border); margin-left: 6px; }
.timeline li::before {
  content: ""; position: absolute; left: -5px; top: 4px; width: 9px; height: 9px;
  border-radius: 50%; background: var(--accent);
}
.timeline .t { font-size: 12px; color: var(--ink-2); }
/* ---- 弹窗 ---- */
.modal {
  position: fixed; z-index: 2200; top: 50%; left: 50%; transform: translate(-50%, -50%);
  background: var(--surface); border-radius: 6px; width: 680px; max-width: 94vw;
  max-height: 86vh; overflow-y: auto; padding: 22px; display: none;
  border: 1px solid var(--border);
}
.modal.show { display: block; }
.modal h3 { margin: 0 0 14px; font-size: 16px; }
.modal .modal-close { float: right; background: transparent; border: 0; font-size: 18px; cursor: pointer; color: var(--ink-2); }
/* ---- diff ---- */
.diff-head { display: flex; gap: 16px; margin: 0 0 10px; font-size: 13px; color: var(--ink-2); }
.diff-lines { font-family: Consolas, "Courier New", monospace; font-size: 12.5px; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; max-height: 52vh; overflow-y: auto; }
.diff-lines div { padding: 2px 10px; white-space: pre-wrap; word-break: break-all; }
.diff-lines .add { background: var(--ok-soft); color: #24512f; }
.diff-lines .del { background: #f5e4e1; color: #7c2d20; text-decoration: line-through; }
.diff-lines .same { color: var(--ink-2); }
/* ---- toast ---- */
#toastHost { position: fixed; right: 20px; top: 20px; z-index: 3000; display: flex; flex-direction: column; gap: 8px; }
.toast {
  background: var(--ink); color: #fff; border-radius: 6px; padding: 10px 16px;
  font-size: 13px; box-shadow: 0 4px 14px rgba(28,28,26,.25); max-width: 380px;
}
.toast.error { background: var(--danger); }
/* ---- 登录门 ---- */
.admin-gate { position: fixed; inset: 0; z-index: 3000; display: flex; background: var(--bg); }
.gate-brand {
  flex: 1.2; background: var(--sidebar-bg); color: #f4f6f5;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;
  border-right: 1px solid var(--border);
}
.gate-brand .mark {
  width: 52px; height: 52px; background: #2f5d50; color: #fff; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  font-family: "Songti SC", "SimSun", serif; font-weight: 700; font-size: 17px; letter-spacing: 2px;
}
.gate-brand h1 { margin: 0; font-size: 24px; letter-spacing: 2px; font-weight: 600; }
.gate-brand p { margin: 0; color: #93a29b; font-size: 13px; }
.gate-form { width: 420px; max-width: 94vw; background: var(--surface); display: flex; flex-direction: column; justify-content: center; padding: 48px 40px; }
.gate-form h2 { margin-top: 0; }
.gate-form input { width: 100%; }
.gate-form .hint { color: var(--ink-2); font-size: 13px; }
```

- [ ] **步骤 2：整块替换 `#adminApp`（第 263-377 行，即 `<div id="adminApp">` 到其闭合 `</div>`）**

```html
<div id="app" class="hidden">
  <aside class="sidebar">
    <div class="brand">
      <div class="mark">文旅</div>
      <h1>文旅工作台</h1>
      <p>山水有约 · toB 管控端</p>
    </div>
    <nav>
      <button data-page="plans" class="active">方案列表</button>
      <button data-page="approvals">HITL 审核台<span class="nav-badge" id="badgeApprovals"></span></button>
      <button data-page="safety">安全治理看板</button>
      <button data-page="audit">合规审计</button>
      <button data-page="voice">客户之声</button>
      <button data-page="export">白标交付</button>
      <button data-page="stats">经营看板</button>
      <button data-page="customers">客户管理</button>
    </nav>
    <div class="foot">
      <a href="/">游客端 →</a>
      <a href="javascript:void(0)" id="adminLogout">退出登录</a>
    </div>
  </aside>
  <div class="main-col">
    <header class="topbar">
      <h1 id="pageTitle">方案列表</h1>
      <span class="who" id="adminWho"></span>
    </header>
    <main>
      <section class="page active" id="page-plans">
        <div class="panel">
          <h2>方案列表（B1 顾问工作台）</h2>
          <p class="muted">点击任意行打开详情抽屉；操作列可改单、导出。</p>
          <div class="kpi-row" id="planKpis"><span class="kpi">加载中...</span></div>
          <div style="margin-top: 10px">
            <label>状态</label>
            <select id="filterStatus">
              <option value="">全部状态</option>
              <option value="QUEUED">排队中</option>
              <option value="RUNNING">规划中</option>
              <option value="COMPLETED">已完成</option>
              <option value="WAITING_BUDGET_APPROVAL">待预算审批</option>
              <option value="WAITING_SAFETY_REVIEW">待安全审核</option>
              <option value="FAILED">已失败</option>
            </select>
            <label>客户</label>
            <input id="filterCustomer" placeholder="按客户筛选" style="width: 150px" />
            <label>租户</label>
            <input id="filterTenant" placeholder="高级筛选，可留空" style="width: 130px" />
            <label>搜索</label>
            <input id="filterSearch" placeholder="job_id / 目的地关键词" style="width: 200px" />
            <button class="act" id="loadPlans">查询 / 刷新</button>
          </div>
          <div class="table-wrap"><table id="plansTable" style="margin-top: 14px">
            <thead>
              <tr>
                <th>行程</th><th>状态</th><th>进度</th><th>天数</th>
                <th>预算</th><th>客户</th><th>版本</th><th>更新时间</th><th>操作</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table></div>
          <p class="muted" id="plansMeta"></p>
        </div>
      </section>

      <section class="page" id="page-approvals">
        <div class="panel">
          <h2>HITL 审核台（B2）：超预算 / 高风险挂起队列</h2>
          <button class="act secondary" id="loadApprovals">刷新队列</button>
          <div id="approvalList" style="margin-top: 14px"></div>
        </div>
      </section>

      <section class="page" id="page-safety">
        <div class="panel">
          <h2>安全治理看板（B3）：红蓝对抗量化</h2>
          <p class="muted" id="safetyCounters">加载中...</p>
          <div class="chart" id="chartDaily"></div>
          <div class="chart" id="chartAttack"></div>
          <p class="muted">拦截率 = 高风险拦截次数 / 总扫描次数；数据来自本地任务审计日志。</p>
        </div>
      </section>

      <section class="page" id="page-audit">
        <div class="panel">
          <h2>合规审计（B4）：谁 / 何时 / 改了什么</h2>
          <label>Job ID</label>
          <input id="auditJobId" placeholder="plan_xxxxxxxx" style="width: 240px" />
          <button class="act" id="loadAudit">查询审计</button>
          <a class="act secondary" style="text-decoration: none; margin-left: 8px" href="/api/audit/export.csv">导出全量 CSV</a>
          <div id="auditEvents" style="margin-top: 14px"></div>
        </div>
      </section>

      <section class="page" id="page-voice">
        <div class="panel">
          <h2>客户之声：好评 / 投诉聚合</h2>
          <p class="muted">来自本地审计日志聚合（演示级口径）。</p>
          <div class="kpi-row" id="voiceKpis"><span class="kpi">加载中...</span></div>
          <div style="margin-top: 10px">
            <label>类型</label>
            <select id="voiceKind">
              <option value="">全部</option>
              <option value="praise">好评</option>
              <option value="complaint">投诉</option>
            </select>
            <button class="act" id="loadVoice">查询</button>
            <button class="act secondary" id="openFeedbackModal" style="margin-left: 8px">代客记录反馈</button>
          </div>
          <div class="table-wrap"><table id="voiceTable" style="margin-top: 14px">
            <thead><tr><th>时间</th><th>类型</th><th>客户</th><th>行程</th><th>操作人</th><th>内容</th><th>详情</th></tr></thead>
            <tbody></tbody>
          </table></div>
        </div>
      </section>

      <section class="page" id="page-export">
        <div class="panel">
          <h2>白标交付（B5）：企业品牌 + 顾问署名</h2>
          <label>Job ID</label>
          <input id="expJobId" placeholder="plan_xxxxxxxx" style="width: 220px" />
          <label>企业品牌</label>
          <input id="expBrand" value="示例文旅科技有限公司" style="width: 220px" />
          <label>顾问署名</label>
          <input id="expConsultant" value="顾问A" style="width: 140px" />
          <button class="act" id="doExport">生成白标交付文件</button>
          <p class="muted" id="expMeta"></p>
          <pre id="expPreview" class="hidden"></pre>
        </div>
      </section>

      <section class="page" id="page-stats">
        <div class="panel">
          <h2>经营分析看板（B6）：聚合真实任务数据</h2>
          <p class="muted" id="statsMeta">加载中...</p>
          <div class="chart" id="chartDailyCreated"></div>
          <div class="chart" id="chartStatus"></div>
          <div class="chart" id="chartCustomers"></div>
        </div>
      </section>

      <section class="page" id="page-customers">
        <div class="panel">
          <h2>客户管理：按客户聚合方案数据</h2>
          <p class="muted">演示级前端聚合（当前数据窗口内）；点击行查看该客户全部方案。</p>
          <div class="table-wrap"><table id="customersTable" style="margin-top: 8px">
            <thead><tr><th>客户</th><th>方案数</th><th>已完成</th><th>完成率</th><th>待审</th><th>最近活跃</th></tr></thead>
            <tbody></tbody>
          </table></div>
          <p class="muted" id="customersMeta"></p>
        </div>
      </section>
    </main>
  </div>
</div>
```

- [ ] **步骤 3：替换登录门品牌区（`#adminGate` 内 `.gate-brand` 整块）**

```html
      <div class="gate-brand">
        <div class="mark">文旅</div>
        <h1>文旅工作台</h1>
        <p>山水有约 · 多 Agent 文旅系统 · toB 管控端</p>
      </div>
```

同时在 `<body>` 末尾（`#adminApp` 之后）追加抽屉、弹窗与 toast 宿主：

```html
    <div id="drawerOverlay" class="drawer-overlay"></div>
    <aside class="drawer" id="planDrawer">
      <div class="drawer-head">
        <h3 id="drawerTitle">方案详情</h3>
        <div class="drawer-tabs">
          <button data-dtab="plan" class="active">行程书</button>
          <button data-dtab="trace">决策溯源</button>
          <button data-dtab="audit">审计时间线</button>
          <button data-dtab="memory">记忆与干预</button>
          <button class="act link" id="drawerClose" style="margin-left: auto">关闭 ✕</button>
        </div>
      </div>
      <div class="drawer-body">
        <div id="dtab-plan">
          <div id="drawerError" class="err-text hidden" style="margin-bottom: 10px"></div>
          <div id="drawerPlanDiffEntry" class="hidden" style="margin-bottom: 10px">
            <button class="act secondary" id="openDiffBtn">与父版本对比</button>
            <span class="muted" id="drawerParentLabel"></span>
          </div>
          <div id="drawerPlanBody" class="muted">加载中...</div>
        </div>
        <div id="dtab-trace" class="hidden">
          <div class="steps" id="traceSteps"></div>
          <div class="trace-section"><h4>决策辩论（规划方 vs 游客方）</h4><div id="traceDebates" class="muted">加载中...</div></div>
          <div class="trace-section"><h4>反事实对照（放弃 / 换来）</h4><div id="traceCf" class="muted">加载中...</div></div>
          <div class="trace-section"><h4>虚拟游客踩点反馈</h4><div id="traceSwarm" class="muted">加载中...</div></div>
        </div>
        <div id="dtab-audit" class="hidden"><ul class="timeline" id="drawerAuditList"><li class="muted">加载中...</li></ul></div>
        <div id="dtab-memory" class="hidden">
          <div class="empty">记忆中心建设中——共享图记忆与运行态强干预由工单 7 独立批次交付。<br/>届时此处呈现该任务/客户的记忆三元组卡片（过敏禁忌/偏好/约束）与干预历史时间线。</div>
        </div>
      </div>
    </aside>
    <div class="modal-overlay" id="modalOverlay"></div>
    <div class="modal" id="modalReplan">
      <button class="modal-close" data-close="modalReplan">✕</button>
      <h3>改单（增量重规划）</h3>
      <p class="muted" id="replanJobLabel"></p>
      <label>改动需求（自然语言）</label>
      <textarea id="replanRequest" placeholder="例如：预算改为 3000 元，减少打车"></textarea>
      <p class="muted">基于当前版本 v<span id="replanVersion"></span> 提交；目的地/天数/偏好未变时自动增量复用父节点。</p>
      <button class="act" id="submitReplan">提交改单</button>
      <p class="muted" id="replanResult"></p>
    </div>
    <div class="modal" id="modalDiff">
      <button class="modal-close" data-close="modalDiff">✕</button>
      <h3>版本对比 <span class="muted" id="diffTitle" style="font-size: 13px"></span></h3>
      <div class="diff-head" id="diffHead"></div>
      <div class="diff-lines" id="diffLines"></div>
    </div>
    <div class="modal" id="modalFeedback">
      <button class="modal-close" data-close="modalFeedback">✕</button>
      <h3>代客记录反馈</h3>
      <label>Job ID</label><input id="fbJobId" placeholder="plan_xxxxxxxx" style="width: 240px" />
      <label>类型</label>
      <select id="fbKind"><option value="praise">好评</option><option value="complaint">投诉</option></select>
      <label>操作人</label><input id="fbOperator" value="顾问A" style="width: 120px" />
      <label>内容</label><input id="fbContent" placeholder="反馈内容" style="width: 300px" />
      <button class="act" id="submitFeedback">提交反馈</button>
      <p class="muted" id="fbResult"></p>
    </div>
    <div id="toastHost"></div>
```

- [ ] **步骤 4：浏览器验证骨架**

启动后端（`uvicorn app.main:app --reload`），打开 `http://127.0.0.1:8000/b` 登录。
预期：侧边栏 8 项可见、墨绿 active 态；此时除方案列表外多数按钮无数据（脚本尚未接好属正常，下一任务接上）。确认无渐变/霓虹蓝残留。

---

### 任务 8：脚本基础设施（toast / 导航 / 角标 / 认证修复）

**文件：**
- 修改：`frontend/admin.html` 的 `<script>` 块（第 378 行起）

- [ ] **步骤 1：替换脚本头部（第 379-418 行：apiBase 到 `let chartsInited`）**

```js
      const apiBase = localStorage.getItem("apiBase") || (location.protocol === "file:" ? "http://127.0.0.1:8000" : "");
      const $ = (sel) => document.querySelector(sel);
      const authHeaders = () => {
        const token = localStorage.getItem("adminToken");
        return token ? { Authorization: `Bearer ${token}` } : {};
      };
      function apiFetch(url, opts = {}) {
        const headers = Object.assign({ "Content-Type": "application/json" }, authHeaders(), (opts && opts.headers) || {});
        return fetch(url, Object.assign({}, opts, { headers }));
      }
      const STATUS_CN = {
        QUEUED: "排队中", RUNNING: "规划中", WAITING_RATE_LIMIT: "限流等待",
        WAITING_BUDGET_APPROVAL: "待预算审批", WAITING_SAFETY_REVIEW: "待安全审核",
        WAITING_PARSE_REVIEW: "解析待复核", RECOVERY_REQUIRED: "待恢复处理",
        REPLAN_REQUIRED: "需重新规划", COMPLETED: "已完成", FAILED: "已失败", CORRUPTED: "文件异常",
      };
      const NODE_ORDER = ["Researcher", "Planner", "Itinerary", "Validator", "Debate", "Mood", "Reporter"];
      const NODE_CN = {
        Researcher: "调研", Planner: "规划", Itinerary: "行程", Validator: "校验",
        Debate: "辩论", Mood: "心情剧本", Reporter: "行程书",
      };
      function cnStatus(s) { return STATUS_CN[s] || s || "-"; }
      function tripLabel(item) {
        const o = item.origin ? item.origin + " -- " : "";
        return o + (item.destination || "未知");
      }
      function toast(msg, isError = false) {
        const el = document.createElement("div");
        el.className = "toast" + (isError ? " error" : "");
        el.textContent = msg;
        $("#toastHost").appendChild(el);
        setTimeout(() => el.remove(), 3600);
      }
      function esc(s) {
        return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      }
      let chartsInited = false;
      let plansCache = []; // 供客户管理页与搜索复用
```

- [ ] **步骤 2：导航切换 + 页面标题 + 角标轮询（替换原 nav 按钮监听，第 420-431 行）**

```js
      const PAGE_TITLES = {
        plans: "方案列表", approvals: "HITL 审核台", safety: "安全治理看板",
        audit: "合规审计", voice: "客户之声", export: "白标交付",
        stats: "经营看板", customers: "客户管理",
      };
      document.querySelectorAll(".sidebar nav button").forEach((btn) => {
        btn.addEventListener("click", () => {
          document.querySelectorAll(".sidebar nav button").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
          $(`#page-${btn.dataset.page}`).classList.add("active");
          $("#pageTitle").textContent = PAGE_TITLES[btn.dataset.page] || "";
          if (btn.dataset.page === "safety") initCharts();
          if (btn.dataset.page === "approvals") loadApprovals();
          if (btn.dataset.page === "plans") loadPlans();
          if (btn.dataset.page === "stats") loadStats();
          if (btn.dataset.page === "voice") loadVoice();
          if (btn.dataset.page === "customers") loadCustomers();
        });
      });
      async function refreshBadge() {
        try {
          const data = await (await apiFetch(`${apiBase}/api/approvals/pending`)).json();
          const badge = $("#badgeApprovals");
          badge.textContent = data.total;
          badge.classList.toggle("show", data.total > 0);
        } catch (e) { /* 后端未启动时静默 */ }
      }
      setInterval(refreshBadge, 60000);
      let drawerRefreshTimer = null;
      function startDrawerRefresh() {
        clearInterval(drawerRefreshTimer);
        drawerRefreshTimer = setInterval(() => {
          if (!drawerJobId || !$("#planDrawer").classList.contains("show")) return;
          loadDrawerStatus();
          if (!$("#dtab-plan").classList.contains("hidden")) loadDrawerPlan();
          if (!$("#dtab-audit").classList.contains("hidden")) loadDrawerAudit();
        }, 5000);
      }
      function stopDrawerRefresh() {
        clearInterval(drawerRefreshTimer);
        drawerRefreshTimer = null;
      }
      let drawerRefreshTimer = null;
      function startDrawerRefresh() {
        clearInterval(drawerRefreshTimer);
        drawerRefreshTimer = setInterval(() => {
          if (!drawerJobId || !$("#planDrawer").classList.contains("show")) return;
          loadDrawerStatus();
          if (!$("#dtab-plan").classList.contains("hidden")) loadDrawerPlan();
          if (!$("#dtab-audit").classList.contains("hidden")) loadDrawerAudit();
        }, 5000);
      }
      function stopDrawerRefresh() {
        clearInterval(drawerRefreshTimer);
        drawerRefreshTimer = null;
      }
```

- [ ] **步骤 3：四处裸 fetch 改 apiFetch（修复 AUTH_ENABLED=true 下 401）**

- `decide()` 中 `await fetch(\`${apiBase}/api/plans/${item.job_id}/approval\`` 改为 `await apiFetch(...)`，并删除其手工 `headers: { "Content-Type": "application/json" }`（apiFetch 已带）；审批成功后加 `toast("已批准并继续"); refreshBadge();`，失败分支的 `alert(...)` 改为 `toast(..., true)`。
- `loadAudit()` 中 `const resp = await fetch(...)` 改为 `await apiFetch(...)`。
- `submitFeedback()` 中 `await fetch(...)` 改为 `await apiFetch(...)`，成功后 `toast("反馈已记录并落审计日志。")`。
- `doExport()` 的认证头修复**合并进任务 14 的整函数替换**，本步骤不改它，避免同一函数改两遍。

- [ ] **步骤 4：登录门与启动逻辑更新（替换文件末尾 `$("#loadPlans"...` 到 `loadSafety();` 的绑定区）**

```js
      $("#loadPlans").addEventListener("click", loadPlans);
      $("#loadApprovals").addEventListener("click", loadApprovals);
      $("#loadAudit").addEventListener("click", loadAudit);
      $("#submitFeedback").addEventListener("click", submitFeedback);
      $("#doExport").addEventListener("click", doExport);
      $("#loadVoice").addEventListener("click", loadVoice);
      $("#openFeedbackModal").addEventListener("click", () => openModal("modalFeedback"));

      function openModal(id) { $("#" + id).classList.add("show"); $("#modalOverlay").classList.add("show"); }
      function closeModal(id) { $("#" + id).classList.remove("show"); $("#modalOverlay").classList.remove("show"); }
      document.querySelectorAll("[data-close]").forEach((btn) =>
        btn.addEventListener("click", () => closeModal(btn.dataset.close))
      );
      $("#modalOverlay").addEventListener("click", () => {
        document.querySelectorAll(".modal.show").forEach((m) => m.classList.remove("show"));
        $("#modalOverlay").classList.remove("show");
      });

      // ---- 工作台登录门禁 ----
      function showGateIfNeeded() {
        if (!localStorage.getItem("adminToken")) {
          document.querySelector("#adminGate").classList.remove("hidden");
          document.querySelector("#app").classList.add("hidden");
        } else {
          document.querySelector("#adminGate").classList.add("hidden");
          document.querySelector("#app").classList.remove("hidden");
          document.querySelector("#adminWho").textContent = localStorage.getItem("adminName") || "管理员";
        }
      }
      document.querySelector("#adminLoginBtn").addEventListener("click", async () => {
        const errorBox = document.querySelector("#adminAuthError");
        errorBox.textContent = "";
        try {
          const resp = await apiFetch(`${apiBase}/api/auth/login`, {
            method: "POST",
            body: JSON.stringify({
              realm: "tob",
              username: document.querySelector("#adminUser").value.trim(),
              password: document.querySelector("#adminPass").value,
            }),
          });
          const data = await resp.json();
          if (!resp.ok) { errorBox.textContent = data.detail || "登录失败"; return; }
          localStorage.setItem("adminToken", data.token);
          localStorage.setItem("adminName", data.name);
          showGateIfNeeded();
          loadPlans();
          refreshBadge();
        } catch (err) {
          errorBox.textContent = "网络异常，请确认后端已启动";
        }
      });
      document.querySelector("#adminLogout").addEventListener("click", () => {
        localStorage.removeItem("adminToken");
        localStorage.removeItem("adminName");
        location.reload();
      });
      showGateIfNeeded();
      loadPlans();
      loadSafety();
      refreshBadge();
```

注意：登录请求原来用裸 fetch + 手工 Content-Type，这里统一走 apiFetch（Content-Type 已内置），删除原 `headers` 行。

- [ ] **步骤 5：浏览器验证**

刷新 `/b`：8 页签切换正常、标题联动；审核台有挂起任务时角标显示数字；执行一次审批不再 401 且出现 toast；`alert` 不再出现。

---

### 任务 9：方案列表增强（操作列 / 搜索 / 失败红标 / plansCache）

**文件：**
- 修改：`frontend/admin.html`（`loadPlans` 函数整体替换，第 433-476 行）

- [ ] **步骤 1：替换 `loadPlans` 为下述实现**

```js
      function planRowActions(item) {
        return `
          <button class="act link" data-op="detail" data-job="${item.job_id}">详情</button>
          <button class="act link" data-op="replan" data-job="${item.job_id}" data-version="${item.version}">改单</button>
          <button class="act link" data-op="export" data-job="${item.job_id}">导出</button>`;
      }
      async function loadPlans() {
        const status = $("#filterStatus").value;
        const customer = $("#filterCustomer").value.trim();
        const tenant = $("#filterTenant").value.trim();
        const params = new URLSearchParams({ limit: "500" });
        if (status) params.set("status", status);
        if (customer) params.set("customer", customer);
        if (tenant) params.set("tenant", tenant);
        const data = await (await apiFetch(`${apiBase}/api/plans?${params}`)).json();
        plansCache = data.items;
        renderPlansTable(plansCache);
        apiFetch(`${apiBase}/api/stats/overview`)
          .then((r) => r.json())
          .then((s) => {
            const pending = s.status_distribution.filter(([k]) => k.startsWith("WAITING")).reduce((a, [, v]) => a + v, 0);
            const running = (s.status_distribution.find(([k]) => k === "RUNNING") || [null, 0])[1];
            const rate = s.completed_rate === null ? "-" : (s.completed_rate * 100).toFixed(1) + "%";
            $("#planKpis").innerHTML = [
              ["任务总量", s.total], ["完成率", rate], ["挂起待审", pending], ["执行中", running],
            ].map(([k, v]) => `<span class="kpi">${k}<strong>${v}</strong></span>`).join("");
          })
          .catch(() => {
            $("#planKpis").innerHTML = '<span class="kpi">统计加载失败，点击"查询 / 刷新"重试</span>';
          });
      }
      function renderPlansTable(items) {
        const kw = ($("#filterSearch").value || "").trim().toLowerCase();
        const filtered = kw
          ? items.filter((it) =>
              [it.job_id, it.destination, it.customer, it.origin]
                .some((v) => String(v || "").toLowerCase().includes(kw)))
          : items;
        const tbody = $("#plansTable tbody");
        tbody.innerHTML = "";
        if (!filtered.length) {
          tbody.innerHTML = `<tr><td colspan="9"><div class="empty">没有符合条件的方案</div></td></tr>`;
        }
        for (const item of filtered) {
          const row = document.createElement("tr");
          row.className = "clickable";
          const failed = item.status === "FAILED" || item.status === "CORRUPTED";
          row.innerHTML = `
            <td><div>${esc(tripLabel(item))}</div><div class="muted" style="font-size: 12px">${esc(item.job_id)}</div></td>
            <td><span class="status ${item.status}" ${failed ? `title="${esc(item.error || "")}"` : ""}>${cnStatus(item.status)}</span></td>
            <td>${item.progress}%</td>
            <td>${item.days ?? "-"}</td>
            <td>${item.budget ?? "-"}</td>
            <td>${esc(item.customer || "-")}</td>
            <td>v${item.version}</td>
            <td>${(item.updated_at || "").slice(0, 19).replace("T", " ")}</td>
            <td>${planRowActions(item)}</td>`;
          row.addEventListener("click", (e) => {
            if (e.target.closest("button")) return;
            openDrawer(item.job_id);
          });
          tbody.appendChild(row);
        }
        $("#plansMeta").textContent = `共 ${filtered.length} 条方案（窗口内 ${items.length} 条）`;
      }
```

- [ ] **步骤 2：绑定搜索与操作列事件（追加到任务 8 的绑定区）**

```js
      $("#filterSearch").addEventListener("input", () => renderPlansTable(plansCache));
      $("#plansTable").addEventListener("click", (e) => {
        const btn = e.target.closest("button[data-op]");
        if (!btn) return;
        const job = btn.dataset.job;
        if (btn.dataset.op === "detail") openDrawer(job);
        if (btn.dataset.op === "replan") openReplanModal(job, Number(btn.dataset.version));
        if (btn.dataset.op === "export") {
          $("#expJobId").value = job;
          document.querySelector('[data-page="export"]').click();
        }
      });
```

- [ ] **步骤 3：浏览器验证**

列表出现操作列；搜索"北京"即时过滤；点行打开抽屉会因 `openDrawer` 未定义而报错——属预期（下一任务实现）；改单/导出按钮同理。确认失败任务红标与 title 提示。

---

### 任务 10：方案详情抽屉（行程书 / 决策溯源 / 审计）

**文件：**
- 修改：`frontend/admin.html`（`<script>` 内追加模块）

- [ ] **步骤 1：先核对三个体验接口的真实响应字段名**

对任一已完成任务执行（或从 toC 页 DevTools Network 面板观察）：

```bash
curl -s http://127.0.0.1:8000/api/plans/{已完成job_id}/debates | python -m json.tool | head -40
curl -s http://127.0.0.1:8000/api/plans/{已完成job_id}/counterfactual | python -m json.tool | head -30
curl -s http://127.0.0.1:8000/api/plans/{已完成job_id}/swarm | python -m json.tool | head -30
```

把三个响应的"论点列表字段、对照卡字段、游客反馈字段"的真实名字记下来——下面步骤 2 的渲染代码在标注 `<!-- 字段以实测为准 -->` 的三处使用的是推测名，必须按实测结果替换，兜底链顺序保持不变。

- [ ] **步骤 2：追加抽屉逻辑**

```js
      // ---- 方案详情抽屉 ----
      let drawerJobId = null;
      const drawerTabsLoaded = new Set();
      function openDrawer(jobId) {
        drawerJobId = jobId;
        drawerTabsLoaded.clear();
        $("#drawerTitle").textContent = `方案详情 · ${jobId}`;
        $("#drawerError").classList.add("hidden");
        switchDrawerTab("plan");
        $("#planDrawer").classList.add("show");
        $("#drawerOverlay").classList.add("show");
        loadDrawerStatus().then(() => loadDrawerPlan());
      }
      function closeDrawer() {
        $("#planDrawer").classList.remove("show");
        $("#drawerOverlay").classList.remove("show");
      }
      $("#drawerClose").addEventListener("click", closeDrawer);
      $("#drawerOverlay").addEventListener("click", closeDrawer);
      document.querySelectorAll(".drawer-tabs button[data-dtab]").forEach((btn) =>
        btn.addEventListener("click", () => switchDrawerTab(btn.dataset.dtab))
      );
      function switchDrawerTab(tab) {
        document.querySelectorAll(".drawer-tabs button[data-dtab]").forEach((b) =>
          b.classList.toggle("active", b.dataset.dtab === tab));
        ["plan", "trace", "audit", "memory"].forEach((t) =>
          $(`#dtab-${t}`).classList.toggle("hidden", t !== tab));
        if (!drawerJobId) return;
        if (tab === "trace" && !drawerTabsLoaded.has("trace")) { drawerTabsLoaded.add("trace"); loadDrawerTrace(); }
        if (tab === "audit" && !drawerTabsLoaded.has("audit")) { drawerTabsLoaded.add("audit"); loadDrawerAudit(); }
      }
      async function loadDrawerStatus() {
        const data = await (await apiFetch(`${apiBase}/api/plans/${drawerJobId}`)).json();
        if (data.error) {
          $("#drawerError").textContent = `任务异常：${data.error}`;
          $("#drawerError").classList.remove("hidden");
        }
        renderTraceSteps(data);
        if (data.parent_job_id) {
          $("#drawerPlanDiffEntry").classList.remove("hidden");
          $("#drawerParentLabel").textContent = `父版本 ${data.parent_job_id}`;
          $("#openDiffBtn").dataset.parent = data.parent_job_id;
        } else {
          $("#drawerPlanDiffEntry").classList.add("hidden");
        }
      }
      function renderTraceSteps(status) {
        const done = new Set(status.completed_nodes || []);
        const orderIdx = Object.fromEntries(NODE_ORDER.map((n, i) => [n, i]));
        const current = status.current_agent;
        const resumeIdx = status.resume_from ? orderIdx[status.resume_from] : null;
        const allDone = status.status === "COMPLETED";
        $("#traceSteps").innerHTML = NODE_ORDER.map((node) => {
          let cls = "";
          if (allDone || done.has(node)) cls = "done";
          else if (node === current || (resumeIdx !== null && orderIdx[node] >= resumeIdx && status.status.startsWith("WAITING") === false && orderIdx[node] === resumeIdx)) cls = "running";
          return `<span class="step ${cls}">${NODE_CN[node]}</span>`;
        }).join("");
      }
      async function loadDrawerPlan() {
        $("#drawerPlanBody").innerHTML = `<span class="muted">加载中...</span>`;
        const resp = await apiFetch(`${apiBase}/api/plans/${drawerJobId}/result`);
        if (!resp.ok) {
          $("#drawerPlanBody").innerHTML = `<div class="empty">行程书尚未生成（任务未完成或已失败）</div>`;
          return;
        }
        const data = await resp.json();
        $("#drawerPlanBody").innerHTML = mdToHtml(data.travel_plan_md || "");
      }
      function mdToHtml(md) {
        const lines = esc(md).split(/\r?\n/);
        const out = [];
        let inList = false;
        for (const line of lines) {
          const h = line.match(/^(#{1,4})\s+(.*)$/);
          const li = line.match(/^\s*[-*]\s+(.*)$/);
          if (li) { if (!inList) { out.push("<ul>"); inList = true; } out.push(`<li>${li[1]}</li>`); continue; }
          if (inList) { out.push("</ul>"); inList = false; }
          if (h) { out.push(`<h${h[1].length + 1} style="margin:14px 0 6px">${h[2]}</h${h[1].length + 1}>`); continue; }
          if (!line.trim()) { out.push("<div style='height:6px'></div>"); continue; }
          out.push(`<p style="margin:4px 0">${line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")}</p>`);
        }
        if (inList) out.push("</ul>");
        return out.join("");
      }
      async function loadDrawerTrace() {
        const safe = (sel) => { const el = $(sel); el.classList.remove("muted"); return el; };
        const debates = await apiFetch(`${apiBase}/api/plans/${drawerJobId}/debates`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
        const plannerPts = debates?.planner_points || debates?.planning_side || [];   <!-- 字段以实测为准 -->
        const travelerPts = debates?.traveler_points || debates?.traveler_side || []; <!-- 字段以实测为准 -->
        if (plannerPts.length || travelerPts.length) {
          safe("#traceDebates").innerHTML = `
            <div class="debate-cols">
              <div class="col"><h5>规划方</h5>${plannerPts.map((p) => `<div>· ${esc(typeof p === "string" ? p : p.point || JSON.stringify(p))}</div>`).join("")}</div>
              <div class="col"><h5>游客方</h5>${travelerPts.map((p) => `<div>· ${esc(typeof p === "string" ? p : p.point || JSON.stringify(p))}</div>`).join("")}</div>
            </div>
            ${debates.final_tradeoff || debates.final ? `<p class="muted">最终取舍：${esc(debates.final_tradeoff || debates.final)}</p>` : ""}`;
        } else safe("#traceDebates").innerHTML = `<div class="empty">本任务未生成该部分</div>`;
        const cf = await apiFetch(`${apiBase}/api/plans/${drawerJobId}/counterfactual`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
        const cfCards = cf?.cards || cf?.items || [];                                  <!-- 字段以实测为准 -->
        safe("#traceCf").innerHTML = cfCards.length
          ? cfCards.map((c) => `<div class="card"><div class="row"><strong>${esc(c.gave_up || c.dropped || c.title || "放弃项")}</strong></div><div class="row muted">${esc(c.trade_for || c.gained || c.detail || "")}</div></div>`).join("")
          : `<div class="empty">本任务未生成该部分</div>`;
        const swarm = await apiFetch(`${apiBase}/api/plans/${drawerJobId}/swarm`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
        const swarmItems = swarm?.feedbacks || swarm?.items || swarm?.agents || [];    <!-- 字段以实测为准 -->
        safe("#traceSwarm").innerHTML = swarmItems.length
          ? swarmItems.map((s) => `<div class="card"><div class="row"><strong>${esc(s.persona || s.name || "虚拟游客")}</strong></div><div class="row muted">${esc(s.feedback || s.comment || s.summary || "")}</div></div>`).join("")
          : `<div class="empty">本任务未生成该部分</div>`;
      }
      async function loadDrawerAudit() {
        const resp = await apiFetch(`${apiBase}/api/plans/${drawerJobId}/audit`);
        const box = $("#drawerAuditList");
        if (!resp.ok) { box.innerHTML = `<li class="muted">查询失败：HTTP ${resp.status}</li>`; return; }
        const data = await resp.json();
        box.innerHTML = data.events.length
          ? data.events.map((e) => `<li><div>${esc(e.action || "")} · ${esc(e.operator || "-")}</div><div class="t">${esc((e.created_at || "").slice(0, 19).replace("T", " "))}</div></li>`).join("")
          : `<li class="muted">暂无审计事件</li>`;
      }
```

- [ ] **步骤 3：按实测字段核对渲染代码**

若步骤 1 实测的字段名与步骤 2 代码中标注 `<!-- 字段以实测为准 -->` 的兜底链不一致，把实测字段插入各兜底链首位；若"反事实/虚拟游客/辩论"始终显示"未生成"，回到 Network 面板核对字段名后重试。缺省文案行为不变。

- [ ] **步骤 4：浏览器验证**

点击列表任意行：抽屉滑出；行程书页签渲染全文；溯源页签显示节点步骤条（增量复用任务应出现复用节点的 done 态）+ 三块内容或"未生成"缺省文案；审计页签为垂直时间线。点遮罩/关闭可退出。

---

### 任务 11：改单弹窗 + 版本 diff 视图

**文件：**
- 修改：`frontend/admin.html`（`<script>` 内追加模块；绑定区补两个监听）

- [ ] **步骤 1：追加改单与 diff 逻辑**

```js
      // ---- 改单（增量重规划）----
      function openReplanModal(jobId, version) {
        $("#replanJobLabel").textContent = jobId;
        $("#replanVersion").textContent = version || 1;
        $("#replanRequest").value = "";
        $("#replanResult").textContent = "";
        openModal("modalReplan");
      }
      $("#submitReplan").addEventListener("click", async () => {
        const change = $("#replanRequest").value.trim();
        if (!change) { toast("请填写改动需求", true); return; }
        const resp = await apiFetch(`${apiBase}/api/plans/${$("#replanJobLabel").textContent}/replan`, {
          method: "POST",
          body: JSON.stringify({ change_request: change, base_version: Number($("#replanVersion").textContent) }),
        });
        const data = await resp.json();
        if (!resp.ok) { toast(`改单失败：${data.detail || resp.status}`, true); return; }
        $("#replanResult").textContent = `已创建新任务 ${data.job_id}（模式：${data.replan_mode}）`;
        toast(`改单已提交：${data.job_id}`);
        closeModal("modalReplan");
        loadPlans();
        setTimeout(() => openDrawer(data.job_id), 400);
      });

      // ---- 版本 diff ----
      $("#openDiffBtn").addEventListener("click", async () => {
        const job = drawerJobId;
        const resp = await apiFetch(`${apiBase}/api/plans/${job}/diff`);
        const data = await resp.json();
        if (!resp.ok) { toast(`对比失败：${data.detail || resp.status}`, true); return; }
        $("#diffTitle").textContent = `${data.parent_job_id} → ${job}`;
        $("#diffHead").innerHTML = `<span>新增 <strong class="ok">${data.added}</strong> 行</span><span>删除 <strong class="err-text">${data.removed}</strong> 行</span><span>保留 ${data.unchanged} 行</span>${data.truncated ? '<span class="err-text">内容过长已截断</span>' : ""}`;
        $("#diffLines").innerHTML = data.lines
          .map((l) => `<div class="${l.type}">${esc(l.text) || "&nbsp;"}</div>`)
          .join("");
        openModal("modalDiff");
      });
```

- [ ] **步骤 2：浏览器验证**

对已完成任务点"改单"：提交"预算改为 3000 元，减少打车"→ toast → 列表刷新 → 自动打开新任务抽屉；等新任务完成后点"与父版本对比"：红绿行与统计数字正确；对非改单任务确认不显示对比按钮。

---

### 任务 12：客户管理页

**文件：**
- 修改：`frontend/admin.html`（`<script>` 内追加）

- [ ] **步骤 1：追加聚合逻辑**

```js
      // ---- 客户管理（演示级前端聚合）----
      async function loadCustomers() {
        const data = await (await apiFetch(`${apiBase}/api/plans?limit=500`)).json();
        const groups = new Map();
        for (const it of data.items) {
          const key = it.customer || "未归属";
          const g = groups.get(key) || { name: key, total: 0, completed: 0, pending: 0, last: "" };
          g.total += 1;
          if (it.status === "COMPLETED") g.completed += 1;
          if (String(it.status).startsWith("WAITING")) g.pending += 1;
          if ((it.updated_at || "") > g.last) g.last = it.updated_at || "";
          groups.set(key, g);
        }
        const rows = [...groups.values()].sort((a, b) => b.total - a.total);
        const tbody = $("#customersTable tbody");
        tbody.innerHTML = rows.length
          ? rows.map((g) => `
              <tr class="clickable" data-customer="${esc(g.name)}">
                <td><strong>${esc(g.name)}</strong></td>
                <td>${g.total}</td><td>${g.completed}</td>
                <td>${g.total ? ((g.completed / g.total) * 100).toFixed(0) + "%" : "-"}</td>
                <td>${g.pending}</td>
                <td>${g.last.slice(0, 19).replace("T", " ") || "-"}</td>
              </tr>`).join("")
          : `<tr><td colspan="6"><div class="empty">暂无客户数据</div></td></tr>`;
        $("#customersMeta").textContent = `共 ${rows.length} 个客户（窗口内 ${data.items.length} 条方案）`;
      }
      $("#customersTable").addEventListener("click", (e) => {
        const tr = e.target.closest("tr[data-customer]");
        if (!tr) return;
        $("#filterCustomer").value = tr.dataset.customer === "未归属" ? "" : tr.dataset.customer;
        document.querySelector('[data-page="plans"]').click();
        loadPlans();
      });
```

- [ ] **步骤 2：浏览器验证**

有带 `customer` 提交的任务时（可在 toC 用"客户归属"提交一单）：客户行聚合数字正确；点击行跳回方案列表并带客户筛选。

---

### 任务 13：客户之声页

**文件：**
- 修改：`frontend/admin.html`（`<script>` 内追加；确认原审计页的反馈表单 HTML 已在任务 7 移除）

- [ ] **步骤 1：追加列表逻辑**

```js
      // ---- 客户之声 ----
      async function loadVoice() {
        const kind = $("#voiceKind").value;
        const params = new URLSearchParams({ limit: "200" });
        if (kind) params.set("kind", kind);
        const data = await (await apiFetch(`${apiBase}/api/feedbacks?${params}`)).json();
        $("#voiceKpis").innerHTML = [
          ["好评", data.praise_count], ["投诉", data.complaint_count], ["合计", data.praise_count + data.complaint_count],
        ].map(([k, v]) => `<span class="kpi">${k}<strong>${v}</strong></span>`).join("");
        const tbody = $("#voiceTable tbody");
        tbody.innerHTML = data.items.length
          ? data.items.map((it) => `
              <tr>
                <td>${esc((it.created_at || "").slice(0, 19).replace("T", " "))}</td>
                <td>${it.kind === "complaint" ? '<span class="err-text">投诉</span>' : '<span class="ok">好评</span>'}</td>
                <td>${esc(it.customer || "-")}</td>
                <td>${esc(it.destination || "-")}</td>
                <td>${esc(it.operator || "-")}</td>
                <td>${esc(it.content || "-")}</td>
                <td><button class="act link" data-vjob="${esc(it.job_id)}">查看任务</button></td>
              </tr>`).join("")
          : `<tr><td colspan="7"><div class="empty">暂无反馈记录</div></td></tr>`;
      }
      $("#voiceTable").addEventListener("click", (e) => {
        const btn = e.target.closest("button[data-vjob]");
        if (!btn) return;
        openDrawer(btn.dataset.vjob);
      });
```

- [ ] **步骤 2：浏览器验证**

在弹窗里对一个已完成任务记录一条好评：列表即时（重新点"查询"）出现该行，计数卡 +1；类型筛选生效；"查看任务"打开抽屉。确认原审计页已无反馈表单。

---

### 任务 14：白标交付页修复

**文件：**
- 修改：`frontend/admin.html`（`doExport` 函数替换）

- [ ] **步骤 1：替换 `doExport`**

```js
      async function doExport() {
        const jobId = $("#expJobId").value.trim();
        if (!jobId) return;
        const resp = await apiFetch(`${apiBase}/api/plans/${jobId}/export`, {
          method: "POST",
          body: JSON.stringify({
            brand: $("#expBrand").value || "企业品牌",
            consultant: $("#expConsultant").value || "顾问",
          }),
        });
        const data = await resp.json();
        if (!resp.ok) {
          $("#expMeta").textContent = `导出失败：HTTP ${resp.status}（${data.detail || ""}）`;
          toast(`导出失败：${data.detail || resp.status}`, true);
          return;
        }
        $("#expMeta").innerHTML = `已生成 <strong>${esc(data.file)}</strong>（sha256 ${esc(String(data.sha256).slice(0, 16))}…），交付记录已落审计。`;
        const preview = $("#expPreview");
        preview.classList.remove("hidden");
        preview.textContent = data.markdown;
        toast("白标交付文件已生成");
      }
```

- [ ] **步骤 2：浏览器验证**

对已完成任务导出：元信息与预览全文可见（旧 bug 的 `display:none` 已随任务 7 重构消除，此处确认）；预览首部出现"中立声明"行。

---

### 任务 15：全链路回归 + 文档同步

**文件：**
- 修改：`README.md`、`接口文档.md`

- [ ] **步骤 1：后端回归**

```bash
cd backend
python -m compileall app scripts
python -m pytest tests -q
PYTHONIOENCODING=utf-8 python scripts/smoke_test.py
```
预期：全绿。

- [ ] **步骤 2：浏览器全链路验收（按规格 §8.3）**

登录 `/b` 后依次验证：① 列表 → 详情抽屉四页签（"记忆与干预"显示建设空态）；② 改单 → 新任务 diff 红绿可见；③ 代客记录反馈 → 客户之声出现；④ 白标导出预览含中立声明；⑤ 角标随挂起任务出现/消失；⑥ `AUTH_ENABLED=true` 重启后端后，审批/审计/反馈/导出四操作不 401（验证后记得关回）。

- [ ] **步骤 3：同步《接口文档.md》**

在接口清单中追加：

```markdown
### 客户之声聚合
- `GET /api/feedbacks?kind=&customer=&limit=`：从各任务审计日志聚合反馈事件（好评/投诉）。响应：`total / praise_count / complaint_count / items[]`（item 含 job_id、created_at、kind、operator、content、customer、destination）。挂 toB 管理守卫。

### 版本对比
- `GET /api/plans/{job_id}/diff?base=`：子任务与父任务 travel_plan.md 的行级 diff（difflib，上限 2000 行，`truncated` 标注截断）。非重规划任务返回 400 `NOT_A_REPLAN`。同时 `GET /api/plans/{job_id}` 响应新增 `parent_job_id`、`completed_nodes` 字段。
```

- [ ] **步骤 4：同步 README.md**

"当前已实现"的 toB 条目替换为：

```markdown
- toB 企业端工作台（`/b`）：侧边栏八页签——方案列表（行内操作/搜索/失败红标）、HITL 审核台（待审角标）、安全治理看板、合规审计、客户之声（反馈聚合）、白标交付（含中立声明）、经营看板、客户管理（演示级前端聚合）；方案详情抽屉（行程书/决策溯源/审计时间线）与改单+父子版本行级 diff。
```

演示脚本追加第 6 条：

```markdown
6. 决策溯源 + 版本对比：toB 工作台点开已完成方案 → 抽屉"决策溯源"看节点步骤条与辩论双栏 → 对改单子任务点"与父版本对比"看行级红绿 diff。
```

- [ ] **步骤 5：最终视觉复核**

对照规格 §3 逐项确认：无 `#38bdf8` 残留、无渐变按钮/发光/倾斜徽标、单一墨绿强调色、KPI 数字 tabular 对齐、空状态文案齐全。

---

## 覆盖检查

- 规格§3 视觉系统 → 任务 7、15
- 规格§4 信息架构/角标 → 任务 7、8
- 规格§5.1 列表增强 → 任务 9
- 规格§5.2 详情抽屉/溯源 → 任务 10（含"记忆与干预"空态挂载点，工单 7 主体另立批次，见《工单要点提取与落点映射.md》）
- 规格§5.3 改单+diff → 任务 11（依赖任务 2、3）
- 规格§5.4 客户管理 → 任务 12
- 规格§5.5 客户之声 → 任务 13（依赖任务 4）
- 规格§5.6 白标 → 任务 14（依赖任务 5）
- 规格§6 后端四处 → 任务 1、2、3、4、5
- 规格§7 认证修复 → 任务 8
- 规格§8 验证 → 任务 6、15
- 规格§9 诚实口径 → 任务 12/13 页面标注 + 15 复核
