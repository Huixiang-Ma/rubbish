# -*- coding: utf-8 -*-
"""一次性前端改造脚本：toC 文旅主题 + 移除 toB 元素 + toB 布局优化。执行后可删除。"""
from pathlib import Path
import re

# ---------- toC: index.html ----------
path = Path("frontend/index.html")
text = path.read_text(encoding="utf-8")

new_css = """    <style>
      :root {
        --paper: #f6f1e7;
        --ink: #2c2a26;
        --muted: #7a746a;
        --cinnabar: #b03a2e;
        --cinnabar-dark: #8f2d23;
        --gold: #c9a227;
        --teal: #2f6f6a;
        --card: #fffdf7;
        --border: #e5dcc8;
      }
      body {
        margin: 0;
        font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
        background: var(--paper);
        color: var(--ink);
      }
      .hero {
        background:
          radial-gradient(circle at 85% 20%, rgba(201, 162, 39, 0.2), transparent 42%),
          linear-gradient(135deg, #2f6f6a 0%, #24504b 60%, #1e423e 100%);
        color: #f8f4ea;
        padding: 26px 24px 22px;
        display: flex;
        align-items: center;
        gap: 18px;
        border-bottom: 3px solid var(--gold);
      }
      .seal {
        min-width: 58px;
        height: 58px;
        background: linear-gradient(160deg, #c74a3d, var(--cinnabar-dark));
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: "Songti SC", "SimSun", serif;
        font-weight: 700;
        font-size: 19px;
        letter-spacing: 2px;
        border-radius: 10px;
        transform: rotate(-5deg);
        box-shadow: 0 4px 14px rgba(176, 58, 46, 0.45);
        text-align: center;
        line-height: 1.15;
      }
      .hero h1 {
        margin: 0 0 6px;
        font-family: "Songti SC", "SimSun", "STSong", serif;
        font-size: 26px;
        letter-spacing: 2px;
      }
      .hero p {
        margin: 0;
        opacity: 0.88;
        font-size: 14px;
        letter-spacing: 1px;
      }
      main {
        max-width: 1080px;
        margin: 0 auto;
        padding: 26px 20px 60px;
      }
      .panel {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 14px;
        box-shadow: 0 6px 24px rgba(44, 42, 38, 0.07);
        padding: 22px;
        margin-bottom: 20px;
      }
      h1, h2 {
        font-family: "Songti SC", "SimSun", "STSong", serif;
      }
      h2 {
        margin-top: 0;
        font-size: 18px;
        color: var(--teal);
        padding-left: 10px;
        border-left: 4px solid var(--gold);
      }
      h3 {
        margin: 18px 0 6px;
        font-size: 15px;
        color: var(--cinnabar-dark);
      }
      label {
        display: block;
        margin: 12px 0 6px;
        font-weight: 600;
        font-size: 14px;
      }
      input, textarea, select {
        width: 100%;
        box-sizing: border-box;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px 12px;
        font-size: 15px;
        background: #fff;
      }
      textarea {
        min-height: 72px;
      }
      button {
        margin-top: 16px;
        border: 0;
        border-radius: 10px;
        background: linear-gradient(135deg, var(--cinnabar), var(--cinnabar-dark));
        color: #fff;
        padding: 11px 20px;
        font-size: 15px;
        cursor: pointer;
      }
      button:disabled {
        background: #b9b2a4;
        cursor: not-allowed;
      }
      button.secondary {
        background: var(--teal);
      }
      button.danger {
        background: #a33327;
      }
      button + button {
        margin-left: 10px;
      }
      button.mini {
        margin: 0;
        padding: 4px 10px;
        font-size: 13px;
        background: var(--teal);
      }
      button.mini.star {
        background: var(--gold);
        color: #3a2f00;
      }
      pre {
        white-space: pre-wrap;
        background: #2c2a26;
        color: #f0ead9;
        border-radius: 12px;
        padding: 16px;
        overflow: auto;
        font-size: 13px;
      }
      .status {
        display: inline-block;
        border-radius: 999px;
        padding: 4px 12px;
        background: #eaf3ef;
        color: var(--teal);
        font-weight: 700;
        font-size: 13px;
      }
      .hint {
        color: var(--muted);
        font-size: 13px;
      }
      .hidden {
        display: none;
      }
      .ornament {
        text-align: center;
        color: var(--gold);
        margin: 0 0 8px;
        letter-spacing: 10px;
        font-size: 12px;
      }
      .two-col {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }
      .bubble {
        padding: 8px 12px;
        border-radius: 10px;
        margin: 4px 0;
        font-size: 14px;
      }
      .side-plan {
        background: #eaf3ef;
        border-left: 3px solid var(--teal);
      }
      .side-traveler {
        background: #fbf3dd;
        border-left: 3px solid var(--gold);
      }
      .exp-card {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 10px 12px;
        margin: 6px 0;
        font-size: 14px;
        background: #fff;
      }
      .live-box {
        max-height: 260px;
        overflow: auto;
        background: #2c2a26;
        border-radius: 10px;
        padding: 10px;
      }
      .live-box .side-plan {
        color: #9adbd4;
        background: transparent;
        border-left-color: var(--teal);
      }
      .live-box .side-traveler {
        color: #ecd9a0;
        background: transparent;
        border-left-color: var(--gold);
      }
      .legend {
        font-size: 13px;
        margin: 6px 0;
      }
      .comfort-舒适 { color: #2e7d32; font-weight: 700; }
      .comfort-一般 { color: #b45309; font-weight: 700; }
      .comfort-拥挤 { color: var(--cinnabar); font-weight: 700; }
      .hist-item {
        display: flex;
        gap: 8px;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px dashed var(--border);
        font-size: 14px;
      }
      #map {
        height: 320px;
        border-radius: 10px;
        border: 1px solid var(--border);
      }
      @media (max-width: 760px) {
        .two-col { grid-template-columns: 1fr; }
        .hero { padding: 18px 16px; gap: 12px; }
        .hero h1 { font-size: 20px; }
        main { padding: 18px 12px 40px; }
        .panel { padding: 16px; }
        button + button { margin-left: 6px; }
      }
    </style>"""

