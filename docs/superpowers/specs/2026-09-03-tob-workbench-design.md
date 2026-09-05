# toB 企业端工作台改造 · 设计规格

> 版本：v1.0 ｜ 日期：2026-09-03 ｜ 状态：已获用户批准的设计方向（方案 A）
> 上位文档：《竞品调研报告_AI旅行规划》§5.2/§6.2-6.5、《落地实施方案_真实呈现版》批次 3

## 1. 背景与目标

toC 端已完成对话式规划与水墨主题的大版本升级，toB 工作台（`frontend/admin.html`）自 8 月 30 日后未再演进，体验停留在基础版。竞品调研给出三个明确信号：

1. **可解释性是本方唯一 5 分维度**（Agent 级留痕/辩论/溯源），但后端已有的 `/debates`、`/counterfactual`、`/swarm`、`/audit` 接口在 toB 工作台零呈现——最强差异化卖点没有 UI 落点。
2. **改单 + 版本 diff** 承诺过未实现（批次 3 B1），后端 `/replan` 已返回 `diff_summary` 与 `parent_job_id`。
3. **审计页的反馈表单形态是反的**（顾问替客户填好评/投诉），应改为"客户之声"聚合视图。

**目标**：一次改造同时完成——体验翻新（去 AI 味的专业后台风）、功能补齐（详情抽屉/改单 diff/客户管理/客户之声/角标与行内操作）、差异化叙事落地（决策溯源视图、中立声明）。

## 2. 范围

**做**：admin.html 全量重构（视觉 + 信息架构 + 新功能）；后端 4 处最小改动（见 §6）；修复 4 处漏带认证头的前端调用。

**不做**（明确排除）：
- "算得准"预算超支 bug 修复（`recommend_hotel` 未按人数放大交通成本）——独立批次，不混入本次。
- 顾问对话式下单（用户明确未选）。
- **工单 7 主体**（共享图记忆引擎、Memory Mutator 强干预 API、Neo4j/图存储、竞态审计报告）——按《工单要点提取与落点映射.md》§3 独立成批（约 3 人日）；本批次仅在详情抽屉预留"记忆与干预"页签挂载点（空态标注"记忆中心建设中"），不做任何记忆后端。
- MCP 开放集成、真实供应链接入（结构性差距，非本批能解决）。
- 前端框架迁移（保持原生单文件 HTML，沿用现有 vanilla 模式）。
- toC 端任何改动。

## 3. 视觉系统：去 AI 味专业后台风

**删除清单**：霓虹天蓝 `#38bdf8` 强调色（nav 下划线、登录门边框、徽标渐变）；`.brand-mark` 的渐变+`rotate(-5deg)`+发光阴影；头部与登录门品牌区的渐变背景；过大的圆角（12px+）与弥散阴影。

**设计 tokens**（CSS 变量）：

| token | 值 | 用途 |
|---|---|---|
| `--bg` | `#f7f7f5` | 页面底色（暖灰白） |
| `--surface` | `#ffffff` | 卡片 |
| `--border` | `#e4e4e0` | 1px 细边框（替代阴影） |
| `--ink` | `#1c1c1a` | 主文字（近黑墨色） |
| `--ink-2` | `#6f6f6a` | 次级文字 |
| `--accent` | `#2f5d50` | 唯一强调色（墨绿，呼应"山水有约"） |
| `--accent-hover` | `#254a40` | 强调色 hover |
| `--danger` | `#b04a3a` | 失败/驳回（低饱和红） |
| `--warn` | `#9a6b2f` | 待审批（低饱和琥珀） |

状态 pill：小圆角（4px）、浅底深字、无渐变，语义色沿用现有 STATUS 分类但降饱和。数字统一 `font-variant-numeric: tabular-nums`。登录门：纯色深墨绿（`#16211d`）分栏，方形印章式徽标（无倾斜无发光），保留演示账号提示。侧边栏深墨绿底、白字、active 项左侧 3px 墨绿竖线。全局 toast 组件替代 `alert()`；每个列表/看板补空状态文案（如"当前没有挂起任务"已有，其余页面对齐）。

## 4. 信息架构：顶部导航改左侧边栏

固定左侧边栏（约 200px，含品牌区 + 8 项导航 + 底部退出/游客端链接），右侧内容区自适应（max-width 保持 1180px 居中）：

1. 方案列表 2. HITL 审核台（**角标**：待审数，来自 `/api/approvals/pending` 的 total，页面加载、审批操作后、60s 定时轮询更新） 3. 安全治理看板 4. 合规审计 5. 客户之声（新） 6. 白标交付 7. 经营看板 8. 客户管理（新）

