# design_v2 接入真实后端 · 实施方案

> 目标：以 `design_v2/index.html`（青绿山水皮肤、功能全量 Demo）为新首页骨架，替换 `frontend/index.html`，但**保留旧版全部真实后端能力**（登录、生成流水线、行程书、体验中心、服务大厅）。
> 原则：结构与视觉沿用 design_v2；交互数据源从「写死 mock」切换为「真实 API + 失败降级 mock」。

---

## 一、现状盘点（已核实）

### 后端端点契约（backend/app/api，全部真实存在）

| 端点 | 方法 | 关键字段 |
|---|---|---|
| `/api/auth/login` | POST | `{realm:"toc", username, password}` → `{token, name}` |
| `/api/auth/register` | POST | `{username, password, display}` → `{token, name}` |
| `/api/plans` | POST | `{destination, days(1-14), budget, travelers, origin, departure_date, return_date, mood, preferences[], constraints[]}` → `{job_id, status}` |
| `/api/plans/{job_id}` | GET | `{status, current_agent, progress(0-100), resume_from, version, error, completed_nodes[]}` |
| `/api/plans/{job_id}/approval` | POST | `{decision:"approve"/"reject", operator, reason, base_version}`（409=版本冲突） |
| `/api/plans/{job_id}/replan` | POST | `{change_request, base_version}` → `{job_id, diff_summary}`（增量复用 Researcher/Planner/Itinerary） |
| `/api/plans/{job_id}/result` | GET | `{travel_plan_md, sha256, itinerary[], hotels[], economy_tips[]}` |
| `/api/plans/{job_id}/debates` | GET | `{debates:[{topic, plan_side{role,point}, traveler_side{role,point}, verdict{decision,reason}}]}` |
| `/api/plans/{job_id}/swarm` | GET | `{reports:[{persona, style, day, verdict, tip}]}` |
| `/api/plans/{job_id}/counterfactual` | GET | `{cards:[{gave_up, got, reason, cost_note}]}` |
| `/api/plans/{job_id}/guides` | GET | `{reviews:[{id, name, persona, review}]}` |
| `/api/plans/{job_id}/dialogue` | POST | `{guide_id, message, history[]}` → `{guide, reply}` |
| `/api/plans/{job_id}/map` / `/nearby?kind=` | GET | 地图动线 / 周边分类数据 |
| `/api/services/{kind}` | GET | train/flight/attraction/merchant/entertainment，`?destination=&origin=` |

**状态机**：`QUEUED → RUNNING → (WAITING_BUDGET_APPROVAL | WAITING_SAFETY_REVIEW) → COMPLETED`，异常态含 `FAILED / CORRUPTED / REPLAN_REQUIRED / RECOVERY_REQUIRED / WAITING_PARSE_REVIEW / WAITING_RATE_LIMIT`。

### 旧前端关键行为（迁移时必须保留）

1. `apiBase = localStorage.apiBase || (file: 协议 ? http://127.0.0.1:8000 : "")`；
2. 轮询间隔 **600ms**；`WAITING_BUDGET_APPROVAL` 时**停轮询**、弹批准横幅，approve 后恢复轮询（approval 接口把状态置回 RUNNING 并重新入队）；
3. token 存 `localStorage.tocToken / tocName`，登出即清除刷新；toC 的 plans 系列接口**不强制带 Authorization**（admin 才强制）；
4. 行程书优先用 `result.itinerary` 结构化渲染（每天 items/meals/legs/weather/fun_tip），无 itinerary 时降级渲染 markdown（剥离工程章节）；
5. 「翻车预演/B 计划」直接从 `travel_plan_md` 的 `## N. 翻车预演` 章节正则提取；
6. 备注（笔记）按 `wl_notes_{jobId}` 存 localStorage；
7. `/vendor/leaflet`、`/media/scenery.mp4` 走项目静态服务，file: 直开会缺失（原版同样如此）。

---

## 二、design_v2 区块 ↔ 真实 API 映射表

