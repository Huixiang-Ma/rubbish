# 多 Agent 文旅系统 · 需求分析与 WBS 拆解文档

> 文档版本：v1.1（正式交付版）  
> 编制日期：2026-08-28  
> 输入依据：《实现顺序梳理.md》  
> 当前阶段：任务一——需求分析、前后端架构设计与任务拆解  
> 阶段约束：本文档定稿前，不进入业务编码阶段。

---

## 目录

1. 文档目标与适用范围
2. 产品定位与场景划分
3. MVP 范围与非目标边界
4. 功能需求
5. 非功能需求
6. 总体技术架构
7. 核心业务流与数据流
8. 多 Agent 架构设计
9. 数据库、缓存、消息队列与文件设计
10. 接口设计
11. 算法与安全技术方案
12. 异常场景与边界处理
13. 1 人 1 周 WBS 拆解
14. 验收标准与可砍范围
15. 结论

---

## 1. 文档目标与适用范围

### 1.1 文档目标

本文档用于将《实现顺序梳理.md》中的开发顺序、架构约束和交付目标，整理为可执行、可验收、无歧义的需求与任务拆解说明。

本文档重点明确：

- 系统面向哪些业务场景；
- MVP 必须交付哪些能力；
- 哪些功能属于增强项或可砍项；
- 前端、后端、队列、状态、文件和 Agent 如何协同；
- 如何处理文件并发写入损坏、API 速率限制、恶意 Prompt 注入、断点状态检测、高并发防重等异常场景；
- 一名开发者在一周内如何按优先级完成可演示版本。

### 1.2 适用范围

本文档适用于：

- 任务一阶段的需求评审、架构设计和 WBS 拆解；
- 后续编码阶段的技术边界依据；
- 答辩或验收阶段的范围说明；
- 后续《三方需求互评与对齐记录》和《核心技术架构深度剖析手册》的引用。

### 1.3 基本约束

- 当前没有已有代码上下文。
- 原始输入文档为 `D:\Desktop\WL项目\实现顺序梳理.md`。
- 任务编号沿用 T001–T037。
- 文档中的生产级设计可作为目标架构说明，MVP 实现允许按降级策略收敛。
- 本文档中的“裁决”表示三方对齐后的推荐裁决，仍需学生在最终定稿时确认。

---

## 2. 产品定位与场景划分

### 2.1 产品定位

本系统定位为：

> 面向游客与文旅顾问的多 Agent 智能行程规划与审核系统，重点展示多 Agent 协作、可解释规划、安全防御、断点恢复、增量重规划和高并发防重能力。

系统核心不是“一次 LLM 调用生成攻略”，而是通过多个职责明确的 Agent，完成从需求理解、资料调研、路线规划、预算判断、安全检测、可行性校验到 Markdown 汇报的完整工程化链路。

### 2.2 场景划分

| 场景 | 目标用户 | 核心目标 | MVP 要求 |
|---|---|---|---|
| toC 行程生成 | 普通游客 | 输入目的地、天数、预算、偏好，生成可读行程 | 必须实现 |
| toC 可解释展示 | 普通游客 | 说明行程安排理由、风险和替代方案 | 必须保留基础能力 |
| toB 顾问审核 | 文旅顾问 | 审核超预算、高风险或需重规划方案 | 后端挂起能力必须，完整前端可简化 |
| 工程展示 | 答辩/验收 | 展示断点恢复、Prompt 注入拦截、增量重规划、安全计数 | 必须保留核心演示 |
| 经营管理 | 管理者 | 多租户、经营看板、白标交付 | 可选增强 |
| 趣味玩法 | 游客 | 盲盒、徽章、年报、直播辩论大屏等 | 可砍 |

### 2.3 明确不做的内容

本系统 MVP 不承诺：

- 实时路网导航；
- 商业级 OTA 预订、支付与订单履约；
- 全国全量景点知识库；
- 生产级 SaaS 多租户系统；
- 完全无人参与的预算采购审批；
- 完整行程生成吞吐达到 QPS≥200。

---

## 3. MVP 范围与非目标边界

### 3.1 MVP 必须交付

