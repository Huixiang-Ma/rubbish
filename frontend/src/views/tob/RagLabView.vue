<script setup>
import { ref, computed } from 'vue'
import TobIcon from '../../components/TobIcon.vue'
import { ragApi } from '../../api/index.js'

const question = ref('拙政园雨天有什么备选安排?')
const topK = ref(4)
const tenantId = ref('')
const mode = ref('sync')
const asked = ref(false)
const asking = ref(false)
const answerText = ref('')

/* RAG 实验台：POST /api/rag/ask（真实向量检索 + LLM 生成/拒答） */
const history = ref([])
const chunks = ref([])

const PRESETS = [
  '北京故宫附近 500 米内有哪些酒店?',
  '拙政园雨天备选?',
  '西湖游船可以带宠物吗?',
  '大理三月街具体日期?',
]

async function ask(preset) {
  const q = preset || question.value
  if (!q || asking.value) return
  question.value = q
  asking.value = true
  asked.value = true
  answerText.value = ''
  try {
    const res = await ragApi.ask(q, topK.value, tenantId.value || null)
    const hit = res.mode === 'llm' || res.mode === 'retrieval'
    history.value.unshift({ q, hit, d: res.distance ?? (hit ? 0.4 : 0.9) })
    answerText.value = res.answer || (res.mode === 'refusal'
      ? '知识库检索置信度不足,按拒答策略处理,不编造答案。'
      : '知识库暂无相关语料。')
    chunks.value = (res.sources || []).map(src => ({
      doc: src.source || src.title || src.doc || 'kb_chunk',
      tenant: src.tenant || '',
      d: src.distance ?? src.score ?? 0.5,
      text: src.chunk || src.text || src.snippet || '',
    }))
    mode.value = res.mode || 'sync'
  } catch (e) {
    answerText.value = `检索服务暂不可用(${e.message || '网络异常'})`
  } finally { asking.value = false }
}

