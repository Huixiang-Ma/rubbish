<template>
  <div class="rag-lab">
    <header class="rl-head">
      <div>
        <div class="rl-eyebrow">知识 · 实验台</div>
        <h1 class="rl-title">RAG 实验室</h1>
        <p class="rl-sub">
          调试检索质量 / 跑通拒答阈值 / 观察分块粒度。同一份知识库，对外服务于 toC AI 导游问答，对内为产品和运营提供"问答质检"工具。
        </p>
      </div>
      <div class="rl-head-actions">
        <button class="btn btn-ghost btn-sm" @click="exportHistory">⬇ 导出调用日志</button>
        <button class="btn btn-soft btn-sm" @click="history = []">清空历史</button>
      </div>
    </header>

    <!-- 指标卡 -->
    <section class="kpi-row">
      <div class="kpi card"><div class="kpi-label">累计提问</div><div class="kpi-num">{{ history.length }}</div></div>
      <div class="kpi card">
        <div class="kpi-label">命中率</div>
        <div class="kpi-num">{{ hitRateText }}<small> ({{ hitRate }}%)</small></div>
        <div class="kpi-foot">top-1 距离 ≤ 0.8</div>
      </div>
      <div class="kpi card">
        <div class="kpi-label">拒答率</div>
        <div class="kpi-num" :class="{ warn: refusalRate >= 30 }">{{ refusalRate }}%</div>
        <div class="kpi-foot">距离 > {{ threshold }} 时拒答</div>
      </div>
      <div class="kpi card">
        <div class="kpi-label">平均距离</div>
        <div class="kpi-num">{{ avgDistance }}</div>
        <div class="kpi-foot">越小越相关</div>
      </div>
    </section>

    <div class="rl-grid">
      <!-- 左：测试台 -->
      <section class="card rl-pane">
        <div class="pane-title">检索测试台</div>
        <div class="pane-controls">
          <label class="ctrl">
            <span>tenant_id</span>
            <input v-model="tenantId" placeholder="留空 = 公共知识库" />
          </label>
          <label class="ctrl">
            <span>top_k</span>
            <input type="number" v-model.number="topK" min="1" max="8" />
          </label>
          <label class="ctrl">
            <span>模式</span>
            <select v-model="mode">
              <option value="sync">同步 ask</option>
              <option value="stream">流式 chat (SSE)</option>
            </select>
          </label>
        </div>

        <RagPanel
          :show-mode="false"
          :show-top-k="false"
          :top-k="topK"
          :tenant="tenantId"
          :mode="mode"
          placeholder="例：北京故宫附近 500 米内有哪些酒店？拙政园雨天备选？"
          @answered="onAnswered"
          :reset-able="true"
        />

        <div class="rl-presets">
          <span>回归用例：</span>
          <button v-for="q in PRESETS" :key="q" type="button" class="chip chip-outline" @click="fillQuestion(q)">{{ q }}</button>
        </div>

        <div class="rl-legend">
          <strong>距离阈值色带</strong>
          <span class="leg"><i style="background:#10b981"></i>< 0.40 紧相关</span>
          <span class="leg"><i style="background:#38bdf8"></i>0.40-0.65 可参考</span>
          <span class="leg"><i style="background:#f59e0b"></i>0.65-0.80 边缘</span>
          <span class="leg"><i style="background:#ef4444"></i>≥ 0.80 拒答</span>
        </div>
      </section>

      <!-- 右：分块可视化 + 标品目录 + 历史 -->
      <section class="rl-side">
        <div class="card">
          <div class="pane-title">
            命中块可视化
            <span v-if="lastChunks.length" class="badge">{{ lastChunks.length }} 块</span>
          </div>
          <div v-if="!lastChunks.length" class="empty">
            <div class="icon">📭</div><p>提交问题后，此处展示命中的检索块（含距离、doc_id、租户隔离）</p>
          </div>
          <div v-else class="chunk-stack">
            <div v-for="(c, i) in lastChunks" :key="i" class="chunk card">
              <div class="chunk-head">
                <span class="c-no">#{{ i + 1 }}</span>
                <span class="c-doc">📄 {{ c.doc_id || '匿名分块' }}</span>
                <span v-if="c.tenant_id" class="c-tenant">🏷 {{ c.tenant_id }}</span>
                <span class="c-d" :style="{ color: distColor(c.distance) }">
                  d = {{ c.distance?.toFixed(3) }}
                </span>
              </div>
              <div class="chunk-body">
                <div class="c-text" :class="{ collapsed: !expanded[i] }">{{ c.content }}</div>
                <button v-if="c.content?.length > 220" class="link-btn" @click="expanded[i] = !expanded[i]">
                  {{ expanded[i] ? '收起' : '展开全文' }}
                </button>
              </div>
              <div class="chunk-bar"><i :style="{ width: distPct(c.distance) + '%', background: distColor(c.distance) }" /></div>
            </div>
          </div>
        </div>

        <!-- 标品目录（按分类聚合） -->
        <div class="card" style="margin-top:14px">
          <div class="pane-title">
            标品目录
            <small class="hint-text">按分类聚合的命中标品</small>
          </div>
          <div v-if="!lastGroups.length" class="empty">
            <div class="icon">📂</div><p>暂无命中标品（提交一次有效问题后自动归类）</p>
          </div>
          <div v-else class="prod-cat-stack">
            <div v-for="g in lastGroups" :key="g.key" class="prod-cat-block">
              <div class="prod-cat-head">
                <span class="prod-cat-icon">{{ g.icon }}</span>
                <span class="prod-cat-label">{{ g.label }}</span>
                <span class="prod-cat-count">{{ g.items.length }}</span>
              </div>
              <ul class="prod-cat-items">
                <li v-for="(p, i) in g.items" :key="i">
                  <span class="prod-name">{{ p.title }}</span>
                  <span v-if="p.fields.city" class="prod-city">{{ p.fields.city }}</span>
                  <span v-if="p.fields.open_time" class="prod-time">🕐</span>
                  <span class="prod-d" :style="{ color: distColor(p.distance) }">
                    d={{ p.distance?.toFixed(2) }}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- 入库指引 -->
        <div class="card" style="margin-top:14px">
          <div class="pane-title">
            标品入库指引
            <small class="hint-text">schema · 命令 · 模板</small>
          </div>
          <div class="ingest-tabs">
            <button v-for="t in INGEST_TABS" :key="t.key" type="button"
                    class="itab" :class="{ active: ingestTab === t.key }"
                    @click="ingestTab = t.key">{{ t.label }}</button>
          </div>
          <div class="ingest-body">
            <pre v-if="ingestTab === 'schema'" class="ingest-pre">{{ INGEST_SCHEMA }}</pre>
            <pre v-else-if="ingestTab === 'cmd'" class="ingest-pre">{{ INGEST_CMD }}</pre>
            <pre v-else class="ingest-pre">{{ INGEST_JSON }}</pre>
          </div>
          <p class="ingest-tip">
            💡 上游支持 CSV / JSON / URL / 高德 POI 四种源；name 必填，其他列缺失自动跳过。详见 <code>backend/scripts/sync_rag_corpus.py</code>。
          </p>
        </div>

        <div class="card" style="margin-top:14px">
          <div class="pane-title">调用历史</div>
          <div v-if="!history.length" class="empty"><div class="icon">🕓</div><p>暂无记录</p></div>
          <div v-else class="hist">
            <div v-for="(h, i) in history" :key="i" class="hist-row" @click="loadHistory(h)">
              <span class="hist-i">{{ history.length - i }}</span>
              <span class="hist-q" :title="h.question">{{ h.question }}</span>
              <span class="hist-mode"><StatusTag :status="h.mode" /></span>
              <span class="hist-meta">{{ h.sources_count }} 块 · {{ h.sub_questions_count }} 子问 · {{ h.latency_ms }}ms</span>
              <span class="hist-time">{{ h.at }}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ragApi } from '../../api'