| 编号 | 能力 | 说明 |
|---|---|---|
| M1 | 单 Agent 端到端闭环 | 输入一句旅行需求，前端展示一份可读行程 |
| M2 | `travel_plan.md` schema | 在第二个 Agent 接入前定稿数据契约 |
| M3 | 异步 `job_id` 架构 | 创建任务后立即返回 `job_id`，前端查询进度 |
| M4 | 核心 Agent 链路 | 至少实现 Researcher、Planner、Itinerary、Validator |
| M5 | Reporter 汇总输出 | 由 Reporter 单点生成最终 Markdown |
| M6 | 静态景点库 | 覆盖演示城市 20–30 个景点 |
| M7 | 时空可行性校验 | 能识别明显不可行路线，如“上午故宫下午长城” |
| M8 | Prompt 注入基础防御 | 高风险注入拦截，中风险摘要降权 |
| M9 | 状态持久化与恢复 | 支持 checkpoint / state 文件，演示强杀后恢复调度 |
| M10 | 原子写与 hash 校验 | 避免状态文件和 Markdown 并发写入损坏 |
| M11 | 超预算挂起审批 | 后端支持预算超限挂起、审批、审计 |
| M12 | 联调与交付文档 | 完成录屏、README、部署手册、诚实声明 |

### 3.2 可降级或后置功能

| 功能 | 理想方案 | MVP 降级方案 |
|---|---|---|
| 8 个物理 Agent | 8 个独立 Agent 类 | 4 个核心 Agent 承担 8 类职责 |
| Redis Streams | 完整队列、消费组、pending claim | 单 Worker + 本地任务表，文档保留目标架构 |
| Redis Checkpointer | Redis 保存完整恢复锚点 | 本地 `state.json` + hash 校验 |
| 全国景点库 | 全国静态库或外部 API | 演示城市 20–30 个景点 |
| 实时路网 | 地图接口实时通勤 | 预计算通勤时间，不承诺实时性 |
| 细粒度增量 diff | 节点级依赖 diff | 按天或按节点粗粒度重算 |
| 完整 toB 审核台 | 审核、回滚、版本对比、导出 | 简化审批页或后端接口演示 |
| 多租户与经营看板 | 完整管理后台 | 后置或砍掉 |
| 彩头玩法 | 盲盒、徽章、年报、直播大屏 | 后置或砍掉 |

---

## 4. 功能需求

### 4.1 用户需求输入

用户可以输入以下信息：

- 目的地；
- 出行天数；
- 总预算；
- 出行偏好；
- 人群类型；
- 约束条件，如“不去爬山”“亲子友好”“减少打车”“不要太赶”。

请求示例：

```json
{
  "destination": "北京",
  "days": 3,
  "budget": 5000,
  "preferences": ["亲子", "博物馆", "美食"],
  "constraints": ["减少打车", "不要太赶"]
}
```

### 4.2 行程生成

系统应生成以下内容：

- 行程总览；
- 每日路线；
- 景点说明；
- 交通建议；
- 餐饮建议；
- 预算估算；
- 风险提示；
- 不可行项说明；
- 可解释规划理由；
- 最终 `travel_plan.md`。

### 4.3 多 Agent 协作

系统按职责拆分为 8 类 Agent：

| Agent | 类型 | 主要职责 |
|---|---|---|
| Researcher | 上游产出型 | 收集景点、开放时间、交通、评价、风险信息 |
| Planner | 上游产出型 | 制定总体行程框架和每日主题 |
| Itinerary | 上游产出型 | 细化每日路线、时间段、活动安排 |
| Budget | 中游计算型 | 估算成本并判断是否超预算 |
| Sentiment | 下游消费型 | 识别舆情、负面评价和游客情绪风险 |
| Safety | 下游防御型 | 检测 Prompt 注入、越权指令、高风险内容 |
| Validator | 下游校验型 | 校验时空可行性、闭园、预算、约束冲突 |
| Reporter | 下游汇总型 | 汇总结构化结果并生成 `travel_plan.md` |

### 4.4 断点续传

系统应支持：