text = re.sub(r"    <style>.*?</style>", lambda m: new_css, text, count=1, flags=re.DOTALL)

old_head = """    <main>
      <div class="panel">
        <h1>多 Agent 文旅规划 MVP</h1>
        <p>先用 4 个核心 Agent 跑通异步可恢复闭环：Researcher、Planner、Itinerary、Validator。</p>
        <p><a href="/b">企业端工作台 →</a></p>
        <label>目的地</label>"""
new_head = """    <header class="hero">
      <div class="seal">文旅</div>
      <div>
        <h1>山水有约 · 智游行程规划</h1>
        <p>五 Agent 协同定制：算得准 · 说得清 · 可验证 —— 给你一份走得通的旅程</p>
      </div>
    </header>
    <main>
      <div class="panel">
        <h2>规划我的旅程</h2>
        <p class="ornament">❖ ❖ ❖</p>
        <label>目的地</label>"""
assert old_head in text, "head block not found"
text = text.replace(old_head, new_head)

text = text.replace(
    """        <label>客户（可选，toB 归属）</label>
        <input id="customer" placeholder="留空则不归属客户" />
""",
    "",
)
text = text.replace(
    """          customer: document.querySelector("#customer").value.trim() || null,
""",
    "",
)
text = text.replace(
    '<p class="hint">后端直接托管本页：游客端 `/`，企业端 `/b`。如用 file:// 打开，可在控制台执行 localStorage.setItem("apiBase", "http://...") 后刷新。</p>',
    '<p class="hint">如用 file:// 方式打开本页，可在控制台执行 localStorage.setItem("apiBase", "http://...") 后刷新。</p>',
)

old_safety_panel = """
      <div class="panel">
        <h2>安全看板</h2>
        <p id="safetySummary">加载中...</p>
        <p class="hint">数据来自本地任务审计日志（audit.log）聚合。</p>
      </div>"""
assert old_safety_panel in text, "safety panel not found"
text = text.replace(old_safety_panel, "")

old_fn = """      async function loadSafetySummary() {
        try {
          const data = await (await fetch(`${apiBase}/api/safety/summary`)).json();
          const c = data.counters;
          document.querySelector("#safetySummary").textContent =
            `高风险拦截 ${c.safety_block} 次 · 预算挂起 ${c.budget_approval_required} 次 · 人工审批 ${c.approval} 次（已扫描 ${data.jobs_scanned} 个任务）`;
        } catch (err) {
          document.querySelector("#safetySummary").textContent = "安全看板加载失败（后端未启动？）";
        }
      }

"""
assert old_fn in text, "loadSafetySummary fn not found"
text = text.replace(old_fn, "")
text = text.replace(
    "        pollStatus(currentJobId);\n        loadSafetySummary();\n",
    "        pollStatus(currentJobId);\n",
)
text = text.replace(
    "        pollStatus(data.job_id);\n        loadSafetySummary();\n",
    "        pollStatus(data.job_id);\n",
)
text = text.replace(
    "      renderHistory();\n      loadSafetySummary();\n    </script>",
    "      renderHistory();\n    </script>",
)

