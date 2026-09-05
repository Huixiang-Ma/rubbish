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
<li><a href="#23">2.3 技术栈</a></li>
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
<li><a href="#41-toc-7">4.1 toC 游客端（7 页签行程书 + 服务大厅）</a></li>
<li><a href="#42-tob-9">4.2 toB 企业端（9 页签工作台）</a></li>
</ul>
</li>
<li><a href="#5-api">5. 数据结构与 API</a><ul>
<li><a href="#51-modelsschemaspy">5.1 核心数据模型（models/schemas.py）</a></li>
<li><a href="#52-datajobsjob_id">5.2 任务目录结构（data/jobs/{job_id}/）</a></li>
<li><a href="#53-statejson">5.3 state.json 关键字段</a></li>
<li><a href="#54-rest-api-35-1-sse">5.4 REST API 清单（约 35 个端点 + 1 个 SSE）</a></li>
</ul>
</li>
<li><a href="#6">6. 部署架构与工程质量</a><ul>
<li><a href="#61-docker-backenddockerfile">6.1 Docker 部署（backend/Dockerfile）</a></li>
<li><a href="#62">6.2 项目目录结构</a></li>
<li><a href="#63-appconfigpypydantic-settings">6.3 配置（app/config.py，pydantic-settings）</a></li>
<li><a href="#64">6.4 测试体系</a></li>
<li><a href="#65">6.5 可观测性</a></li>
</ul>
</li>
<li><a href="#7">7. 性能与可靠性</a><ul>
<li><a href="#71">7.1 压测方法</a></li>
<li><a href="#72">7.2 第一轮结果（优化前基线）</a></li>
<li><a href="#73">7.3 第二轮优化与达标结果</a></li>
<li><a href="#74">7.4 过程中发现的环境事实（影响压测口径）</a></li>
<li><a href="#75">7.5 容量短板与扩容建议</a></li>
<li><a href="#76">7.6 可靠性指标</a></li>
</ul>
</li>
<li><a href="#8">8. 安全与合规</a></li>
<li><a href="#9">9. 诚实边界与免责</a></li>
<li><a href="#10">10. 演进路线</a></li>
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
<p>版本：2.0 ｜ 日期：2026-09-05 ｜ 密级：公开
本文档系统阐述项目的产品定位、技术架构、核心机制、数据结构、API 清单、部署架构、功能规格、性能数据与演进路线。
全部技术论断均可追溯至 <code>backend/app</code> 源码；性能数据来源《压测指标报告.md》，口径随文标注。</p>
</blockquote>
<hr />
<h2 id="_1">摘要</h2>
<p>本系统是一套 <strong>多 Agent 协作的文旅行程规划平台</strong>，服务两类用户：</p>
<ul>
<li><strong>toC 游客端</strong>：一句话需求 → 完整可执行行程书（7 页签：总览/逐日/账本/辩论实录/心情剧本/B计划/清单）；</li>
<li><strong>toB 企业端</strong>：旅行社与管理者使用的 9 页签顾问工作台（方案列表、流程状态图、HITL 审核台、安全看板、合规审计、客户之声、白标交付、经营看板、客户管理）。</li>
</ul>
<p>项目的工程定位是：<strong>将"AI 生成攻略"从一次不可控的对话，改造为可审计、可恢复、能防攻击的生产流水线</strong>。核心手段包括：</p>
<ol>
<li><strong>确定性工程兜底</strong>：预算核算、时空可行性校验全部由确定性代码完成，LLM 只负责叙事与决策论证；</li>
<li><strong>状态机 + Checkpoint + 原子写</strong>：长链路任一步骤崩溃均可断点续跑，产物写入具备崩溃一致性；</li>
<li><strong>安全分级防御</strong>：外部内容默认不可信，注入攻击按高/中/低三级处置，全程审计留痕；</li>
<li><strong>人在回路（HITL）</strong>：超预算、涉安全任务自动挂起，由企业端审批放行，审批带版本号防并发资损；</li>
<li><strong>异步解耦</strong>：收单与生产分离，读接口/提交接口压测全部达标（QPS&gt;300，P95&lt;100ms）。</li>
</ol>
<p><strong>关键数据</strong>：读接口 QPS 572（P95 94ms）、首页 350（P95 98ms）、实时 POI 548（P95 67ms）；生成链路 8 并发 100% 成功，单稿约 55 秒；断点恢复 5 秒内调度；已生成 456+ 份真实行程书；20 个 pytest 测试文件 + 8 条 smoke 链路。</p>
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
│  / (index)  │   │  /b (admin) │
└──────┬──────┘   └──────┬──────┘
       │ REST / SSE      │ REST（Bearer Token + RBAC）
       ▼                 ▼