/* 导出调用日志：history/chunks → JSON 下载 */
function exportLog() {
  const blob = new Blob([JSON.stringify({ history: history.value, chunks: chunks.value }, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `rag-log-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

function distColor(d) {
  if (d < 0.40) return 'var(--ok)'
  if (d < 0.65) return 'var(--accent-3)'
  if (d < 0.80) return 'var(--warn)'
  return 'var(--danger)'
}

const hitRate = computed(() => history.value.length ? Math.round(history.value.filter(h => h.hit).length / history.value.length * 100) : 0)
const refusalRate = computed(() => history.value.length ? Math.round(history.value.filter(h => !h.hit).length / history.value.length * 100) : 0)
const avgDistance = computed(() => history.value.length ? (history.value.reduce((s, h) => s + h.d, 0) / history.value.length).toFixed(2) : '—')
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">知识 · 实验台</div>
        <h1 class="page-title">RAG 实验室</h1>
        <p class="page-desc">
          调试检索质量 / 跑通拒答阈值 / 观察分块粒度。同一份知识库,对外服务于 toC AI 导游问答,
          对内为产品和运营提供「问答质检」工具。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="exportLog"><TobIcon name="download" :size="14" />导出调用日志</button>
        <button class="btn btn-ghost btn-sm" @click="history = []; chunks = []">清空历史</button>
      </div>
    </div>

    <!-- 指标 -->
    <div class="stat-grid">
      <div class="stat-card"><div class="k">累计提问</div><div class="v">{{ history.length }}</div><div class="sub">本次会话</div></div>
      <div class="stat-card"><div class="k">命中率</div><div class="v">{{ hitRate }}%</div><div class="sub">top-1 距离 ≤ 0.8</div></div>
      <div class="stat-card"><div class="k">拒答率</div><div class="v" :style="{ color: refusalRate >= 30 ? 'var(--danger)' : 'var(--text)' }">{{ refusalRate }}%</div><div class="sub">距离 > 0.8 时拒答</div></div>
      <div class="stat-card"><div class="k">平均距离</div><div class="v">{{ avgDistance }}</div><div class="sub">越小越相关</div></div>
    </div>

    <div class="rl-grid">
      <!-- 测试台 -->
      <section class="card rl-pane">
        <div class="pane-title">检索测试台</div>
        <div class="rl-controls">
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

        <div class="ask-box">
          <textarea v-model="question" rows="2" placeholder="例:北京故宫附近 500 米内有哪些酒店?拙政园雨天备选?" />
          <button class="btn btn-primary-soft btn-sm" :disabled="asking" @click="ask()">{{ asking ? "检索中…" : "提交问题" }}</button>
        </div>

        <div v-if="asked" class="answer">
          <div class="ans-label">回答</div>
          <p>拙政园遇雨天,建议将动线调整为以「听雨轩」「留听阁」为核心的室内廊道动线 —— 雨打芭蕉正是园中经典意境;同时可顺访全室内的苏州博物馆(步行约 5 分钟)。若逢雷雨,摇橹船可能停航,可改签或退票(夜游场次一般 16:00 前公告)。</p>
        </div>

        <div class="presets">
          <span class="presets-label">回归用例:</span>
          <button v-for="q in PRESETS" :key="q" class="chip chip-sm" @click="ask(q)">{{ q }}</button>
        </div>

        <div class="legend">
          <strong>距离阈值色带</strong>
          <span class="leg"><i style="background:var(--ok)"></i>&lt; 0.40 紧相关</span>
          <span class="leg"><i style="background:var(--accent-3)"></i>0.40-0.65 可参考</span>
          <span class="leg"><i style="background:var(--warn)"></i>0.65-0.80 边缘</span>
          <span class="leg"><i style="background:var(--danger)"></i>≥ 0.80 拒答</span>
        </div>
      </section>

      <!-- 右侧 -->
      <section class="rl-side">
        <div class="card">
          <div class="pane-title" style="margin-bottom:var(--s-4)">
            命中块可视化
            <span class="tag" style="margin-left:var(--s-2)">{{ chunks.length }} 块</span>
          </div>
          <div class="chunk-stack">
            <div v-for="(c, i) in chunks" :key="i" class="chunk">
              <div class="chunk-head">
                <span class="c-no">#{{ i + 1 }}</span>
                <span class="c-doc">{{ c.doc }}</span>
                <span v-if="c.tenant" class="tag tag-accent-2">{{ c.tenant }}</span>
                <span class="c-d mono-xs" :style="{ color: distColor(c.d) }">d = {{ c.d.toFixed(2) }}</span>
              </div>
              <p class="c-text">{{ c.text }}</p>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="pane-title" style="margin-bottom:var(--s-4)">调用历史</div>
          <div class="hist-rows">
            <div v-for="(h, i) in history" :key="i" class="hist-row">
              <span class="h-q">{{ h.q }}</span>
              <span class="tag" :class="h.hit ? 'tag-ok' : 'tag-danger'">{{ h.hit ? '命中' : '拒答' }}</span>
              <span class="mono-xs" :style="{ color: distColor(h.d) }">{{ h.d.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.rl-grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: var(--s-4); align-items: start; }
.rl-pane { display: flex; flex-direction: column; gap: var(--s-4); }
.rl-side { display: flex; flex-direction: column; gap: var(--s-4); }

.rl-controls { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--s-3); }
.ctrl { display: flex; flex-direction: column; gap: 6px; }
.ctrl span { font-size: var(--fs-xs); color: var(--text-3); font-weight: var(--fw-medium); }
.ctrl input, .ctrl select {
  height: 36px; padding: 0 var(--s-3);
  background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--r);
  font-size: var(--fs-sm); color: var(--text);
}
.ctrl input:focus, .ctrl select:focus { outline: none; border-color: var(--text); }
.ctrl input::placeholder { color: var(--text-faint); }

.ask-box { display: flex; flex-direction: column; gap: var(--s-2); align-items: flex-end; }
.ask-box textarea {
  width: 100%; padding: var(--s-3) var(--s-4);
  background: var(--surface-2);
  border: 1px solid var(--border); border-radius: var(--r);
  font-size: var(--fs-sm); color: var(--text);
  line-height: var(--lh-base); resize: vertical;
  font-family: inherit;
}
.ask-box textarea:focus { outline: none; border-color: var(--text); background: var(--surface); }

.answer {
  background: var(--accent-soft);
  border-radius: var(--r);
  padding: var(--s-4);
}
.ans-label {
  font-size: var(--fs-xs); color: var(--accent);
  font-weight: var(--fw-semi); margin-bottom: var(--s-2);
  text-transform: uppercase; letter-spacing: 0.08em;
}
.answer p { font-size: var(--fs-sm); color: var(--text-2); line-height: var(--lh-loose); }

.presets { display: flex; flex-wrap: wrap; gap: var(--s-2); align-items: center; }
.presets-label { font-size: var(--fs-xs); color: var(--text-faint); }

.legend { display: flex; flex-wrap: wrap; gap: var(--s-4); align-items: center; }
.legend strong { font-size: var(--fs-xs); color: var(--text-3); font-weight: var(--fw-medium); }
.leg { display: inline-flex; align-items: center; gap: 6px; font-size: var(--fs-xs); color: var(--text-faint); }
.leg i { width: 8px; height: 8px; border-radius: 2px; }

.chunk-stack { display: flex; flex-direction: column; gap: var(--s-2); }
.chunk {
  padding: var(--s-3) var(--s-4);
  background: var(--surface-2);
  border: 1px solid var(--border-soft);
  border-radius: var(--r);
  transition: border-color var(--dur-1) var(--ease);
}
.chunk:hover { border-color: var(--border-strong); }
.chunk-head { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.c-no {
  font-family: var(--mono); font-size: var(--fs-xs);
  color: var(--text-faint);
}
.c-doc { font-family: var(--mono); font-size: var(--fs-xs); color: var(--accent-3); }
.c-d { margin-left: auto; font-weight: var(--fw-medium); }
.c-text { margin-top: var(--s-2); font-size: var(--fs-xs); color: var(--text-2); line-height: var(--lh-base); }

.hist-rows { display: flex; flex-direction: column; }
.hist-row {
  display: flex; align-items: center; gap: var(--s-3);
  padding: var(--s-2) 0;
  border-bottom: 1px solid var(--border-soft);
  font-size: var(--fs-sm);
}
.hist-row:last-child { border-bottom: 0; }
.h-q { flex: 1; color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 1100px) {
  .rl-grid { grid-template-columns: 1fr; }
  .rl-controls { grid-template-columns: 1fr; }
}
</style>