审计页移除"客户反馈通道"表单，其"代客记录"能力并入客户之声页（轻量按钮 + 弹窗，调原 `POST /api/plans/{id}/feedback`）。

## 5. 功能设计

### 5.1 方案列表增强

- **操作列**（新增，行尾）：详情 / 改单 / 导出三个文字按钮。
- **全局搜索框**：前端过滤（job_id / 目的地 / 客户 包含匹配），在现有 100 条 limit 内，不加后端参数。
- **失败可见**：FAILED/解析待复核行内红标；错误详情进抽屉（列表接口已有 `error` 字段，前端透出即可）。
- **租户筛选**降为高级筛选，与客户同行（保留 B7 演示能力，减少首屏噪音）。
- KPI 行保留。

### 5.2 方案详情抽屉（核心新增）

右侧滑出抽屉（约 640px，遮罩点击关闭），三个页签，数据**懒加载**（打开页签时才请求）：

- **① 行程书**：`GET /api/plans/{id}/result` 渲染 `travel_plan_md` 全文（Markdown 转 HTML，保留辩论/翻车预演等全部章节——toB 顾问需要看全量）。失败任务此页签显示 error。
- **② 决策溯源**（差异化主战场）：
  - Agent 节点步骤条：调研→规划→行程→校验→辩论→心情剧本→行程书（复用 NODE_CN 映射）；节点状态由状态接口的 `completed_nodes`（schema 补字段，见 §6）+ `resume_from` + `current_agent` 推导：已完成（墨绿实心）/进行中（描边）/待执行（灰）。
  - 决策辩论双栏：`GET /api/plans/{id}/debates` 规划方 vs 游客方论点 + 最终取舍。
  - 反事实对照卡：`GET /api/plans/{id}/counterfactual`。
  - 虚拟游客踩点：`GET /api/plans/{id}/swarm`。
  - 接口 404/数据缺失时该模块显示"本任务未生成该部分"（如未填 mood 无心情剧本、增量复用时辩论内容沿用父任务），不报错。
- **③ 审计时间线**：`GET /api/plans/{id}/audit` 事件流（时间/动作/操作人/详情），垂直时间线样式。
- **④ 记忆与干预（挂载点，本批仅空态）**：预留页签，展示"记忆中心建设中——图记忆与运行态强干预由工单 7 独立批次交付，届时此处呈现该任务/客户的记忆三元组卡片与干预历史"。空态样式与全站一致，不请求任何接口。
- **状态刷新**：D3 裁决为抽屉打开期间每 5 秒刷新状态；抽屉关闭时清理定时器。

### 5.3 改单 + 版本 diff

- **改单**：行内"改单"按钮 → 弹窗：显示当前版本号，输入自然语言改动需求（placeholder 示例"预算改为 3000 元，减少打车"），提交 `POST /api/plans/{id}/replan`（`change_request` + `base_version`）。成功后 toast 显示新 job_id，列表刷新，新任务自动打开详情抽屉。
- **版本 diff**：详情抽屉行程书页签顶部，当 `parent_job_id` 存在时显示"与父版本对比"按钮 → `GET /api/plans/{id}/diff` → 行级红绿对比（加=绿底/删=红底/同=灰），头部统计"改了 N 行 / 删了 M 行 / 保留 K 行"。

### 5.4 客户管理页

前端聚合现有 `GET /api/plans`（100 条内）按 `customer` 分组：客户名、方案数、完成数/完成率、待审数、最近活跃时间。行点击 → 跳转方案列表页并预填客户筛选。页面标注"演示级前端聚合（当前数据窗口内）"。无客户归属的任务归入"未归属"行。

### 5.5 客户之声

- **后端**：新接口 `GET /api/feedbacks`（规格见 §6.1）。
- **前端**：顶部计数卡（好评数/投诉数/总数）+ 好评/投诉筛选 tabs + 明细表（时间/客户/类型/操作人/内容/job 链接，job 链接点击打开该任务详情抽屉）+ 右上"代客记录反馈"按钮（弹窗：job_id/类型/操作人/内容 → 原 feedback 接口）。

### 5.6 白标交付

- 修复预览区 bug（`hidden` class + `display:none` 双重隐藏导致生成后看不到预览）。
- 导出成功后：元信息 + 预览区正常展示 markdown 全文。
- 导出文档头部加中立声明行（见 §6.3）。
- 表单布局对齐新视觉（其余功能不变）。

## 6. 后端改动规格（4 处）

### 6.1 新增 `GET /api/feedbacks`（admin.py）

