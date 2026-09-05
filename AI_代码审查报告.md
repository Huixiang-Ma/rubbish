# AI 代码审查报告

> 版本：v1.0 ｜ 日期：2026-09-04 ｜ 审查范围：`backend/app`（重点 agents/services/api）
> 口径：每条 bug 均经源码核实与复现验证，杜绝虚构；"已修复"条目附验证方式；不构成本次问题的候选线索已在文末注明核实结论。

---

## 已修复（本轮审查中确认并修复）

### Bug 1：Validator 瘦身后下游 Agent 读预算字段崩溃
- **位置**：`backend/app/agents/debate.py:45,79`、`backend/app/agents/consultant.py:19,29`、`backend/app/agents/compliance.py:15`
- **现象/影响**：BudgetAgent 拆分后 `validation["estimated_budget"]` 变 None/键缺失，Debate 抛 `TypeError: '>' not supported between 'NoneType' and 'int'`（smoke toC 链路 FAIL）、Consultant 抛 `KeyError: 'estimated_budget'`（toB 链路 FAIL）
- **根因**：预算字段产出方从 Validator 迁移到 Budget，消费方仍直读 Validator 旧字段
- **修复建议**：统一兜底读取——`app/agents/base.py` 新增 `get_budget_payload(outputs)`（Budget 优先 → Validator 旧字段 → 空字典），四个消费方全部接入；Debate 的比较改为 `estimated_budget or 0`
- **验证方式**：`test_budget_agent.py::test_reporter_budget_dual_read`、smoke toC/toB 双管线全绿（pytest 105/105）

### Bug 2：前端生成按钮 `id="btnGo"` 重复
- **位置**：`frontend/index.html` 开始框内与新旧 go-row 各一个（重构残留）
- **现象/影响**：`getElementById` 永远命中第一个按钮，第二个是死按钮；用户点"开始规划"无响应或行为与视觉不符
- **根因**：改版时新开始框已含按钮，旧的 `go-row` 未删除
- **修复建议**：删除旧 go-row 整块，只保留开始框 footer 的唯一按钮（文案"AI 规划旅程"）
- **验证方式**：`grep -c 'id="btnGo"'` = 1；浏览器点击走真实生成链路

### Bug 3：smoke 对外部 API 的等待窗过紧（90 秒）
- **位置**：`backend/scripts/smoke_test.py:33`（`wait_for_status` 默认 timeout=90.0）
- **现象/影响**：LLM/飞猪/高德被限流时段（单稿 2-4 分钟），六条链路必挂，回归误报
- **根因**：等待窗按外部 API 健康期的单稿耗时（~55s）设定，未覆盖限流场景
- **修复建议**：放宽至 240s 并注明原因
- **验证方式**：连续两次 smoke 全绿（此前 90s 连挂两轮）

### Bug 4：web_research 提取器对单行 HTML 解析失败且采错字段
- **位置**：`backend/app/services/web_research.py`（`extract_rules` / `_TextExtractor`）
- **现象/影响**：①行内标签不换行的页面（`<h1>开放时间</h1>` 同行）整行被当文本，剥不出纯标题；②只匹配标题关键词本身，采到"开放时间"标题行而漏掉下一行真实数据"旺季 8:30-17:00…"
- **根因**：html.parser 按文本节点收集时未剥行内标签；关键词匹配缺少"标题触发 → 捕获下一数据行"的状态机
- **修复建议**：增加 `_strip_tags` 兜底（剥标签取纯文本）+ 重写匹配为状态机（标题关键词触发、含数字的下一行作为数据采集）
- **验证方式**：`tests/test_web_research.py::test_extract_rules_parses_fields` 断言 `8:30-17:00` 与 `提前 7 天` 同时采到

### Bug 5：smoke 断言的章节从未被渲染（先行失败）
- **位置**：`backend/scripts/smoke_test.py:71` 断言 `"交通与住宿参考"`；`backend/app/services/markdown_reporter.py`（无该章节渲染）
- **现象/影响**：历史 `travel_plan.md` 输出中从未出现该章节（已核实 466 个旧任务 0 命中），回归基线本身就是坏的
- **根因**：断言先写、章节渲染在改版中遗失，形成"必失败断言"长期被掩盖
- **修复建议**：Reporter 补"### 2.3 交通与住宿参考"小节——渲染 Validator/Budget 的 `travel_advice`（城际高铁/飞行时长对比、往返预算、和风天气 notes、住宿分档口径）
- **验证方式**：smoke 六链路全绿；人工核对行程书出现该小节

---

## 核实无误的候选（不构成 bug，记录核实结论）

- **`recommend_hotel` 的 `adjusted` 恒为 True？** 核实为否：`travel_context_service.py:143-147` 循环中命中可负担档位即 `adjusted=False`，仅预算低于最低档时保持 True（强制经济型）。逻辑与注释一致。
- **尾段并行 `pool.map` 与断点恢复边界**：`plan_processor.py:_run_tail`——并行分支任一 Agent 异常会整体 fail-fast（无部分标记），恢复时走顺序补跑分支；行为安全，代价是重复执行（幂等可接受）。
- **`markdown_reporter` 编号变量**：toB 6/7、toC 带 Mood 7/8、不带 6/7——逐分支核对无跳号（舆情章节插入后已同步 +1）。
- **`economy_total`/`approval_required` 在 travelers>2 的口径**：实测 4 人预算 12000 → 9800 元不挂起（住宿按 rooms=2 折算、餐饮按人数线性），口径自洽；若业务认为人均口径更合理再议，非缺陷。
- **`fliggy_client` 签名重试与缓存 TTL**：10 分钟内存缓存 + 失败单点串行重试一轮，实测单次超时（32.6s）后重试成功（1.8s），行为符合设计。

## 仍存在的已知限制（记录，不在本轮修）

1. **`city_photo` 的 0.4s 限速器为进程内实现**：多实例部署时 QPS 保护会按实例数放大，需改 Redis 分布式限速（压测指标报告已提示）
2. **首页 P95 = 98ms 贴线**：如需余量可将 GZip 压缩级别 6→1 或改 zstd 预压缩
3. **读基准 QPS 受单 Python 压测进程上限约束**：多进程分片已验证 1600+ RPS 聚合，服务端未见瓶颈