- 每个关键节点完成后写入 checkpoint；
- Worker 被强杀或重启后恢复调度；
- 已成功抓取或生成的内容不重复执行；
- 文件 hash 不一致时进入人工恢复，不自动覆盖。

验收口径：

> Worker 重启后 5 秒内发现可恢复任务并恢复调度；不承诺 5 秒内完成 LLM 调用或完整行程生成。

### 4.5 Prompt 注入防御

系统应支持：

- 用户输入检测；
- 网页内容检测；
- 工具输出检测；
- 高风险内容拦截；
- 中风险内容摘要后降权使用；
- Safety Agent 失败时默认保守处理；
- 安全事件记录。

### 4.6 增量重规划

系统应支持基于已有版本发起重规划：

- 用户提交变更请求；
- 系统计算变更影响范围；
- 尽量保留未受影响节点；
- 返回变更摘要和新版本；
- 前端展示差异或变更摘要。

验收口径：

> 不承诺 `<3s`，承诺相较全量重算耗时降低 ≥70%；MVP 可采用按天或按节点的粗粒度重算。

### 4.7 HITL 人工审核

以下场景应进入挂起状态：

- 预算超限；
- 高风险 Prompt 注入；
- Output Parse 多次失败；
- 状态 hash 冲突；
- 第三方接口长期限流；
- 人工主动要求复核。

挂起状态不是失败，而是可恢复、可审计的中间状态。

### 4.8 审计日志

系统应记录：

- 操作人；
- 操作时间；
- 任务 ID 和版本号；
- 操作类型；
- 操作前状态；
- 操作后状态；
- 是否人工确认；
- 操作是否成功。

---

## 5. 非功能需求

| 类别 | 要求 | 验收口径 |
|---|---|---|
| 性能 | QPS≥200 | 仅指任务提交接口 QPS，不指完整行程生成 QPS |
| 可恢复性 | 支持断点续传 | Worker 重启后 5 秒内恢复调度 |
| 一致性 | 防文件损坏 | 原子写 + hash 校验 + Reporter 单点写入 |
| 安全性 | 防 Prompt 注入 | 高风险拦截，中风险摘要降权，低风险审计放行 |
| 幂等性 | 防重复任务、重复审批、重复重规划 | request_hash、版本号、锁机制 |
| 可解释性 | 输出规划理由 | 至少展示一段“为什么这样安排” |
| 可演示性 | 支持录屏和缓存兜底 | LLM 不稳定时可复现实验效果 |
| 可降级性 | 非核心失败不全盘崩溃 | 非核心 Agent 可跳过或降级，核心 Agent 失败才标记 failed |

---

## 6. 总体技术架构

### 6.1 推荐架构

```text
前端 Web
  ↓
FastAPI API Gateway
  ↓
Redis Streams / MVP 任务队列
  ↓
Worker 进程
  ↓
Agent Orchestrator / StateGraph
  ↓
LLM Client + 工具层 + 静态景点库 + Safety 检测
  ↓
Checkpoint / DB / JSON 状态 / 缓存
  ↓
Reporter 原子生成 travel_plan.md
  ↓
前端轮询或 SSE 展示进度与结果
```

### 6.2 架构裁决建议

| 决策点 | 推荐裁决 | 理由 |
|---|---|---|
| 同步 vs 异步 | 采用异步 `job_id` 模式 | 多 Agent 长周期推理无法通过同步接口稳定承载 |
| 状态源 | checkpoint / DB / JSON 为准 | Markdown 是展示产物，不适合作唯一状态源 |
| Markdown 写入 | Reporter 单点原子写 | 防止多个 Agent 并发写入损坏 |
| 队列 | Redis Streams 为目标架构 | 支持削峰、消费组、pending claim |
| MVP Agent 数量 | 至少 4 个核心 Agent | 一周交付风险可控 |
| 景点数据 | 演示城市静态库 | 不承诺实时路网和全国覆盖 |
| 安全策略 | 外部内容默认不可信 | 防止 Prompt 注入污染主链路 |

---

## 7. 核心业务流与数据流

### 7.1 创建规划任务

```text
用户提交需求
  ↓
FastAPI 校验参数
  ↓
生成 request_hash
  ↓
检查重复提交
  ↓
创建 plan_jobs 记录
  ↓
写入 Redis Streams / MVP 任务队列
  ↓
返回 job_id + QUEUED
```