import { toast } from '../../composables/toast'
import RagPanel from '../../components/RagPanel.vue'
import StatusTag from '../../components/StatusTag.vue'
import { parseAndGroup } from '../../lib/productParser'

const tenantId = ref('')
const topK = ref(3)
const mode = ref('sync')
const threshold = 0.8
const lastChunks = ref([])
const expanded = ref({})
const history = ref([])

const PRESETS = [
  '拙政园门票淡旺季分别是多少？',
  '苏州适合雨天的景点有哪些？',
  '北京故宫门票多少钱？',
  '北京 5A 景点推荐几个',
]

function fillQuestion(q) {
  const ta = document.querySelector('.rl-pane textarea')
  if (!ta) return
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set
  setter.call(ta, q)
  ta.dispatchEvent(new Event('input', { bubbles: true }))
  ta.focus()
}

function distColor(d) {
  if (typeof d !== 'number') return '#94a3b8'
  if (d < 0.4) return '#10b981'
  if (d < 0.65) return '#38bdf8'
  if (d < 0.8) return '#f59e0b'
  return '#ef4444'
}
function distPct(d) {
  if (typeof d !== 'number') return 0
  return Math.max(0, Math.min(100, (1 - d) * 100))
}

function onAnswered(result) {
  lastChunks.value = result.sources || []
  // 每一块默认折叠
  expanded.value = {}
  history.value.unshift({
    question: result.question || '(已提交)',
    mode: result.mode || 'unknown',
    sources_count: result.sources?.length || 0,
    sub_questions_count: result.sub_questions?.length || 0,
    latency_ms: result.latency_ms || 0,
    at: new Date().toLocaleTimeString(),
    answer: result.answer,
    sources: result.sources,
    sub_questions: result.sub_questions,
  })
  if (history.value.length > 30) history.value = history.value.slice(0, 30)
}