┌──────────────────────────────────────────┐
│              FastAPI 网关                 │
│   /api/plans · /api/safety · /api/auth   │
│   /api/admin · /api/services · /api/...  │
│   GZip 中间件 · CORS · 页面预压缩缓存     │
└───────┬──────────────┬──────────────────┘
        │ enqueue      │ ack / reclaim
        ▼              ▼
┌──────────────┐   ┌──────────────────────┐
│  任务队列      │◄──│  Worker 消费循环       │
│ memory/Redis │   │  Redis 锁 + 幂等兜底    │
│ Streams      │   │  WORKER_COUNT 多线程    │
└──────────────┘   └──────────┬───────────┘
                              ▼
┌──────────────────────────────────────────┐
│           PlanProcessor 双管线             │
│  toC: Intake→…→Debate‖Mood→Reporter       │
│  toB: Intake→…→Consultant‖Compliance→... │
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
<h3 id="23">2.3 技术栈</h3>
<table>
<thead>
<tr>
<th>层</th>
<th>技术</th>
<th>版本/说明</th>
</tr>
</thead>
<tbody>
<tr>
<td>语言</td>
<td>Python</td>
<td>3.12（Docker 基础镜像 python:3.12-slim）</td>
</tr>
<tr>
<td>Web 框架</td>
<td>FastAPI</td>
<td>0.112.2</td>
</tr>
<tr>
<td>ASGI 服务器</td>
<td>Uvicorn</td>
<td>0.30.6（standard）</td>
</tr>
<tr>
<td>数据校验</td>
<td>Pydantic</td>
<td>2.8.2 + pydantic-settings</td>
</tr>
<tr>
<td>队列</td>
<td>Redis Streams / 内存</td>
<td>redis-py 5.0.8，双实现一键切换</td>
</tr>
<tr>
<td>HTTP 客户端</td>
<td>httpx</td>
<td>LLM 调用 + 外部 API</td>
</tr>
<tr>
<td>数据库</td>
<td>PostgreSQL（可选）</td>
<td>SQLAlchemy 2.0 + Alembic + psycopg 3，未配置时 no-op</td>
</tr>
<tr>
<td>向量检索</td>
<td>pgvector（可选）</td>
<td>语义检索演进，未配置时内存兜底</td>
</tr>
<tr>
<td>可观测</td>
<td>Prometheus</td>
<td>prometheus-client，<code>/metrics</code> 端点</td>
</tr>
<tr>
<td>安全</td>
<td>cryptography</td>
<td>HMAC token 签名</td>
</tr>
<tr>
<td>前端</td>
<td>原生 HTML/CSS/JS</td>
<td>单文件，水墨风设计令牌，ECharts（toB 图表）</td>
</tr>
<tr>
<td>部署</td>
<td>Docker</td>
<td><code>backend/Dockerfile</code>，EXPOSE 8000</td>
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
RUNNING → COMPLETED | FAILED | REPLAN_REQUIRED | CORRUPTED
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
<h3 id="41-toc-7">4.1 toC 游客端（7 页签行程书 + 服务大厅）</h3>
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
<td>行程书 7 页签</td>
<td>①总览 ②逐日 ③账本 ④辩论实录 ⑤心情剧本 ⑥B计划 ⑦清单</td>
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
<tr>
<td>挂起审批弹窗</td>
<td>超预算/安全任务在 toC 端也可直接批准/驳回</td>
</tr>
</tbody>
</table>
<h3 id="42-tob-9">4.2 toB 企业端（9 页签工作台）</h3>
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
<td>任务索引（状态/客户/租户筛选，按更新时间倒序），点行打开详情抽屉</td>
</tr>
<tr>
<td>审核流程状态图</td>
<td>11 态状态机可视化，点击节点下钻筛选</td>
</tr>
<tr>
<td>HITL 审核台</td>
<td>聚合待审批队列（预算/安全），一键批准/驳回，版本冲突 409</td>
</tr>
<tr>
<td>安全看板</td>
<td>拦截率、攻击分布 top6、14 天趋势曲线</td>
</tr>
<tr>
<td>合规审计</td>
<td>单任务审计事件流 + 全量 CSV 导出（UTF-8 BOM）</td>
</tr>
<tr>
<td>客户之声</td>
<td>好评/投诉聚合（praise/complaint 计数），代客记录反馈</td>
</tr>
<tr>
<td>白标交付</td>
<td>企业品牌 + 顾问署名 + 中立声明注入，sha256 校验行留痕</td>
</tr>
<tr>
<td>经营看板</td>
<td>完成率、每日创建、状态分布、客户分布 top8</td>
</tr>
<tr>
<td>客户管理</td>
<td>客户维度任务视图</td>
</tr>
</tbody>
</table>
<hr />
<h2 id="5-api">5. 数据结构与 API</h2>
<h3 id="51-modelsschemaspy">5.1 核心数据模型（<code>models/schemas.py</code>）</h3>
<p><strong>PlanRequest（创建任务入参）</strong>：</p>
<table>
<thead>
<tr>
<th>字段</th>
<th>类型</th>
<th>约束</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td>destination</td>
<td>str</td>
<td>min_length=1</td>
<td>目的地</td>
</tr>
<tr>
<td>days</td>
<td>int</td>
<td>1–14，默认 3</td>
<td>天数</td>
</tr>
<tr>
<td>budget</td>
<td>int</td>
<td>≥0</td>
<td>预算金额（元）</td>
</tr>
<tr>
<td>travelers</td>
<td>int</td>
<td>1–20，默认 2</td>
<td>出行人数（住宿每 2 人一间、打车每 3 人一车）</td>
</tr>
<tr>
<td>origin</td>
<td>str | None</td>
<td>—</td>
<td>出发地（用于大交通建议与分项预算）</td>
</tr>
<tr>
<td>departure_date / return_date</td>
<td>str | None</td>
<td>—</td>
<td>出发/返回日期（前端联动传入）</td>
</tr>
<tr>
<td>customer / tenant</td>
<td>str | None</td>
<td>—</td>
<td>客户归属/租户标识（toB 用）</td>
</tr>
<tr>
<td>mood</td>
<td>str | None</td>
<td>—</td>
<td>心情词（填了才生成情绪弧线章节）</td>
</tr>
<tr>
<td>preferences</td>
<td>list[str]</td>
<td>—</td>
<td>偏好标签</td>
</tr>
<tr>
<td>constraints</td>
<td>list[str]</td>
<td>—</td>
<td>约束条件</td>
</tr>
</tbody>
</table>
<p><strong>PlanStatusResponse（任务状态）</strong>：job_id / status / current_agent / progress / resume_from / version / error / parent_job_id / completed_nodes / created_at / updated_at。</p>
<p><strong>PlanResultResponse（行程书结果）</strong>：job_id / version / travel_plan_md / sha256 / itinerary（结构化逐日行程）/ hotels（实时酒店列表）/ economy_tips（经济实惠建议）/ user_input（原始入参）。</p>
<p><strong>ApprovalRequest（审批入参）</strong>：decision（approve/reject）/ operator / reason / base_version（冲突检测）。</p>
<p><strong>ReplanRequest（重规划入参）</strong>：change_request（追加为新约束）/ base_version。</p>
<h3 id="52-datajobsjob_id">5.2 任务目录结构（<code>data/jobs/{job_id}/</code>）</h3>
<pre><code>data/jobs/plan_{hash12}/
├── state.json              # 任务状态（11 态 + checkpoint + 版本）
├── state.json.sha256       # 状态文件校验旁车
├── agent_outputs/          # 各节点结构化产出
│   ├── Intake.json
│   ├── Researcher.json
│   ├── Planner.json
│   ├── Itinerary.json
│   ├── Budget.json
│   ├── Validator.json
│   ├── Sentiment.json
│   ├── Debate.json         # toC
│   ├── Mood.json           # toC（可选）
│   ├── Consultant.json     # toB
│   └── Compliance.json     # toB
├── travel_plan.md          # 最终行程书（Reporter 单点原子写）
├── travel_plan.md.sha256   # 行程书校验旁车
├── travel_plan_branded.md  # 白标导出版（可选）
└── audit.log               # 全量审计流水（追加式 JSONL）
</code></pre>
<h3 id="53-statejson">5.3 state.json 关键字段</h3>
<table>
<thead>
<tr>
<th>字段</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td>job_id</td>
<td><code>plan_{sha256(prefix12)}</code></td>
</tr>
<tr>
<td>status</td>
<td>11 态之一</td>
</tr>
<tr>
<td>current_node / resume_from</td>
<td>当前节点 / 断点续跑起点</td>
</tr>
<tr>
<td>progress</td>
<td>0–100 进度百分比</td>
</tr>
<tr>
<td>version</td>
<td>版本号（审批/改单自增，冲突检测用）</td>
</tr>
<tr>
<td>completed_nodes</td>
<td>已完成节点列表</td>
</tr>
<tr>
<td>agent_outputs</td>
<td>节点产出文件路径映射 <code>{agent: "agent_outputs/X.json"}</code></td>
</tr>
<tr>
<td>user_input</td>
<td>原始 PlanRequest</td>
</tr>
<tr>
<td>request_hash</td>
<td>幂等哈希（含 <code>_generation_version</code>）</td>
</tr>
<tr>
<td>parent_job_id</td>
<td>重规划子任务的父任务 ID</td>
</tr>
<tr>
<td>customer / tenant</td>
<td>toB 归属</td>
</tr>
<tr>
<td>error</td>
<td>错误信息（FAILED 时）</td>
</tr>
<tr>
<td>created_at / updated_at</td>
<td>时间戳</td>
</tr>
</tbody>
</table>
<h3 id="54-rest-api-35-1-sse">5.4 REST API 清单（约 35 个端点 + 1 个 SSE）</h3>
<p><strong>行程规划（<code>/api/plans</code>）</strong>：</p>
<table>
<thead>
<tr>
<th>方法</th>
<th>路径</th>
<th>用途</th>
<th>鉴权</th>
</tr>
</thead>
<tbody>
<tr>
<td>POST</td>
<td><code>/api/plans</code></td>
<td>创建任务（幂等）</td>
<td>无</td>
</tr>
<tr>
<td>GET</td>
<td><code>/api/plans</code></td>
<td>任务列表（筛选）</td>
<td>无</td>
</tr>
<tr>
<td>GET</td>
<td><code>/api/plans/{job_id}</code></td>
<td>任务状态</td>
<td>无</td>
</tr>
<tr>
<td>GET</td>
<td><code>/api/plans/{job_id}/result</code></td>
<td>行程书结果</td>
<td>无</td>
</tr>
<tr>
<td>GET</td>
<td><code>/api/plans/{job_id}/audit</code></td>
<td>审计日志</td>
<td>无</td>
</tr>
<tr>
<td>POST</td>
<td><code>/api/plans/{job_id}/feedback</code></td>
<td>反馈</td>
<td>consultant+</td>
</tr>
<tr>
<td>POST</td>
<td><code>/api/plans/{job_id}/export</code></td>
<td>白标导出</td>
<td>无</td>
</tr>
<tr>
<td>GET</td>
<td><code>/api/plans/{job_id}/diff</code></td>
<td>版本 diff</td>
<td>无</td>
</tr>
<tr>
<td>POST</td>
<td><code>/api/plans/{job_id}/approval</code></td>
<td>审批</td>
<td>supervisor/admin</td>
</tr>
<tr>
<td>POST</td>
<td><code>/api/plans/{job_id}/replan</code></td>
<td>增量重规划</td>
<td>consultant+</td>
</tr>
</tbody>
</table>
<p><strong>体验区（<code>/api/plans</code>）</strong>：map / nearby / debates / counterfactual / swarm / guides / dialogue / debate/vote / debate/live(SSE)。</p>
<p><strong>认证（<code>/api/auth</code>）</strong>：login / register / me。</p>
<p><strong>企业管理（<code>/api</code>，AUTH_ENABLED 时强制 admin）</strong>：approvals/pending / audit/export.csv / feedbacks / stats/overview。</p>
<p><strong>安全与服务</strong>：<code>/api/safety/summary</code>、<code>/api/services/travel</code>、<code>/api/services/{kind}</code>（五窗口）、<code>/api/services/city/photo</code>。</p>
<p><strong>集成与语义</strong>：<code>/api/integrations/status</code>、<code>/api/semantic/search</code>、<code>/api/semantic/add</code>。</p>
<p><strong>系统</strong>：<code>GET /</code>（toC 首页）、<code>GET /b</code>（toB 工作台）、<code>GET /health</code>、<code>GET /metrics</code>。</p>
<hr />
<h2 id="6">6. 部署架构与工程质量</h2>
<h3 id="61-docker-backenddockerfile">6.1 Docker 部署（<code>backend/Dockerfile</code>）</h3>
<pre><code class="language-dockerfile">FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app ./app
COPY frontend ./frontend
EXPOSE 8000
CMD [&quot;uvicorn&quot;, &quot;app.main:app&quot;, &quot;--host&quot;, &quot;0.0.0.0&quot;, &quot;--port&quot;, &quot;8000&quot;]
</code></pre>
<p><strong>部署命令</strong>：</p>
<pre><code class="language-bash">docker build -f backend/Dockerfile -t wl-travel .
docker run -p 8000:8000 wl-travel
# 多副本扩容（消费者名已按主机+进程自动唯一，分布式锁已内置）
docker compose up --scale backend=N
</code></pre>
<h3 id="62">6.2 项目目录结构</h3>
<pre><code>WL项目/
├── backend/
│   ├── app/
│   │   ├── agents/          # 12 个 Agent 实现（base + 11 节点）
│   │   ├── api/             # 7 个路由模块（plans/auth/admin/experience/safety/services/integrations）
│   │   ├── data/            # 静态数据（景点库 scenic_spots_beijing.json、舆情库 sentiment_reviews.json）
│   │   ├── models/          # states.py（11 态）、schemas.py（Pydantic 模型）
│   │   ├── services/        # 28 个服务模块（管线/队列/LLM/安全/审计/计算/可观测…）
│   │   └── workers/         # plan_worker.py（多线程消费循环）
│   ├── scripts/             # smoke_test / load_test / bench_replan / llm_offline_test
│   ├── tests/               # 20 个 pytest 测试文件
│   ├── alembic/             # 数据库迁移（PostgreSQL 演进）
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html           # toC 游客端（水墨风，单文件）
│   ├── admin.html           # toB 企业端（9 页签工作台，ECharts）
│   ├── vendor/              # echarts.min.js
│   └── media/               # 静态素材
├── data/jobs/               # 运行时任务数据（456+ 份已生成行程书）
├── docs/                    # 项目文档（toB 工作台功能清单等）
├── observability/           # 监控配置
├── design_v2/               # 设计稿
└── .github/                 # CI 工作流
</code></pre>
<h3 id="63-appconfigpypydantic-settings">6.3 配置（<code>app/config.py</code>，pydantic-settings）</h3>
<p>全部环境变量一个入口，与 <code>.env.example</code> 一一对应，本地开发零配置即可运行：</p>
<table>
<thead>
<tr>
<th>配置项</th>
<th>默认值</th>
<th>说明</th>
</tr>
</thead>
<tbody>
<tr>
<td>QUEUE_BACKEND</td>
<td>memory</td>
<td>memory | redis</td>
</tr>
<tr>
<td>REDIS_URL</td>
<td>redis://localhost:6379/0</td>
<td>Redis 连接</td>
</tr>
<tr>
<td>WORKER_COUNT</td>
<td>1</td>
<td>Worker 线程数</td>
</tr>
<tr>
<td>LLM_MODE</td>
<td>mock</td>
<td>mock | real</td>
</tr>
<tr>
<td>LLM_BASE_URL / API_KEY / MODEL</td>
<td>—</td>
<td>real 模式配置</td>
</tr>
<tr>
<td>DATABASE_URL</td>
<td>None</td>
<td>PostgreSQL 连接（未配则 no-op）</td>
</tr>
<tr>
<td>METRICS_ENABLED</td>
<td>true</td>
<td>Prometheus 端点开关</td>
</tr>
<tr>
<td>AUTH_ENABLED</td>
<td>false</td>
<td>toB 管理 API 强制 Bearer 校验</td>
</tr>
<tr>
<td>EXTERNAL_MAP/SEARCH/OCR_PROVIDER</td>
<td>local</td>
<td>外部适配器扩展点</td>
</tr>
</tbody>
</table>
<h3 id="64">6.4 测试体系</h3>
<ul>
<li><strong>20 个 pytest 测试文件</strong>（<code>backend/tests/</code>），覆盖：Agent 单测（intake/budget/validator/sentiment/planner…）、管线契约（toC/toB 章节断言）、RBAC、安全过滤、服务真实调用、配置、外部客户端、幂等、断点恢复、内容溯源等；</li>
<li><strong>8 条 smoke 链路</strong>（<code>scripts/smoke_test.py</code>）：正常链路 / 注入挂起 / 安全放行 / 预算挂起与重复审批 409 / 增量重规划 diff / 断点恢复 / 心情剧本与投票 / toB 管线；</li>
<li>CI 工作流自动执行编译自检 + 测试 + smoke。</li>
</ul>
<h3 id="65">6.5 可观测性</h3>
<ul>
<li>Prometheus <code>/metrics</code>（METRICS_ENABLED 开关）：提交数、审批数、完成/失败计数、节点耗时直方图；</li>
<li>JSON 结构化日志（<code>services/jsonlog.py</code>）全链路事件（创建/挂起/审批/恢复/认领/ack…）。</li>
</ul>
<hr />
<h2 id="7">7. 性能与可靠性</h2>
<h3 id="71">7.1 压测方法</h3>
<p><strong>测试环境</strong>：Docker 部署，FastAPI + Redis Streams + 1 Worker + 通义 LLM real 模式；压测源与被测同机（本机回环，绝对值偏保守）。</p>
<p><strong>测试工具</strong>：Python httpx 异步压测脚本，原始数据见 <code>压测结果.json</code>。</p>
<p><strong>测试场景</strong>：</p>
<table>
<thead>
<tr>
<th>场景</th>
<th>链路</th>
<th>并发</th>
<th>持续/数量</th>
</tr>
</thead>
<tbody>
<tr>
<td>S1-a</td>
<td><code>GET /health</code> 读基准</td>
<td>50</td>
<td>15 秒</td>
</tr>
<tr>
<td>S1-b</td>
<td><code>GET /</code>（首页 HTML，约 127KB）</td>
<td>50</td>
<td>15 秒</td>
</tr>
<tr>
<td>S2</td>
<td><code>GET /api/services/attraction</code>（高德 POI 实时链路）</td>
<td>10</td>
<td>30 秒</td>
</tr>
<tr>
<td>S3</td>
<td><code>POST /api/plans</code> 完整生成链路</td>
<td>8</td>
<td>8 个任务跑至终态</td>
</tr>
</tbody>
</table>
<h3 id="72">7.2 第一轮结果（优化前基线）</h3>
<table>
<thead>
<tr>
<th>指标</th>
<th>S1 读基准</th>
<th>S1 首页</th>
<th>S2 POI 实时</th>
<th>S3 生成提交</th>
</tr>
</thead>
<tbody>
<tr>
<td>请求数</td>
<td>4,447</td>
<td>2,118</td>
<td>5,925</td>
<td>8</td>
</tr>
<tr>
<td>吞吐 RPS</td>
<td>295.5</td>
<td>138.2</td>
<td>197.2</td>
<td>—（串行队列）</td>
</tr>
<tr>
<td>错误率</td>
<td>0%</td>
<td>0%</td>
<td>0.02%</td>
<td>0%</td>
</tr>
<tr>
<td>P50</td>
<td>175ms</td>
<td>343ms</td>
<td>42ms</td>
<td>275ms</td>
</tr>
<tr>
<td>P95</td>
<td>264ms</td>
<td>572ms</td>
<td>92ms</td>
<td>282ms</td>
</tr>
<tr>
<td>P99</td>
<td>321ms</td>
<td>684ms</td>
<td>141ms</td>
<td>282ms</td>
</tr>
</tbody>
</table>
<p>S3 生成链路：8 并发任务 100% 成功，端到端单稿 54.8 秒（无排队），2/8 触发预算审批挂起（审批后续跑完成）。</p>
<h3 id="73">7.3 第二轮优化与达标结果</h3>
<p><strong>实施的三项优化</strong>：</p>
<ol>
<li><strong>首页预压缩缓存</strong>（<code>main.py</code>）：页面按 mtime 缓存进内存 + GZip 字节预生成（compresslevel=6，127KB→36KB），按 <code>Accept-Encoding</code> 返回双版本；</li>
<li><strong>服务窗口 60s 结果缓存</strong>（<code>api/services.py</code>）：五窗口按 <code>kind|destination|origin</code> 缓存 60 秒；</li>
<li><strong>全局 GZip 中间件</strong>（<code>minimum_size=1024</code>）：其余 JSON 接口统一压缩。</li>
</ol>
<p><strong>达标结果</strong>：</p>
<table>
<thead>
<tr>
<th>端点</th>
<th>QPS</th>
<th>P50</th>
<th>P95</th>
<th>达标（&gt;300 / &lt;100ms）</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>GET /health</code></td>
<td><strong>572.5</strong></td>
<td>33ms</td>
<td><strong>94ms</strong></td>
<td>✅</td>
</tr>
<tr>
<td><code>GET /</code>（首页）</td>
<td><strong>350.2</strong></td>
<td>64ms</td>
<td><strong>98ms</strong></td>
<td>✅</td>
</tr>
<tr>
<td><code>GET /api/services/attraction</code></td>
<td><strong>547.7</strong></td>
<td>37ms</td>
<td><strong>67ms</strong></td>
<td>✅</td>
</tr>
</tbody>
</table>
<p>压测形态：单客户端进程，8 条预热长连接 × 32 在途请求（分批 gather）。</p>
<h3 id="74">7.4 过程中发现的环境事实（影响压测口径）</h3>
<ul>
<li><strong>WSL2 并行建连串行化</strong>：8 个并行握手排队约 2.1s/个（localhost/127.0.0.1/[::1] 行为一致，与后端无关）；顺序建连仅 10ms/个。压测必须先顺序预热连接再并发；</li>
<li><strong>单客户端吞吐上限</strong>：单个 Python httpx 客户端进程吞吐上限约 280–350 RPS（客户端 CPU 所致），突破方式是多进程分片压测；</li>
<li><strong>S2 冷启动尖峰</strong>：1 次 3.4s 首建连异常（错误率 0.02%），此后 5,924 次全部 200。</li>
</ul>
<h3 id="75">7.5 容量短板与扩容建议</h3>
<ol>
<li><strong>生成吞吐受限于单 Worker</strong>：<code>WORKER_COUNT=1</code> 时任务逐个串行，8 并发提交时 1 个运行其余排队。扩容路径已具备：调大 <code>WORKER_COUNT</code> + <code>docker compose up --scale backend=N</code>（消费者名已按主机+进程自动唯一，分布式锁已内置）；</li>
<li><strong>LLM 是生成耗时主导项</strong>（单稿 ~55s 中 LLM 占大头）：可换更快模型档位（如 qwen-flash）或降低 <code>LLM_MAX_OUTPUT</code>；</li>
<li><strong>高德 0.4s 全局限速器</strong>是刻意的 QPS 保护：单机够用；多实例部署需改为 Redis 分布式限速，否则每实例各 0.4s 会放大总 QPS 触发上游限流。</li>
</ol>
<h3 id="76">7.6 可靠性指标</h3>
<table>
<thead>
<tr>
<th>指标</th>
<th>数值</th>
</tr>
</thead>
<tbody>
<tr>
<td>断点恢复调度时间</td>
<td><strong>5 秒内</strong></td>
</tr>
<tr>
<td>增量重规划耗时降低（mock 口径）</td>
<td><strong>约 23%</strong></td>
</tr>
<tr>
<td>生成链路成功率（8 并发）</td>
<td><strong>100%（8/8）</strong></td>
</tr>
<tr>
<td>预算挂起触发率（压测样本）</td>
<td>2/8（工作流保护正常）</td>
</tr>
<tr>
<td>已生成真实行程书</td>
<td><strong>456+ 份</strong></td>
</tr>
<tr>
<td>测试覆盖</td>
<td>20 pytest 文件 + 8 smoke 链路</td>
</tr>
</tbody>
</table>
<hr />
<h2 id="8">8. 安全与合规</h2>
<ul>
<li><strong>输入分级过滤</strong>：高危 block / 中危 sanitize / 低危 allow，8+4 条模式规则；</li>
<li><strong>输出递归清洗</strong>：<code>scan_payload</code> 遍历每个 Agent 输出，防"输出即注入"；</li>
<li><strong>CORS 显式关闭凭据</strong>：通配源 + allow_credentials=False（防跨域带 Cookie 组合绕过）；</li>
<li><strong>演示级认证</strong>：Bearer Token + HMAC 一致比较（<code>hmac.compare_digest</code>），7 天过期，RBAC 四级角色校验；</li>
<li><strong>白标导出</strong>：含中立声明与 sha256 校验行，交付留痕写入审计；</li>
<li><strong>全量审计</strong>：<code>audit.log</code> 追加式，CSV 导出 UTF-8 BOM 兼容 Excel。</li>
</ul>
<hr />
<h2 id="9">9. 诚实边界与免责</h2>
<ul>
<li><strong>QPS 指标仅覆盖读接口与提交接口，不覆盖生成吞吐</strong>（生成耗时由大模型延迟决定）；</li>
<li><strong>通勤时间、票价、天气为本地静态估算口径</strong>，非实时 API 数据；</li>
<li><strong>LLM 默认 mock 模式</strong>，配置 key 即切换真实模型；</li>
<li><strong>服务大厅五窗口为演示口径</strong>，真实票务/酒店 API 未接入，字段留空；</li>
<li><strong>网页调研默认关闭</strong>，白名单仅故宫/八达岭两官网；</li>
<li><strong>压测源与被测同机</strong>（本机 Docker 回环），延迟含本机回环开销，绝对值偏保守。</li>
</ul>
<hr />
<h2 id="10">10. 演进路线</h2>
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
<td><code>database_url</code> + 镜像层 + <code>/api/semantic/search</code></td>
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
python -m uvicorn app.main:app --port 8000
# 零配置即可运行（memory 队列 + mock LLM）
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
<td>数据模型</td>
<td><code>models/schemas.py</code></td>
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
<td>行程书渲染</td>
<td><code>services/markdown_reporter.py</code></td>
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
<tr>
<td>配置</td>
<td><code>config.py</code></td>
</tr>
<tr>
<td>应用入口</td>
<td><code>main.py</code></td>
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