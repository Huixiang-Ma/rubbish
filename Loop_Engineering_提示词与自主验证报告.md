# Loop Engineering 提示词与自主验证报告

> 版本：v1.0 ｜ 日期：2026-09-04 ｜ 依据：源码逐行核实（backend/app），无虚构条目
> 范围：LLM 提示词清单、自主验证机制、验证闭环、Loop 改进记录

---

## 1. 各 Agent 提示词清单

所有 LLM 调用经 `app/services/llm_client.py` 统一出口。系统提示词固定为：
`"你是严谨的 JSON 生成器，只输出一个合法 JSON 对象，不要输出任何多余文字。"`（`llm_client.py:90`），
并强制 `response_format: {"type": "json_object"}`；`temperature` 取自配置 `LLM_TEMPERATURE`（默认 0.2，`llm_client.py:94`）。

| Agent | 触发条件 | 位置 | 输出 JSON Schema | max_tokens |
|---|---|---|---|---|
| **Planner**（行程编排师） | 管线常驻 | `agents/planner.py:122` | `{"days": [{"day": int, "theme": str(≤8字), "spot_names": [str]}]}`；恰好 N 天；每天 1-max_per_day 个景点；只能从候选清单选、不跨天重复 | 默认 1600 |
| **Itinerary**（内容增强） | 管线常驻 | `agents/itinerary.py:181` | `{"days": {"1": {"fun_tip": str(≤40字), "spot_reasons": {景点: str(≤40字)}, "meal_details": {"午餐": {signature, price_hint}}}}}` | **2400**（`itinerary.py:190`，内容增强大输出） |
| **Mood**（心情导演） | `user_input.mood` 非空 | `agents/mood.py:60` | `{"theme": str, "phases": [{"day": int, "phase": str, "emotion": str, "narration": str(≤60字,须引用当日景点名)}]}`，phases 每天一条 | 默认 1600 |
| **Sentiment**（舆情分析师） | 本地舆情库未收录的景点 | `agents/sentiment.py:76` | `{"reviews": [{"name", "risk_level"(BENIGN/NEGATIVE_REVIEW/SERVICE_RISK/SAFETY_RISK/SCAM_RISK/UNKNOWN), "highlights", "warnings"}]}`；不确定时 UNKNOWN | 默认 1600 |

**约束条件注入示例**（Planner，`planner.py:122-137`）：地理跨度约束（同 area 优先同一天，严禁跨区往返）→ 偏好贴合（theme 匹配偏好标签）→ 经济导向（免费景点填充、收费景点每天 ≤1、门票总额 ≤ 预算 15%）→ 文本约束（"不要太赶"→ 每天 ≤max_per_day；"避免早起"→ 首站选免预约景点）。

**确定性 Agent（无 LLM）**：Debate（辩论式可解释）、Consultant（toB 话术/报价）、Compliance（toB 合规审计）、Validator（时空校验）、Budget（预算分项）、Intake（输入规范化）、Reporter（单点渲染）——全部为规则引擎，输入输出可完全复现。

## 2. 自主验证机制（`llm_client.py`）

1. **调用链**：`try_generate_json(prompt, schema, max_tokens)` → `mode=="real" 且有 key` 才发请求（`:54`）→ `_chat_completion` → `_chat_via_httpx` 失败自动降级 `_chat_via_socket`（`:103`，raw-socket 兜底通道，规避代理/SDK 层问题）
2. **重试与退避**：`max_retries + 1` 次尝试，失败退避 `0.5 × (attempt + 1)` 秒（`:56-63`）；`LLM_MAX_RETRIES` 环境变量可调（当前配置 1）
3. **JSON 解析**：`_parse_json_object` 容忍 markdown 代码围栏与前后杂文；解析失败计入重试
4. **mock 兜底**：real 调用最终失败返回 `None`，调用方落确定性 mock 模板——**页面永不因 LLM 故障而失败**；`LLM_MODE=mock` 时 `generate_json` 显式返回 mock 标记（`:66-72`）

## 3. 验证闭环

| 层级 | 工具 | 覆盖 |
|---|---|---|
| L0 语法 | `python -m compileall app scripts` | 全部源码可编译 |
| L1 离线 | `scripts/llm_offline_test.py` | LLM 不可达时全链路 mock 兜底可跑 |
| L2 单测 | `pytest tests`（**105 用例**） | Agent 单元/外部客户端/RBAC/管线结构/无演示词断言 |
| L3 链路 | `scripts/smoke_test.py` | 六条关键链路：正常生成、安全挂起审批、预算挂起审批、重规划 diff、断点恢复、toB 管线 |
| L4 压测 | `压测脚本.py` + `压测预热.py` | 读接口 QPS>300 & P95<100ms 达标验证（见 压测指标报告.md） |

## 4. Loop 改进记录（发现 → 修复 → 验证）

| # | 发现 | 修复 | 验证 |
|---|---|---|---|
| 1 | 排程溢出：行程过满时出现 `25:58`/`32:07` 错乱时间 | `compute_schedule` 溢出显示为"次日 HH:MM"（`agents/itinerary.py:54-57`，注释原文"防溢出"） | smoke 断言逐小时时间轴格式 |
| 2 | 高德 TLS 偶发抖动返回空结果，无静态库城市无法兜底 | Researcher 三次退避重试（`researcher.py` `time.sleep(0.8×(attempt+1))`）+ amap `_get` 内 2 次重试（`amap_client.py:36`） | 首页/行程书景点数量稳定；压测 S2 错误率 0.02% |
| 3 | 短途步行仍调用公交规划产生荒谬建议 | `compute_schedule`/commute 逻辑短途不调公交 | 行程书通勤建议合理性单测（`test_reasonableness.py`） |
| 4 | web_research 提取器对单行 HTML（行内标签不换行）整行当文本，解析失败 | `extract_rules` 增加 `_strip_tags` 兜底：原始 HTML 行剥标签后再匹配 | `tests/test_web_research.py::test_extract_rules_parses_fields` |
| 5 | 提取器采到标题行（"开放时间"）漏掉下一行真实数据 | 重写为"标题行触发 → 捕获下一数据行"状态机 | 同上单测断言 `8:30-17:00` 与 `提前 7 天` |
| 6 | Validator 瘦身后 Debate/Consultant/Compliance 读 `estimated_budget` 抛 None/NameError | 统一 `get_budget_payload(outputs)` 兜底（Budget 优先 → Validator 旧字段），debate 补 `or 0` | `test_no_demo_content.py` 2 用例 + smoke toB 链路 |
| 7 | smoke 对外部 API（LLM/飞猪/高德）90s 等待窗过紧，限流时段必挂 | `wait_for_status` 超时放宽至 240s（`scripts/smoke_test.py:33`） | 连续两次 smoke 全绿 |

## 5. 本轮（背景对齐批次）新增的 Loop 改进

- Sentiment 的 LLM 增强失败回退链路：本地舆情库 → LLM 增强 → UNKNOWN 保守文案，三级降级全部有单测覆盖（`test_sentiment_agent.py::test_unknown_fallback_conservative`）
- Validator→Budget 拆分采用"字段名不变 + 双兜底读取"策略，`test_budget_agent.py::test_reporter_budget_dual_read` 验证旧任务渲染不报错
- 预算挂起判定迁移到 Budget 节点后，审批恢复点由 `CheckpointStore._next_node` 自动指向 Validator，`smoke_test` 第 3 条链路验证通过