| design_v2 区块（现 mock） | 改造后数据源 | 说明 |
|---|---|---|
| 登录门禁（新增） | `/api/auth/login` `/register` | 沿用旧版门禁逻辑，皮肤换青绿山水风 |
| 表单（目的地/天数/预算/日期/心情 chips） | `POST /api/plans` | 心情 chips 多选合并为 `mood` 词组；补 travelers/origin 字段 |
| 生成弹层（6 条固定日志 + 4 角色卡） | 轮询 `GET /api/plans/{job_id}` | `current_agent` + `completed_nodes` 驱动角色卡状态；`progress` 驱动进度条；日志改为真实节点事件流 |
| 预算挂起（弹窗演示） | 状态 `WAITING_BUDGET_APPROVAL` → `POST /approval` | 真实挂起：预估额从 result/进度事件取，approve/reject 二选一，带 base_version |
| 行程书 7 章（mock 成都三日） | `GET /result` 的 `itinerary` + `travel_plan_md` | ②逐日=itinerary；③账本=md 费用章；④辩论=debates 接口；⑤剧本=mood 参数生成章；⑥B计划=md 翻车预演章；⑦清单=md 装备章 |
| 体验中心 6 卡 | debates / swarm / counterfactual / guides / dialogue / map+nearby | 全部换真实接口数据；名导对话接 dialogue |
| 服务大厅 5 窗口 | `/api/services/{kind}` | 真实数据；「预订」按钮保留 toast「未接支付」口径 |
| 4 张智能体卡产出浮层 | `completed_nodes` + result 各章 | 展示真实节点完成情况与对应产出章节 |
| 收藏/我的行程 | `GET /api/plans`（列表接口，按 customer 过滤）+ localStorage | 沿用旧版历史收藏逻辑 |

---

## 三、关键技术决策

1. **双模式降级**：页面保留 design_v2 现有 mock 数据为「演示模式」。启动时探测后端（`GET /api/plans` 超时 1.5s 或失败）→ 不可用则顶部出现「演示模式」徽章，全部走 mock；可用则走真实链路。**好处：设计稿演示能力不丢，后端挂了页面不白屏**。
2. **生成弹层重写为状态机驱动**：删除固定 6 条日志的 `setInterval` 剧本，改为轮询回调渲染——每次 poll 的 `current_agent` 变化即追加一条日志；角色卡映射 `Researcher→情报员 / Planner→路线师 / Itinerary→排期师 / Validator→质检官 / Budget→账房 / Debate→辩论席 / Reporter→主笔`（沿用「游客视角转译」文案原则）。上次修复的「日志声明归属角色」机制保留。
3. **行程书渲染器复用**：直接移植旧版 `renderTripView / mdToHtml / stripEngineeringSections / inlineMd` 四个函数（纯函数，无 DOM 结构耦合），输出套 design_v2 书页样式。
4. **版本与批准**：全程维护 `currentVersion`；approval/replan 的 409 冲突提示沿用旧版文案。
5. **不迁移项**：旧版的对话式引导输入流（planner 预填）、备注笔记、wiki 图片增强、城市照片。P0 不做，列入 P2 可选。

---

## 四、分阶段计划与验收

### P0 · 核心闭环（先做）
登录门禁 + 表单提交 + 轮询进度（含真实挂起/批准/续跑）+ 行程书真实渲染（itinerary 优先、md 降级）+ 演示模式降级。
**验收**：docker-compose 起后端后，登录→输入成都 3 天→真实流水线→超预算弹真实批准框→出真实行程书；停掉后端→页面自动进演示模式。

### P1 · 体验中心真实化
六卡全部换 debates/swarm/counterfactual/guides/dialogue/map+nearby；replan（「改一改行程」）接增量重规划并展示 diff_summary。
**验收**：每张卡内容与 `data/` 下该 job 的 agent_outputs 一致；改一改能生成新 job 且摘要正确。

### P2 · 服务大厅与收尾
服务大厅接 `/api/services/*`；历史行程列表接 `GET /api/plans`；导出长图（html2canvas）；可选：备注笔记、wiki 增强。

### 风险点
- itinerary 为 toB 旧 job 缺省字段 → 必须 md 降级路径可用（已验证旧版有）；
- 轮询期间用户关闭弹层 → 保留后台轮询，顶栏状态条继续显示进度（不中断生成）；
- design_v2 现有事件委托结构较松 → 新增 API 层统一放独立 `<script>` 段，与现有演示层隔离，便于回滚。

---

## 五、执行方式

- 新文件在 `design_v2/index.html` 基础上改造（原地升级），完成 P0 后先备份旧 `frontend/index.html` → `frontend/index_legacy_backup.html`，再替换。
- 每阶段完成后浏览器实测 + Node 语法/ID 校验（沿用既有校验脚本）。