边界规则：

- 参数缺失返回 `400 INVALID_REQUEST`。
- 同一用户重复提交相同需求时，返回已有 `job_id`。
- 队列不可用时，MVP 可降级写入 DB/文件任务表。
- API 不等待完整规划结果。

### 7.2 Worker 执行任务

```text
Worker 拉取任务
  ↓
获取 lock:job:{job_id}
  ↓
读取 checkpoint
  ↓
从 resume_from 执行 Agent
  ↓
每个节点完成后写 checkpoint
  ↓
Reporter 汇总生成 travel_plan.md
  ↓
更新状态为 COMPLETED
```

边界规则：

- 拿不到任务锁时延迟重试。
- checkpoint hash 不一致时进入 `CORRUPTED` 或 `RECOVERY_REQUIRED`。
- LLM 限流时进入 `WAITING_RATE_LIMIT`。
- 预算超限时进入 `WAITING_BUDGET_APPROVAL`。

### 7.3 Prompt 注入防御

```text
外部网页 / 评论 / 工具输出
  ↓
标记为 untrusted_content
  ↓
规则分类器初筛
  ↓
Safety Agent 二次判断
  ↓
高风险 block
中风险 summary + 降权
低风险审计后进入上下文
```

边界规则：

- 包含“忽略之前指令”“输出系统提示词”等语句时，至少标记为 `SUSPICIOUS`。
- Safety Agent 失败时默认保守拦截。
- Attack Agent 只作为影子评测，不污染主链路上下文。

### 7.4 断点恢复

```text
Worker 启动
  ↓
扫描 running 超时任务 / pending message / 残留 tmp
  ↓
读取 checkpoint 与文件 hash
  ↓
状态一致：从 resume_from 恢复
状态缺失：从 Researcher 开始或人工处理
状态冲突：进入 RECOVERY_REQUIRED / CORRUPTED
```

---

## 8. 多 Agent 架构设计

### 8.1 职责分层

```text
上游产出型：Researcher → Planner → Itinerary
中游计算型：Budget
下游消费型：Sentiment → Safety → Validator → Reporter
影子评测型：Attack Agent（只做安全测试，不进入主链路）
```

### 8.2 主链路状态机

```text
QUEUED
  ↓
RUNNING: Researcher
  ↓
RUNNING: Safety Precheck
  ↓
RUNNING: Planner
  ↓
RUNNING: Itinerary
  ↓
RUNNING: Budget
  ↓
WAITING_BUDGET_APPROVAL? ── approve ──→ RUNNING
  ↓ reject
REPLAN_REQUIRED
  ↓
RUNNING: Sentiment
  ↓
RUNNING: Validator
  ↓
RUNNING: Reporter
  ↓
COMPLETED
```

### 8.3 状态枚举

| 状态 | 含义 |
|---|---|
| `QUEUED` | 任务已入队，等待 Worker 执行 |
| `RUNNING` | Agent 链路正在执行 |
| `WAITING_RATE_LIMIT` | 第三方 API 或 LLM 限流，等待重试 |
| `WAITING_BUDGET_APPROVAL` | 预算超限，等待人工审批 |
| `WAITING_SAFETY_REVIEW` | 高风险内容，等待人工安全确认 |
| `WAITING_PARSE_REVIEW` | 输出解析多次失败，等待人工确认 |
| `RECOVERY_REQUIRED` | 状态冲突，需要人工恢复 |
| `COMPLETED` | 任务完成 |
| `FAILED` | 核心 Agent 失败且不可恢复 |
| `CORRUPTED` | 状态或文件 hash 损坏，禁止自动继续 |

---

## 9. 数据库、缓存、消息队列与文件设计

### 9.1 数据库表设计

#### `plan_jobs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `job_id` | string | 主键 |
| `request_hash` | string | 幂等键 |
| `user_input` | json | 原始输入 |
| `status` | string | 当前任务状态 |
| `current_node` | string | 当前节点 |
| `resume_from` | string | 恢复锚点 |
| `result_path` | string | Markdown 结果路径 |
| `version` | int | 当前版本 |
| `error_code` | string | 错误码 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