text = text.replace('<button id="submit">创建异步规划任务</button>', '<button id="submit">开始规划旅程</button>')
text = text.replace("<title>多 Agent 文旅规划 MVP</title>", "<title>山水有约 · 智游行程规划</title>")
path.write_text(text, encoding="utf-8")
print("toC themed OK")

# ---------- toB: admin.html 布局优化 ----------
apath = Path("frontend/admin.html")
atext = apath.read_text(encoding="utf-8")

# KPI 行 + 表格横向滚动容器
atext = atext.replace(
    "<h2>方案列表（B1 顾问工作台）</h2>",
    "<h2>方案列表（B1 顾问工作台）</h2>\n          <div class=\"kpi-row\" id=\"planKpis\"><span class=\"kpi\">加载中...</span></div>",
)
atext = atext.replace(
    '<table id="plansTable" style="margin-top: 14px">',
    '<div class="table-wrap"><table id="plansTable" style="margin-top: 14px">',
)
atext = atext.replace(
    "</table>\n          <p class=\"muted\" id=\"plansMeta\"></p>",
    "</table></div>\n          <p class=\"muted\" id=\"plansMeta\"></p>",
)

# 图表标签优化：攻击分布与状态分布加右侧图例，避免长标签遮挡
atext = atext.replace(
    """        echarts.init($("#chartAttack")).setOption({
          title: { text: "攻击模式分布（高危规则命中）", left: "center", textStyle: { fontSize: 14 } },
          tooltip: {},
          series: [
            {
              type: "pie",
              radius: "62%",
              data: data.attack_distribution.map(([name, value]) => ({ name, value })),
            },
          ],
        });""",
    """        echarts.init($("#chartAttack")).setOption({
          title: { text: "攻击模式分布（高危规则命中）", left: "center", textStyle: { fontSize: 14 } },
          tooltip: {},
          legend: { orient: "vertical", right: 10, top: "middle" },
          series: [
            {
              type: "pie",
              radius: "55%",
              center: ["38%", "54%"],
              label: { formatter: "{c} 次" },
              data: data.attack_distribution.map(([name, value]) => ({ name, value })),
            },
          ],
        });""",
)
atext = atext.replace(
    """          series: [
            {
              type: "pie",
              radius: "62%",
              data: data.status_distribution.map(([name, value]) => ({ name, value })),
            },
          ],""",
    """          legend: { orient: "vertical", right: 10, top: "middle" },
          series: [
            {
              type: "pie",
              radius: "55%",
              center: ["38%", "54%"],
              data: data.status_distribution.map(([name, value]) => ({ name, value })),
            },
          ],""",
)

# loadPlans 追加 KPI 渲染
atext = atext.replace(
    '        $("#plansMeta").textContent = `共 ${data.total} 条方案`;',
    """        $("#plansMeta").textContent = `共 ${data.total} 条方案`;
        fetch(`${apiBase}/api/stats/overview`)
          .then((r) => r.json())
          .then((s) => {
            const pending = s.status_distribution.filter(([k]) => k.startsWith("WAITING")).reduce((a, [, v]) => a + v, 0);
            const running = (s.status_distribution.find(([k]) => k === "RUNNING") || [null, 0])[1];
            const rate = s.completed_rate === null ? "-" : (s.completed_rate * 100).toFixed(1) + "%";
            $("#planKpis").innerHTML = [
              ["任务总量", s.total],
              ["完成率", rate],
              ["挂起待审", pending],
              ["执行中", running],
            ]
              .map(([k, v]) => `<span class="kpi">${k}<strong>${v}</strong></span>`)
              .join("");
          });""",
)

# CSS 追加：KPI 卡、表格滚动、审核台双列
atext = atext.replace(
    "    </style>",
    """      .kpi-row {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin: 12px 0 4px;
      }
      .kpi {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 8px 16px;
        font-size: 13px;
        color: #475569;
      }
      .kpi strong {
        display: block;
        font-size: 19px;
        color: #0f172a;
        margin-top: 2px;
      }
      .table-wrap {
        overflow-x: auto;
      }
      #approvalList {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(430px, 1fr));
        gap: 12px;
      }
      @media (max-width: 980px) {
        #approvalList {
          grid-template-columns: 1fr;
        }
      }
    </style>""",
)
apath.write_text(atext, encoding="utf-8")
print("toB layout optimized OK")
