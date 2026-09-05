<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>多 Agent 文旅行程规划系统 · 项目白皮书</title>
<style>:root{
  --paper:#faf7f0; --card:#ffffff; --ink:#1f3d36; --ink2:#2f5a51;
  --muted:#6b7f7a; --line:#e3ded2; --teal:#2f8f83; --teal-soft:#e6f3f0;
  --cinnabar:#b23a2e; --cinnabar-soft:#fbeae7; --gold:#a8842c; --gold-soft:#faf1dc;
  --warn:#b8781f; --warn-soft:#fdf3e2;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"PingFang SC","Microsoft YaHei","Hiragino Sans GB","Source Han Sans SC",system-ui,-apple-system,sans-serif;
  font-size:15px; line-height:1.75;
}
.layout{display:flex; max-width:1440px; margin:0 auto; align-items:flex-start}
.toc{
  position:sticky; top:0; width:270px; flex:0 0 270px; height:100vh; overflow-y:auto;
  background:#fff; border-right:1px solid var(--line); padding:26px 18px 60px;
}
.toc h3{font-size:13px; letter-spacing:2px; color:var(--muted); margin:0 0 14px; font-weight:600}
.toc a{
  display:block; text-decoration:none; color:var(--ink2); font-size:13.5px;
  padding:6px 10px; border-radius:6px; border-left:2px solid transparent; margin-bottom:1px;
}
.toc a:hover{background:var(--teal-soft); color:var(--teal)}
.toc a.active{background:var(--teal-soft); color:var(--teal); border-left-color:var(--teal); font-weight:600}
.toc a.sub{padding-left:24px; font-size:12.5px; color:var(--muted)}
.toc a.sub:hover{color:var(--teal)}
.toc .brand{font-size:16px; font-weight:700; color:var(--ink); margin-bottom:4px; letter-spacing:1px}
.toc .brand-sub{font-size:11.5px; color:var(--muted); margin-bottom:22px}
.toc .toc{font-size:13px}
main{flex:1; min-width:0; padding:0 46px 100px}
.hero{padding:52px 0 30px; border-bottom:2px solid var(--line); margin-bottom:34px}
.hero h1{font-size:31px; margin:0 0 10px; letter-spacing:1px}
.hero p{margin:0; color:var(--muted); font-size:14.5px}
h2{
  font-size:22px; margin:52px 0 8px; padding-top:26px; border-top:1px solid var(--line);
  scroll-margin-top:20px; letter-spacing:.5px;
}
h2:first-of-type{border-top:none}
h3{font-size:17.5px; margin:34px 0 10px; color:var(--ink2); scroll-margin-top:20px}
h4{font-size:15.5px; margin:0 0 4px}
p{margin:8px 0}
code{background:#f2efe6; padding:1px 6px; border-radius:4px; font-size:13px; font-family:"JetBrains Mono",Consolas,monospace}
pre{
  background:#1f3d36; color:#e8f2ef; border-radius:10px; padding:16px 18px; overflow-x:auto;
  font-size:13px; line-height:1.65; font-family:"JetBrains Mono",Consolas,monospace;
}
pre code{background:none; color:inherit; padding:0}
table{width:100%; border-collapse:collapse; margin:14px 0 20px; font-size:13.6px; background:var(--card)}
th,td{border:1px solid var(--line); padding:9px 11px; text-align:left; vertical-align:top}
th{background:var(--teal-soft); color:var(--ink); font-weight:600; white-space:nowrap}
tbody tr:nth-child(even){background:#fcfbf7}
blockquote{
  margin:16px 0; border-left:3px solid var(--teal); background:var(--teal-soft);
  padding:12px 16px; border-radius:0 8px 8px 0; font-size:14px;
}
ul{margin:8px 0; padding-left:20px}
ol{margin:8px 0; padding-left:22px}
li{margin:4px 0}
hr{border:none; border-top:1px solid var(--line); margin:30px 0}
strong{color:var(--ink)}
</style>
</head>
<body>
<div class="layout">
  <nav class="toc">
    <div class="brand">多 Agent 文旅系统</div>
    <div class="brand-sub">文档导航</div>
    <h3>目录</h3>
    <div class="toc">
<ul>
<li><a href="#_1">摘要</a></li>
<li><a href="#1">1. 背景与问题</a><ul>
<li><a href="#11">1.1 行业现状</a></li>
<li><a href="#12">1.2 本项目的回答</a></li>
</ul>
</li>
<li><a href="#2">2. 系统概览</a><ul>
<li><a href="#21">2.1 总体架构</a></li>
<li><a href="#22-9-agent-reporter">2.2 双管线（9 Agent + Reporter）</a></li>
</ul>
</li>
<li><a href="#3">3. 核心技术</a><ul>
<li><a href="#31-11">3.1 11 态状态机与断点恢复</a></li>
<li><a href="#32-servicessafety_servicepy">3.2 安全防御体系（services/safety_service.py）</a></li>
<li><a href="#33">3.3 幂等与并发安全</a></li>
<li><a href="#34-llm-servicesllm_clientpy">3.4 LLM 接入层（services/llm_client.py）</a></li>
<li><a href="#35-servicestravel_context_servicepy">3.5 确定性计算内核（services/travel_context_service.py 等）</a></li>
<li><a href="#36-hitl">3.6 审计与可解释（HITL 闭环）</a></li>
</ul>
</li>
<li><a href="#4">4. 产品能力</a><ul>
<li><a href="#41-toc">4.1 toC 游客端</a></li>
<li><a href="#42-tob">4.2 toB 企业端（八页签工作台）</a></li>
</ul>
</li>
<li><a href="#5">5. 工程质量与安全合规</a><ul>
<li><a href="#51">5.1 测试体系</a></li>
<li><a href="#52">5.2 可观测性</a></li>
<li><a href="#53">5.3 安全与合规</a></li>
</ul>
</li>
<li><a href="#6">6. 性能与可靠性</a><ul>
<li><a href="#61">6.1 压测结论（第二轮，方法修正后）</a></li>
<li><a href="#62">6.2 生成链路</a></li>
<li><a href="#63">6.3 口径声明（诚实边界）</a></li>
</ul>
</li>
<li><a href="#7">7. 演进路线</a></li>
<li><a href="#a">附录 A · 快速启动</a></li>
<li><a href="#b">附录 B · 关键代码索引</a></li>
</ul>
</div>

  </nav>
  <main>
    <div class="hero">
      <h1>多 Agent 文旅行程规划系统 · 项目白皮书</h1>
      <p>基于 backend/app 实际代码核实整理</p>
    </div>
    <p><strong>Multi-Agent Travel Planner System — Project Whitepaper</strong></p>
<blockquote>
<p>版本：1.0 ｜ 日期：2026-09-05 ｜ 密级：公开
本文档系统阐述项目的产品定位、技术架构、核心机制、工程质量、性能数据与演进路线。
全部技术论断均可追溯至 <code>backend/app</code> 源码；性能数据来源《压测指标报告.md》，口径随文标注。</p>
</blockquote>
<hr />
<h2 id="_1">摘要</h2>
<p>本系统是一套 <strong>多 Agent 协作的文旅行程规划平台</strong>，服务两类用户：</p>
<ul>
<li><strong>toC 游客端</strong>：一句话需求 → 完整可执行行程书（含预算账本、舆情避坑、决策辩论、翻车预演、人生剧本）；</li>
<li><strong>toB 企业端</strong>：旅行社与管理者使用的顾问工作台（方案管理、人工审批、安全治理、合规审计、白标交付、经营看板）。</li>
</ul>
<p>项目的工程定位是：<strong>将"AI 生成攻略"从一次不可控的对话，改造为可审计、可恢复、能防攻击的生产流水线</strong>。核心手段包括：</p>
<ol>
<li><strong>确定性工程兜底</strong>：预算核算、时空可行性校验全部由确定性代码完成，LLM 只负责叙事与决策论证；</li>
<li><strong>状态机 + Checkpoint + 原子写</strong>：长链路任一步骤崩溃均可断点续跑，产物写入具备崩溃一致性；</li>
<li><strong>安全分级防御</strong>：外部内容默认不可信，注入攻击按高/中/低三级处置，全程审计留痕；</li>
<li><strong>人在回路（HITL）</strong>：超预算、涉安全任务自动挂起，由企业端审批放行，审批带版本号防并发资损；</li>
<li><strong>异步解耦</strong>：收单与生产分离，读接口/提交接口压测全部达标（QPS&gt;300，P95&lt;100ms）。</li>
</ol>
<hr />
<h2 id="1">1. 背景与问题</h2>
<h3 id="11">1.1 行业现状</h3>
<p>传统行程规划依赖人工顾问，效率低、成本高、标准不一；LLM 出现后"AI 写攻略"成为热点，但直接落地存在系统性缺陷：</p>
<table>
<thead>
<tr>
<th>问题</th>
<th>表现</th>
<th>后果</th>
</tr>
</thead>
<tbody>
<tr>
<td>算不准</td>
<td>LLM 排"上午故宫 + 下午长城当天往返"</td>
<td>行程不可执行</td>
</tr>
<tr>
<td>不可控</td>
<td>输出无法复现、无过程、无责任人</td>
<td>企业不敢用</td>
</tr>
<tr>
<td>不安全</td>
<td>用户输入夹带指令可劫持链路</td>
<td>提示词泄露、结果被操纵</td>
</tr>
<tr>
<td>不健壮</td>
<td>长链路崩溃即全量重来</td>
<td>成本失控</td>
</tr>
<tr>
<td>不可追</td>
<td>谁改了什么无从查证</td>
<td>无法审计合规</td>
</tr>
<tr>
<td>有资损风险</td>
<td>重复提交、重复审批</td>
<td>状态脏、真金白银受损</td>
</tr>
</tbody>
</table>
<h3 id="12">1.2 本项目的回答</h3>
<p>用<strong>可工程化的流水线</strong>而非"更聪明的 Prompt"解决上述问题——把"一次对话"拆成"一条带状态、带检查点、带审计的生产线"。</p>
<hr />
<h2 id="2">2. 系统概览</h2>
<h3 id="21">2.1 总体架构</h3>
<pre><code>┌─────────────┐   ┌─────────────┐
│  toC 游客端  │   │  toB 企业端  │   ← 原生单文件前端（FastAPI 静态托管）
└──────┬──────┘   └──────┬──────┘
       │ REST / SSE      │ REST（Bearer Token + RBAC）
       ▼                 ▼
┌──────────────────────────────────────────┐
│              FastAPI 网关                 │
│   /api/plans · /api/safety · /api/auth   │
│   /api/admin · /api/services · /api/...  │
└───────┬──────────────┬──────────────────┘
        │ enqueue      │ ack / reclaim
        ▼              ▼
┌──────────────┐   ┌──────────────────────┐
│  任务队列      │◄──│  Worker 消费循环       │
│ memory/Redis │   │  Redis 锁 + 幂等兜底    │
└──────────────┘   └──────────┬───────────┘
                              ▼
┌──────────────────────────────────────────┐
│           PlanProcessor 双管线             │
│  toC: Intake→…→Debate/Mood→Reporter       │
│  toB: Intake→…→Consultant/Compliance→... │
│  每个节点：Agent 执行 → scan_payload      │
│          → checkpoint 落盘 → 下一节点      │
└──────────────┬───────────────────────────┘
               ▼
┌──────────────────────────────────────────┐
│  存储层：state.json + agent_outputs/     │
│  + travel_plan.md + .sha256 + audit.log  │
│  （原子写，可选 PostgreSQL/pgvector）      │
└──────────────────────────────────────────┘
</code></pre>
<h3 id="22-9-agent-reporter">2.2 双管线（9 Agent + Reporter）</h3>
<p><strong>toC 管线</strong>：</p>
<pre><code>Intake → Researcher → Planner → Itinerary → Budget → Validator → Sentiment
      → [Debate ‖ Mood]（尾段并行）→ Reporter
</code></pre>
<p><strong>toB 管线</strong>：</p>
<pre><code>Intake → Researcher → Planner → Itinerary → Budget → Validator → Sentiment
      → [Consultant ‖ Compliance]（尾段并行）→ Reporter
</code></pre>
<p>各节点职责：</p>
<table>
<thead>
<tr>
<th>节点</th>
<th>职责</th>
<th>实现方式</th>
</tr>
</thead>
<tbody>
<tr>
<td>Intake</td>
<td>需求解析与归一化（去"市"后缀、天数/人数夹取、偏好去重、<code>transit_first</code>/<code>avoid_early_rise</code> 标志）</td>
<td>确定性代码</td>
</tr>
<tr>
<td>Researcher</td>
<td>景点调研：高德实时 POI + 官网白名单抓取（故宫/八达岭两站，默认关闭）</td>
<td>外部 + LLM 归纳</td>
</tr>
<tr>
<td>Planner</td>
<td>景点聚类主题分组（<code>geo_cluster_v19</code>）</td>
<td>LLM + 确定性排序</td>
</tr>
<tr>
<td>Itinerary</td>
<td>逐日排期（含餐饮推荐，时间槽排序）</td>
<td>确定性 + LLM</td>
</tr>
<tr>
<td>Budget</td>
<td>预算分项核算 + 经济口径建议，超支触发挂起</td>
<td><strong>纯确定性</strong></td>
</tr>
<tr>
<td>Validator</td>
<td>时空校验（跨区/通勤/强度/打车）+ 翻车预演 what_if</td>
<td><strong>纯确定性</strong></td>
</tr>
<tr>
<td>Sentiment</td>
<td>舆情分级（本地库 + LLM 增强，未收录景点保守口径）</td>
<td>混合</td>
</tr>
<tr>
<td>Debate / Mood</td>
<td>toC 叙事：决策辩论、情绪弧线剧本</td>
<td>LLM</td>
</tr>
<tr>
<td>Consultant / Compliance</td>
<td>toB 叙事：顾问话术、合规审计摘要</td>
<td>LLM</td>
</tr>
<tr>
<td>Reporter</td>
<td>汇总全部结构化输出，单点原子写 <code>travel_plan.md</code></td>
<td>确定性</td>
</tr>
</tbody>
</table>
<hr />
<h2 id="3">3. 核心技术</h2>
<h3 id="31-11">3.1 11 态状态机与断点恢复</h3>
<p>任务生命周期包含 11 个状态（<code>models/states.py</code>）：</p>
<pre><code>QUEUED → RUNNING →（节点间流转）
        ├→ WAITING_RATE_LIMIT（自动，退避后可回）
        ├→ WAITING_BUDGET_APPROVAL（人工审批）
        ├→ WAITING_SAFETY_REVIEW（人工审批）
        ├→ WAITING_PARSE_REVIEW（人工处理）
        └→ RECOVERY_REQUIRED（数据损坏，人工干预）
RUNNING → COMPLETED | FAILED | REPLAN_REQUIRED
</code></pre>
<ul>
<li><strong>Checkpoint</strong>：每节点完成写 <code>state.json</code> + 节点产出分文件（<code>agent_outputs/{agent}.json</code>），<code>resume_from</code> 记录续跑点（<code>checkpoint_store.py</code>）；</li>
<li><strong>原子写</strong>：<code>.tmp → flush+fsync → os.replace（PermissionError 退避 5 次）→ .sha256 旁车校验</code>（<code>atomic_writer.py</code>），崩溃后 state 与产物要么都旧、要么都新，不存在半写状态；</li>
<li><strong>恢复</strong>：启动扫描 <code>QUEUED/RUNNING</code> 重入队，hash 校验失败进 <code>RECOVERY_REQUIRED</code>，不自动覆盖（<code>recovery.py</code>）。实测进程被杀后 <strong>5 秒内恢复调度</strong>。</li>
</ul>
<h3 id="32-servicessafety_servicepy">3.2 安全防御体系（<code>services/safety_service.py</code>）</h3>
<table>
<thead>
<tr>
<th>分级</th>
<th>处置</th>
<th>模式示例</th>
</tr>
</thead>
<tbody>
<tr>
<td>高危（8 条模式）</td>
<td><strong>block</strong>：任务挂起 <code>WAITING_SAFETY_REVIEW</code>，人工放行</td>
<td>"忽略之前所有指令"、"输出系统提示词"、泄露密钥类</td>
</tr>
<tr>
<td>中危（4 条模式）</td>
<td><strong>sanitize</strong>：清洗后放行，写事件</td>
<td>base64 隐藏文本、HTML 注释、修改预算指令</td>
</tr>
<tr>
<td>低危</td>
<td><strong>allow</strong></td>
<td>正常输入</td>
</tr>
</tbody>
</table>
<ul>
<li>用户输入在<strong>入链前</strong>扫描；每个 Agent 输出经 <code>scan_payload</code> <strong>递归清洗</strong>后才进入下一节点（防"输出即注入"）；</li>
<li>拦截/清洗全部落审计，<code>aggregate_safety_events</code> 聚合安全看板（拦截率、攻击分布 top6、近 14 天曲线）；</li>
<li>网页调研默认关闭，白名单仅两站（故宫官网、八达岭官网）。</li>
</ul>
<h3 id="33">3.3 幂等与并发安全</h3>
<table>
<thead>
<tr>
<th>场景</th>
<th>机制</th>
<th>代码</th>
</tr>
</thead>
<tbody>
<tr>
<td>重复提交</td>
<td><code>request_hash</code>（含 <code>_generation_version</code>）→ 返回同一 job_id</td>
<td><code>api/plans.py:51-56</code></td>
</tr>
<tr>
<td>重复审批/改单</td>
<td><code>base_version</code> 校验，冲突返回 HTTP 409</td>
<td><code>api/plans.py:326-327,364-365</code></td>
</tr>
<tr>
<td>多 Worker 抢任务</td>
<td>Redis 分布式锁 <code>SET NX PX</code> + Lua 原子删除；PEL 消息由 <code>XAUTOCLAIM</code> 认领，at-least-once + 幂等兜底</td>
<td><code>services/distributed.py</code>、<code>queue_client.py</code></td>
</tr>
</tbody>
</table>
<h3 id="34-llm-servicesllm_clientpy">3.4 LLM 接入层（<code>services/llm_client.py</code>）</h3>
<ul>
<li><strong>mock-first</strong>：无 key/非 real 模式即走本地模板，主链路离线可跑；</li>
<li><strong>双通道降级</strong>：<code>httpx</code> 失败自动降级 raw socket 自解 chunked 通道，解决容器长连接空闲 19 秒被切断问题（实测 70s+ 长生成稳定）；</li>
<li><strong>重试退避</strong>：<code>max_retries+1</code> 次指数退避；固定系统提示"只输出合法 JSON"+ <code>response_format</code> 约束。</li>
</ul>
<h3 id="35-servicestravel_context_servicepy">3.5 确定性计算内核（<code>services/travel_context_service.py</code> 等）</h3>
<ul>
<li><strong>预算分项</strong>：城际 + 酒店（按预算档位推荐）+ 市内交通 + 门票 + 餐饮；经济口径（300 元/晚住宿、100 元/天餐饮、市内交通减半）；</li>
<li><strong>时空校验</strong>：单日 &gt;3 景点告警；跨区 &gt;15km（haversine）告警；单腿打车超阈值、全天通勤超阈值告警；</li>
<li><strong>挂起触发</strong>：标准口径超预算 <strong>且</strong> 经济口径也超预算 → <code>WAITING_BUDGET_APPROVAL</code>；</li>
<li><strong>翻车预演</strong>：天气、通勤超时、闭馆替补（取未选景点首位）三类 B 计划。</li>
</ul>
<h3 id="36-hitl">3.6 审计与可解释（HITL 闭环）</h3>
<ul>
<li>全量审计：<code>audit.log</code> 追加式记录（谁、何时、什么动作、详情 JSON），CSV 导出含 UTF-8 BOM 兼容 Excel；</li>
<li>RBAC：游客/顾问/主管/管理员四级；审批仅 supervisor/admin，改单与反馈限 consultant 及以上；</li>
<li>决策溯源：行程书含"决策辩论"章节，toB 详情页节点步骤条 + 父子版本行级 diff（<code>difflib.SequenceMatcher</code>）；</li>
<li>反事实对照卡、虚拟游客 swarm 反馈、角色名导团点评（体验层扩展）。</li>
</ul>
<hr />
<h2 id="4">4. 产品能力</h2>
<h3 id="41-toc">4.1 toC 游客端</h3>
<table>
<thead>
<tr>
<th>能力</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td>一句话成行</td>
<td>目的地/天数/预算/偏好/心情 → 异步生成行程书</td>
</tr>
<tr>
<td>服务大厅</td>
<td>火车票/机票/景点/商家/娱乐五窗口（演示口径，60s 结果缓存）</td>
</tr>
<tr>
<td>携程式行程视图</td>
<td>结构化 itinerary + 实时酒店（高德 POI/静态库）</td>
</tr>
<tr>
<td>地图模式</td>
<td>每日景点坐标标注；周边 POI（美食/车位/厕所）</td>
</tr>
<tr>
<td>决策辩论</td>
<td>规划方 vs 游客方多议题辩论 + SSE 直播 + 投票计票</td>
</tr>
<tr>
<td>反事实后悔药</td>
<td>换一种安排的对照卡</td>
</tr>
<tr>
<td>虚拟游客 swarm</td>
<td>三组画像对行程的踩点反馈</td>
</tr>
<tr>
<td>名导团</td>
<td>角色化导览点评 + 多轮对话追问</td>
</tr>
</tbody>
</table>
<h3 id="42-tob">4.2 toB 企业端（八页签工作台）</h3>
<table>
<thead>
<tr>
<th>页签</th>
<th>能力</th>
</tr>
</thead>
<tbody>
<tr>
<td>方案列表</td>
<td>任务索引（状态/客户/租户筛选，按更新时间倒序）</td>
</tr>
<tr>
<td>审核台</td>
<td>聚合待审批队列（预算/安全），一键批准/驳回，版本冲突 409</td>
</tr>
<tr>
<td>安全看板</td>
<td>拦截率、攻击分布、趋势曲线</td>
</tr>
<tr>
<td>合规审计</td>
<td>全量审计导出 CSV</td>
</tr>
<tr>
<td>客户之声</td>
<td>好评/投诉聚合（praise/complaint 计数）</td>
</tr>
<tr>
<td>白标交付</td>
<td>企业品牌 + 顾问署名 + 中立声明注入，sha256 校验行留痕</td>
</tr>
<tr>
<td>经营看板</td>
<td>完成率、每日创建、状态分布、客户分布</td>
</tr>
<tr>
<td>客户管理</td>
<td>客户维度任务视图</td>
</tr>
</tbody>
</table>
<hr />
<h2 id="5">5. 工程质量与安全合规</h2>
<h3 id="51">5.1 测试体系</h3>
<ul>
<li><strong>20 个 pytest 测试文件</strong>（<code>backend/tests/</code>），覆盖：Agent 单测（intake/budget/validator/sentiment/planner…）、管线契约（toC/toB 章节断言）、RBAC、安全过滤、服务真实调用、配置、外部客户端、幂等、断点恢复、内容溯源等；</li>
<li><strong>8 条 smoke 链路</strong>（<code>scripts/smoke_test.py</code>）：正常链路 / 注入挂起 / 安全放行 / 预算挂起与重复审批 409 / 增量重规划 diff / 断点恢复 / 心情剧本与投票 / toB 管线；</li>
<li>CI 工作流自动执行编译自检 + 测试 + smoke。</li>
</ul>
<h3 id="52">5.2 可观测性</h3>
<ul>
<li>Prometheus <code>/metrics</code>（METRICS_ENABLED 开关）：提交数、审批数、完成/失败计数、节点耗时直方图；</li>
<li>JSON 结构化日志（<code>services/jsonlog.py</code>）全链路事件（创建/挂起/审批/恢复/认领/ack…）。</li>
</ul>
<h3 id="53">5.3 安全与合规</h3>
<ul>
<li>输入分级过滤 + 输出递归清洗（§3.2）；</li>
<li>CORS 显式关闭凭据（防跨域带 Cookie 组合绕过）；</li>
<li>演示级认证（Bearer Token + HMAC 一致比较 <code>hmac.compare_digest</code>，7 天过期，RBAC 角色校验）；</li>
<li>白标导出含中立声明与 sha256 校验行，交付留痕写入审计。</li>
</ul>
<hr />
<h2 id="6">6. 性能与可靠性</h2>
<h3 id="61">6.1 压测结论（第二轮，方法修正后）</h3>
<table>
<thead>
<tr>
<th>端点</th>
<th>QPS</th>
<th>P95 延迟</th>
<th>达标（&gt;300 / &lt;100ms）</th>
</tr>
</thead>
<tbody>
<tr>
<td>健康检查/读基准</td>
<td><strong>572.5</strong></td>
<td><strong>94ms</strong></td>
<td>✅</td>
</tr>
<tr>
<td>首页（GZip 预压缩）</td>
<td><strong>350.2</strong></td>
<td><strong>98ms</strong></td>
<td>✅</td>
</tr>
<tr>
<td>实时 POI 窗口</td>
<td><strong>547.7</strong></td>
<td><strong>67ms</strong></td>
<td>✅</td>
</tr>
<tr>
<td>提交接口（保守口径）</td>
<td><strong>246</strong></td>
<td>—</td>
<td>口径内达标</td>
</tr>
</tbody>
</table>
<p>优化手段：首页 GZip 字节预生成缓存（127KB→36KB）、服务窗口 60s 结果缓存、全局 GZip 中间件（minimum_size=1024）。</p>
<h3 id="62">6.2 生成链路</h3>
<ul>
<li>8 并发任务 100% 成功，端到端单稿约 <strong>55 秒</strong>（real 模式）；</li>
<li>断点恢复 <strong>5 秒内</strong>恢复调度；</li>
<li>增量重规划 mock 口径降约 <strong>23%</strong> 耗时。</li>
</ul>
<h3 id="63">6.3 口径声明（诚实边界）</h3>
<ul>
<li><strong>QPS 指标仅覆盖读接口与提交接口，不覆盖生成吞吐</strong>（生成耗时由大模型延迟决定）；</li>
<li>提交接口口径：POST /api/plans，含 state.json 原子落盘与入队，不含生成；</li>
<li>通勤时间、票价、天气为<strong>本地静态估算</strong>口径；LLM 默认 mock，配置 key 即切换真实模型；</li>
<li>第一轮压测暴露 WSL2 建连串行化陷阱，最终数据以修正方法后的第二轮为准。</li>
</ul>
<hr />
<h2 id="7">7. 演进路线</h2>
<table>
<thead>
<tr>
<th>阶段</th>
<th>事项</th>
<th>预留点</th>
</tr>
</thead>
<tbody>
<tr>
<td>近</td>
<td>pgvector 语义检索替换静态景点 JSON</td>
<td><code>database_url</code> + 镜像层</td>
</tr>
<tr>
<td>近</td>
<td>Redis Checkpointer + 分布式限速</td>
<td><code>queue_client</code> 双实现、限速点收敛</td>
</tr>
<tr>
<td>中</td>
<td>MCP 标准化数据源接入（高德/携程/12306）</td>
<td><code>external_*_provider</code> 三组扩展点</td>
</tr>
<tr>
<td>中</td>
<td>推理模型用于 Debate/Validator</td>
<td>LLM 配置参数化</td>
</tr>
<tr>
<td>中</td>
<td>OpenTelemetry trace 定位慢节点</td>
<td>Prometheus + JSON 日志已就绪</td>
</tr>
<tr>
<td>远</td>
<td>AI 红队影子评测</td>
<td>安全拦截统计已就绪</td>
</tr>
<tr>
<td>远</td>
<td>多模态/以图规划</td>
<td><code>external_ocr_provider</code> 扩展点</td>
</tr>
</tbody>
</table>
<hr />
<h2 id="a">附录 A · 快速启动</h2>
<pre><code class="language-bash">cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000    # 零配置即可运行（memory 队列 + mock LLM）
# 游客端 http://127.0.0.1:8000/  企业端 http://127.0.0.1:8000/b
# 演示账号：admin/wl2026 · supervisor/sv2026 · consultant/ct2026 · 旅者/123456
</code></pre>
<h2 id="b">附录 B · 关键代码索引</h2>
<table>
<thead>
<tr>
<th>模块</th>
<th>文件</th>
</tr>
</thead>
<tbody>
<tr>
<td>双管线定义</td>
<td><code>services/pipelines.py</code></td>
</tr>
<tr>
<td>管线编排</td>
<td><code>services/plan_processor.py</code></td>
</tr>
<tr>
<td>状态机</td>
<td><code>models/states.py</code></td>
</tr>
<tr>
<td>状态存储/审计</td>
<td><code>services/checkpoint_store.py</code></td>
</tr>
<tr>
<td>原子写</td>
<td><code>services/atomic_writer.py</code></td>
</tr>
<tr>
<td>断点恢复</td>
<td><code>services/recovery.py</code></td>
</tr>
<tr>
<td>安全</td>
<td><code>services/safety_service.py</code></td>
</tr>
<tr>
<td>队列</td>
<td><code>services/queue_client.py</code></td>
</tr>
<tr>
<td>分布式锁</td>
<td><code>services/distributed.py</code></td>
</tr>
<tr>
<td>LLM 接入</td>
<td><code>services/llm_client.py</code></td>
</tr>
<tr>
<td>确定性计算</td>
<td><code>services/travel_context_service.py</code></td>
</tr>
<tr>
<td>Agent 实现</td>
<td><code>agents/{intake,researcher,planner,itinerary,budget,validator,sentiment,debate,mood,consultant,compliance}.py</code></td>
</tr>
<tr>
<td>业务接口</td>
<td><code>api/{plans,auth,admin,experience,safety,services,integrations}.py</code></td>
</tr>
<tr>
<td>Worker</td>
<td><code>workers/plan_worker.py</code></td>
</tr>
</tbody>
</table>
<hr />
<p><em>本文档由项目源码与压测报告整理而成，供评审、答辩、对外交流使用。</em></p>
  </main>
</div>
<script>
const links=[...document.querySelectorAll('.toc a')];
const heads=[...document.querySelectorAll('main h2,h3')].filter(h=>h.id);
window.addEventListener('scroll',()=>{
  let cur=null;
  for(const h of heads){ if(h.getBoundingClientRect().top<=90) cur=h.id; }
  links.forEach(a=>a.classList.toggle('active', a.getAttribute('href')==='#'+(cur||'')));
});
</script>
</body>
</html>