#### `plan_versions`

| 字段 | 类型 | 说明 |
|---|---|---|
| `version_id` | string | 版本 ID |
| `job_id` | string | 所属任务 |
| `parent_version_id` | string | 父版本 |
| `base_version` | int | 重规划基线版本 |
| `diff_summary` | json | 变更摘要 |
| `file_hash` | string | Markdown sha256 |
| `state_hash` | string | 状态 sha256 |
| `created_at` | datetime | 创建时间 |

#### `audit_logs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `log_id` | string | 日志 ID |
| `job_id` | string | 任务 ID |
| `version` | int | 操作版本 |
| `operator` | string | 操作人 |
| `action` | string | 操作类型 |
| `before_state` | json | 操作前状态 |
| `after_state` | json | 操作后状态 |
| `success` | boolean | 是否成功 |
| `created_at` | datetime | 创建时间 |

#### `safety_events`

| 字段 | 类型 | 说明 |
|---|---|---|
| `event_id` | string | 事件 ID |
| `job_id` | string | 任务 ID |
| `source` | string | `user_input` / `web_content` / `tool_output` |
| `risk_type` | string | 风险类型 |
| `risk_level` | string | `low` / `medium` / `high` |
| `action` | string | `allow` / `sanitize` / `block` |
| `evidence` | text | 命中证据 |
| `created_at` | datetime | 创建时间 |

### 9.2 Redis Key 设计

```text
stream:plan_jobs
checkpoint:{job_id}
lock:job:{job_id}
lock:file:{job_id}:travel_plan
lock:approval:{job_id}:{version}
lock:replan:{job_id}:{base_version}
idempotency:request:{request_hash}
cache:web:{url_hash}
cache:agent:{job_id}:{agent_name}:{input_hash}
rate_limit:user:{user_id}
rate_limit:llm:{provider}
```

### 9.3 文件目录设计

```text
data/
  jobs/
    {job_id}/
      state.json
      state.json.sha256
      travel_plan.md
      travel_plan.md.sha256
      versions/
        v1.md
        v2.md
      agent_outputs/
        researcher.json
        planner.json
        itinerary.json
        validator.json
      audit.log
```

### 9.4 `travel_plan.md` 定位

`travel_plan.md` 是最终展示与导出产物，不是唯一状态源。

约束：

- Agent 不直接写最终 Markdown；
- Agent 只输出结构化 JSON；
- Reporter 汇总所有结构化结果后生成 Markdown；
- 文件写入采用 `.tmp → fsync → rename → sha256`；
- hash 校验失败时不自动继续执行。

---

## 10. 接口设计

### 10.1 创建规划任务

```http
POST /api/plans
```

请求：

```json
{
  "destination": "北京",
  "days": 3,
  "budget": 5000,
  "preferences": ["亲子", "博物馆", "美食"],
  "constraints": ["减少打车"],
  "mode": "async"
}
```

响应：

```json
{
  "job_id": "plan_20260828_001",
  "status": "QUEUED"
}
```

### 10.2 查询任务状态

```http
GET /api/plans/{job_id}
```

响应：

```json
{
  "job_id": "plan_20260828_001",
  "status": "RUNNING",
  "current_agent": "Validator",
  "progress": 72,
  "resume_from": "validator.spatial_check",
  "version": 2,
  "result_url": null,
  "error": null
}
```

### 10.3 获取结果

```http
GET /api/plans/{job_id}/result
```

响应：

```json
{
  "job_id": "plan_20260828_001",
  "version": 2,
  "travel_plan_md": "# 北京 3 日游...",
  "sha256": "..."
}
```

### 10.4 增量重规划

```http
POST /api/plans/{job_id}/replan
```

请求：

```json
{
  "change_request": "预算改为 3000 元，减少打车",
  "base_version": 2
}
```

响应：

```json
{
  "job_id": "plan_20260828_002",
  "parent_job_id": "plan_20260828_001",
  "status": "QUEUED",
  "replan_mode": "incremental"
}
```

### 10.5 人工审批