function loadHistory(h) {
  lastChunks.value = h.sources || []
  expanded.value = {}
  toast(`加载了历史结果`, 'ok')
}

function exportHistory() {
  const blob = new Blob([JSON.stringify(history.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `rag-lab-history-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// 指标
const hitRate = computed(() => {
  if (!history.value.length) return 0
  const hits = history.value.filter(h => ['llm', 'retrieval'].includes(h.mode)).length
  return Math.round((hits / history.value.length) * 100)
})
const hitRateText = computed(() => {
  if (!history.value.length) return '-'
  const hits = history.value.filter(h => ['llm', 'retrieval'].includes(h.mode)).length
  return `${hits}/${history.value.length}`
})
const refusalRate = computed(() => {
  if (!history.value.length) return 0
  const r = history.value.filter(h => h.mode === 'refusal' || h.mode === 'empty').length
  return Math.round((r / history.value.length) * 100)
})
const avgDistance = computed(() => {
  const all = history.value.flatMap(h => (h.sources || []).map(s => s.distance)).filter(d => typeof d === 'number')
  if (!all.length) return '-'
  return (all.reduce((a, b) => a + b, 0) / all.length).toFixed(3)
})

// 标品目录：把当前命中按分类聚合
const lastGroups = computed(() => parseAndGroup(lastChunks.value))

// 入库指引内容
const ingestTab = ref('schema')
const INGEST_TABS = [
  { key: 'schema', label: '字段 Schema' },
  { key: 'json',   label: 'JSON 模板' },
  { key: 'cmd',    label: '命令' },
]
const INGEST_SCHEMA = `name      必填，标品名称（如"拙政园"）
city      城市（如"苏州"）
address   街道地址
level     景区等级（A/AAAA/AAAAA；非景区类留空）
open_time 开放时间（如"08:00-17:30"）
ticket    门票信息（"淡季70元/旺季90元"）
description 简介（≤400字）`
const INGEST_JSON = `[
  {
    "name": "拙政园",
    "city": "苏州",
    "address": "姑苏区东北街178号",
    "level": "AAAAA",
    "open_time": "07:30-17:30",
    "ticket": "淡季70元/旺季90元",
    "description": "江南古典园林代表；分东中西三部分。"
  }
]`
const INGEST_CMD = `# 1. CSV / JSON 入库
python -m scripts.sync_rag_corpus \\
  --source file \\
  --file ./spots.json \\
  --job-id corpus:spots:v1 \\
  --verify "拙政园 门票"

# 2. 政务平台 URL 拉取
python -m scripts.sync_rag_corpus \\
  --source url \\
  --url https://data.xxx.gov.cn/poi.json \\
  --param city=北京 --param size=50

# 3. 高德 POI 实时拉取（需 AMAP_API_KEY）
python -m scripts.sync_rag_corpus \\
  --source amap --city 北京 --keywords 风景名胜 --size 25`
</script>

<style scoped>
.rag-lab { display: flex; flex-direction: column; gap: 18px; }

.rl-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; }
.rl-eyebrow { font-size: 11.5px; color: var(--text-faint); letter-spacing: .18em; font-weight: 700; }
.rl-title { margin: 4px 0 6px; font-size: 24px; font-weight: 800; color: var(--text); letter-spacing: -.01em; }
.rl-sub { font-size: 13px; color: var(--text-dim); max-width: 720px; line-height: 1.6; margin: 0; }

.rl-head-actions { display: flex; gap: 10px; }

/* KPI */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi { padding: 16px 18px; }
.kpi-label { font-size: 11.5px; color: var(--text-faint); font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.kpi-num { font-size: 26px; font-weight: 800; color: var(--text); margin-top: 6px; font-variant-numeric: tabular-nums; line-height: 1.1; }
.kpi-num small { font-size: 12.5px; color: var(--text-faint); font-weight: 500; }
.kpi-num.warn { color: var(--danger); }
.kpi-foot { margin-top: 6px; font-size: 11.5px; color: var(--text-faint); }

/* Grid */
.rl-grid { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr); gap: 18px; align-items: start; }
@media (max-width: 1100px) { .rl-grid { grid-template-columns: 1fr; } }

.rl-pane { padding: 18px 20px; display: flex; flex-direction: column; gap: 14px; }
.pane-title { font-size: 15px; font-weight: 800; color: var(--text); display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.pane-title .badge { background: var(--brand); color: #04202E; font-size: 11px; padding: 2px 8px; border-radius: 999px; }

.pane-controls { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 10px; }
.ctrl { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-dim); }
.ctrl input, .ctrl select {
  background: var(--bg); border: 1px solid var(--line); color: var(--text);
  border-radius: 8px; padding: 7px 10px; font-size: 13px; font-family: inherit;
}
.ctrl input:focus, .ctrl select:focus { outline: none; border-color: var(--brand); }

.rl-presets { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 12.5px; color: var(--text-dim); }
.chip-outline {
  background: transparent; border: 1px solid var(--line); color: var(--text-dim);
  padding: 4px 10px; border-radius: 999px; font-size: 12px; cursor: pointer;
}
.chip-outline:hover { background: var(--bg-hover); color: var(--text); border-color: var(--brand); }

.rl-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; font-size: 11.5px; color: var(--text-dim); padding-top: 6px; border-top: 1px dashed var(--line); }
.rl-legend strong { color: var(--text); margin-right: 4px; }
.leg { display: inline-flex; align-items: center; gap: 5px; }
.leg i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }

/* 命中块 */
.rl-side { display: flex; flex-direction: column; }
.chunk-stack { display: flex; flex-direction: column; gap: 10px; }
.chunk { padding: 14px 16px; }
.chunk-head { display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--text-dim); flex-wrap: wrap; }
.c-no { background: var(--brand); color: #04202E; padding: 2px 8px; border-radius: 4px; font-weight: 800; font-size: 11.5px; }
.c-doc { color: var(--text); font-weight: 600; }
.c-tenant { padding: 1px 7px; background: rgba(56,189,248,.13); color: var(--brand); border-radius: 999px; font-size: 11px; }
.c-d { margin-left: auto; font-weight: 800; font-variant-numeric: tabular-nums; font-size: 13px; }
.chunk-body { margin: 8px 0 10px; }
.c-text { font-size: 13px; line-height: 1.65; color: var(--text); white-space: pre-wrap; word-break: break-word; }
.c-text.collapsed { display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.link-btn { background: none; border: none; color: var(--brand); font-size: 12px; cursor: pointer; padding: 0; margin-top: 4px; }
.link-btn:hover { text-decoration: underline; }
.chunk-bar { height: 4px; border-radius: 2px; background: var(--line); overflow: hidden; }
.chunk-bar i { display: block; height: 100%; transition: width .35s; }

/* 历史 */
.hist { display: flex; flex-direction: column; }
.hist-row {
  display: grid; grid-template-columns: 28px 1fr auto auto auto;
  gap: 10px; align-items: center;
  padding: 9px 4px; border-bottom: 1px dashed var(--line);
  font-size: 12.5px; cursor: pointer;
}
.hist-row:hover { background: var(--bg-hover); }
.hist-i { color: var(--text-faint); font-variant-numeric: tabular-nums; font-weight: 700; text-align: right; }
.hist-q { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hist-meta { color: var(--text-faint); font-size: 11.5px; }
.hist-time { color: var(--text-faint); font-size: 11px; font-variant-numeric: tabular-nums; }

.empty { padding: 32px 18px; text-align: center; color: var(--text-dim); }
.empty .icon { font-size: 32px; opacity: .5; }
.empty p { margin: 6px 0 0; font-size: 13px; }

/* 标品目录 */
.hint-text { font-size: 11.5px; color: var(--text-faint); font-weight: 400; }
.prod-cat-stack { display: flex; flex-direction: column; gap: 12px; }
.prod-cat-block {
  background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
  padding: 10px 12px;
}
.prod-cat-head {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 700; color: var(--text);
  padding-bottom: 6px; border-bottom: 1px dashed var(--line); margin-bottom: 6px;
}
.prod-cat-icon { font-size: 16px; }
.prod-cat-label { flex: 1; }
.prod-cat-count {
  background: var(--brand); color: #04202E;
  padding: 1px 8px; border-radius: 999px; font-size: 11px;
}
.prod-cat-items { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; }
.prod-cat-items li {
  display: grid; grid-template-columns: 1fr auto auto auto;
  gap: 8px; align-items: center;
  font-size: 12.5px; color: var(--text-dim);
  padding: 3px 0;
}
.prod-name { color: var(--text); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prod-city { font-size: 11.5px; color: var(--text-faint); }
.prod-time { font-size: 11.5px; }
.prod-d { font-size: 11.5px; font-weight: 700; font-variant-numeric: tabular-nums; }

/* 入库指引 */
.ingest-tabs {
  display: flex; gap: 4px; padding: 4px;
  background: var(--bg); border-radius: 8px;
  margin-bottom: 10px;
}
.itab {
  flex: 1; background: none; border: none;
  padding: 6px 10px; border-radius: 6px;
  font-size: 12px; color: var(--text-dim); cursor: pointer;
  font-family: inherit;
}
.itab:hover { color: var(--text); }
.itab.active { background: var(--brand); color: #04202E; font-weight: 700; }
.ingest-pre {
  background: #04202E; color: #94e2d5;
  padding: 12px 14px; border-radius: 8px;
  font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
  font-size: 12px; line-height: 1.65;
  overflow-x: auto; max-height: 320px;
  margin: 0;
}
.ingest-tip { font-size: 12px; color: var(--text-faint); margin-top: 8px; line-height: 1.6; }
.ingest-tip code {
  background: var(--bg); padding: 1px 5px; border-radius: 4px;
  font-size: 11.5px;
}
</style>