- Query：`kind`（praise|complaint，可选）、`customer`（可选）、`limit`（默认 100）。
- 实现：复用 `export_audit_csv` 的聚合模式——遍历 `_iter_states()`，读 `DATA_ROOT/{job_id}/audit.log`，过滤 `action == "feedback"` 事件，用 state 补 `customer`/`destination`。
- 响应：`{"total": int, "praise_count": int, "complaint_count": int, "items": [{"job_id", "created_at", "kind", "operator", "content", "customer", "destination"}]}`（按 created_at 倒序）。
- 认证：挂在 admin router 上，自动继承 main.py 的 `_auth_deps` 守卫。

### 6.2 新增 `GET /api/plans/{job_id}/diff`（plans.py）

- 前置：replan 时在子任务 state 落盘 `parent_job_id`（当前只在响应/父审计里有，state 未存——replan `store.create` 后仿照 create_plan 补写 customer 的模式补一行）。
- 实现：load 子任务 state → 取 `parent_job_id`（无则 400，detail 明确提示"非重规划任务"）→ 读父子两份 `travel_plan.md`（任一缺失 404）→ `difflib.SequenceMatcher` 行级比对 → 结构化输出（上限 2000 行，超出截断并标注）。
- 响应：`{"job_id", "parent_job_id", "added": int, "removed": int, "unchanged": int, "truncated": bool, "lines": [{"type": "same"|"add"|"del", "text": str}]}`。
- 认证：与 plans router 现有读接口（如 `/{job_id}/audit`）同层级，不挂管理守卫（plans_router 挂载时无 dependencies）；`GET /api/feedbacks` 挂 admin_router 自动继承管理守卫。

### 6.3 白标导出加中立声明（plans.py `export_branded_plan`）

`branded` 头部块（企业品牌行之后）插入一行：
`> 中立声明：本方案由中立规划引擎生成，不绑定任何供应链、不参与返佣分成，推荐结果不受库存利益影响。`

### 6.4 schema 补字段（schemas.py `PlanStatusResponse` + 状态端点）

- `parent_job_id: str | None = None`、`completed_nodes: list[str] | None = None`——状态端点从 state 透出，供抽屉的步骤条与 diff 入口使用。列表接口不动。

## 7. 前端修复项

admin.html 的管理请求统一使用 `apiFetch`（带 Bearer）：审批、导出、审计、反馈，以及审计 CSV 改为 `fetch + blob` 下载（D1），避免 `AUTH_ENABLED=true` 时直链 401。D3 裁决为详情抽屉每 5 秒刷新状态，关闭抽屉时清理定时器。

## 8. 验证与验收标准

1. `python -m compileall app scripts` + `PYTHONIOENCODING=utf-8 python scripts/smoke_test.py` 全绿（回归不破坏六条链路）。
2. 新接口各配一条可复现 curl 或 pytest：feedbacks 聚合含 praise/complaint 计数正确；diff 对真实父子任务返回红绿行且行数统计一致；非重规划任务调 diff 返回 400。
3. 浏览器全链路实测（`/b` 登录 → 8 页签）：提交任务 → 列表出现 → 详情抽屉三页签 → 改单 → 新任务 diff 红绿可见 → 提交反馈 → 客户之声出现该记录 → 白标导出预览与声明可见。
4. AUTH_ENABLED=true 下回归验证四处修复调用不再 401。
5. README 演示脚本、《接口文档.md》同步更新新接口与页面说明。

## 9. 诚实口径（不变 + 新增标注）

- 客户管理页标注"演示级前端聚合（当前数据窗口内）"。
- 反馈列表来自本地审计日志聚合，非独立反馈存储。
- diff 为 travel_plan.md 行级文本 diff，非语义级变更说明。
- 决策溯源呈现的是既有 Agent 留痕（agent_outputs/辩论/反事实/swarm），非新增推理能力。
- 出行数据仍为本地估算/演示样例（上位文档口径不变）。

## 10. 交付物清单

| 文件 | 改动 |
|---|---|
| `frontend/admin.html` | 全量重构（视觉 tokens、侧边栏、详情抽屉、改单弹窗、客户管理、客户之声、角标、修复认证头） |
| `backend/app/api/admin.py` | +`GET /api/feedbacks` |
| `backend/app/api/plans.py` | +`GET /api/plans/{id}/diff`；replan 落盘 parent_job_id；export 加中立声明 |
| `backend/app/models/schemas.py` | PlanStatusResponse 补 `parent_job_id`/`completed_nodes` |
| `backend/tests/test_tob_workbench.py`（新增） | feedbacks/diff/中立声明/parent_job_id 落盘的用例，与现有 `tests/` pytest 套件同构 |
| `README.md` / `接口文档.md` | 同步更新 |