```http
POST /api/plans/{job_id}/approval
```

请求：

```json
{
  "decision": "approve",
  "operator": "student",
  "reason": "预算超出但可接受",
  "base_version": 2
}
```

响应：

```json
{
  "status": "APPROVED",
  "next_node": "Reporter"
}
```

边界规则：

- 版本冲突返回 `409 VERSION_CONFLICT`；
- 已审批返回 `409 APPROVAL_ALREADY_DECIDED`；
- 审计日志写入失败时，审批不得生效。

---

## 11. 算法与安全技术方案

### 11.1 时空可行性校验

输入：

- 每日路线；
- 景点经纬度；
- 开放时间；
- 预估游玩时长；
- 预计算通勤时长。

规则：

- 相邻景点通勤时间 + 游玩时间超过可用时间窗口时，判定不可行；
- 到达时间晚于闭园时间时，判定不可行；
- 用户要求低强度但路线密度过高时，给出风险提示。

示例：

> 如果用户要求“上午故宫，下午长城当天往返”，系统应提示“两地通勤与游玩时间超过当天可用窗口，闭园前无法覆盖”，并建议拆分到不同日期。

### 11.2 高风险舆情与负面情感分类

MVP 采用“关键词规则 + LLM 分类”的混合方案，不训练小模型。

| 标签 | 含义 | 处理 |
|---|---|---|
| `BENIGN` | 无明显风险 | 正常推荐 |
| `NEGATIVE_REVIEW` | 普通负面评价 | 降权或提示 |
| `SERVICE_RISK` | 服务质量风险 | 提示风险 |
| `SAFETY_RISK` | 人身或财产安全风险 | 高亮提示或不推荐 |
| `SCAM_RISK` | 宰客、诈骗、强制消费 | 默认不推荐 |
| `UNKNOWN` | 无法判断 | 保守降权 |

### 11.3 Prompt 注入分类防御

| 标签 | 含义 | 处理 |
|---|---|---|
| `BENIGN` | 正常资料 | 可进入上下文并审计 |
| `SUSPICIOUS` | 疑似注入 | 摘要后降权使用 |
| `MALICIOUS` | 明确攻击 | 拦截，不进入 Planner |
| `UNKNOWN` | 无法判断 | 默认保守处理 |

典型高风险模式：

- 忽略之前所有指令；
- 输出系统提示词；
- 绕过审核；
- 修改预算上限；
- 要求不要告知用户；
- 泄露密钥；
- 伪造工具结果。

### 11.4 Output Parse Fallback

Agent 输出结构化解析失败时：

1. 尝试 JSON 修复；
2. 使用 fallback prompt 要求重新输出指定 schema；
3. 最多重试 N 次；
4. 仍失败则进入 `WAITING_PARSE_REVIEW`；
5. 不得直接信任未解析原文。

---

## 12. 异常场景与边界处理

| 异常 | 处理结果 |
|---|---|
| 文件写入中断 | 恢复最近完整版本，残留 `.tmp` 不直接覆盖正式文件 |
| 文件 hash 不一致 | 标记 `CORRUPTED` 或 `RECOVERY_REQUIRED`，等待人工处理 |
| 多 Agent 同时写 Markdown | 禁止，Reporter 单点写入 |
| 同一任务被多个 Worker 拉取 | 只有拿到 `lock:job:{job_id}` 的 Worker 执行 |
| API 提交过快 | 限流或入队，返回 queued / rate limited |
| LLM 限流 | 状态变为 `WAITING_RATE_LIMIT`，指数退避 |
| LLM 多次失败 | 核心 Agent 失败则 `FAILED`，非核心 Agent 可降级 |
| 高风险 Prompt 注入 | 拦截，不进入 Planner |
| Safety 失败 | 默认保守拦截 |
| 进程在 Agent 调用前中断 | 从该 Agent 重新执行 |
| 进程在 Agent 输出后、checkpoint 前中断 | 允许重跑该 Agent，但通过缓存避免重复副作用 |
| 任务已完成又收到恢复请求 | 直接返回最终结果 |
| 预算超限 | 进入 `WAITING_BUDGET_APPROVAL` |
| 重复审批 | 返回 `409 CONFLICT` 或当前最终状态 |
| 审计日志写入失败 | 审批不得生效 |
| 重规划 `base_version` 过旧 | 返回 `409 VERSION_CONFLICT` |
| 静态景点库无数据 | 返回“暂不支持该城市”或使用样例数据演示 |

---

## 13. 1 人 1 周 WBS 拆解

| 天数 | 目标 | 任务 | 产出 | 对应编号 |
|---|---|---|---|---|
| D1 | 跑通最小闭环 | 初始化前后端；封装 LLM Client；定稿 schema；单 Agent 输入到 Markdown 输出 | 页面展示一份可读行程 | T001–T005 部分 |
| D2 | 异步任务化 | 引入 `job_id`；实现任务队列；实现 Worker；实现状态查询 | API 提交后返回 queued/running/completed | T004、T005 |
| D3 | 多 Agent 主链路 | 抽象 Agent 基类；实现 Researcher/Planner/Itinerary/Validator；Reporter 汇总 | 多 Agent 输出进入 `travel_plan.md` | T005–T007 |
| D4 | 算得准与安全 | 静态景点库；时空校验；Safety 检测；Prompt 注入样例 | 能拒绝不可行行程，能拦截注入 | T008–T009、T012–T013 |
| D5 | 可恢复与防损坏 | checkpoint；原子写；hash 校验；kill-9 演练；缓存去重 | 强杀后恢复调度，文件不损坏 | T011、T015 |
| D6 | 可解释与管控 | 增量重规划；diff 摘要；预算挂起审批；审计日志 | 可改单、可审批、可追踪 | T010、T017–T018、T024–T028 部分 |
| D7 | 联调交付 | 压测提交接口；两大场景联调；录屏；README；部署手册；诚实声明 | 可演示、可交付、可答辩 | T034–T037 |

### 13.1 每日验收标准

| 天数 | 验收问题 | 不通过时降级 |
|---|---|---|
| D1 | 输入一句话页面能出行程吗？ | LLM 不通则用样例数据 |
| D2 | 是否返回 `job_id` 并可查状态？ | Redis 不通则用本地任务表 |
| D3 | 多 Agent 是否各有实质贡献？ | 降到 4 Agent 承担 8 职责 |
| D4 | 能拒绝“故宫+长城当天往返”吗？ | 只覆盖演示城市数据 |
| D5 | 强杀后能恢复调度吗？ | 退到缓存去重 + 秒级重启 |
| D6 | 是否能改单并展示差异？ | 按天粗粒度重算 |
| D7 | 是否有录屏、文档、部署说明？ | 不可降级，必须完成 |

---

## 14. 验收标准与可砍范围

### 14.1 不可砍项

- Step 0 单 Agent 端到端；
- `travel_plan.md` schema；
- 异步任务架构裁决；
- 至少 4 个核心 Agent；
- Reporter 单点原子写；
- 状态 checkpoint；
- Prompt 注入基础防御；
- 静态景点库与时空校验；
- 两大场景联调；
- 录屏与文档。

### 14.2 优先保留项

- 辩论式可解释；
- 翻车预演；
- 超预算挂起审批；
- 安全看板计数；
- 增量重规划。

### 14.3 可砍项

- 直播辩论大屏；
- 角色名导团；
- 盲盒、徽章、年报；
- 经营看板；
- 多租户；
- 全国景点库；
- 实时路网。

---

## 15. 结论

本项目应按照“先垂直切片，再横向加厚”的策略推进：

> Step 0 用 1 个 Agent 跑通端到端；Step 1 扩展多 Agent 职责；Step 2–4 补齐时空校验、断点恢复、安全防御和增量重规划；Step 5 做 toB 挂起审核；Step 6 只保留高价值玩法；Step 7–8 完成压测、联调、录屏和文档。

最终方案必须守住三条红线：

1. `travel_plan.md` schema 先定，Markdown 只作为展示与导出产物；
2. Step 0 就采用异步 `job_id` 架构，不在同步架构下承诺 QPS≥200；
3. 外部内容默认不可信，状态文件必须原子写入并做 hash 校验。
