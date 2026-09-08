<template>
  <div class="ragp" :class="{ 'is-compact': compact }">
    <!-- 提问区 -->
    <div class="ragp-input">
      <textarea
        v-model="question"
        :placeholder="placeholder || '问 AI 导游：景点、票价、玩法、避坑…'"
        :rows="compact ? 2 : 3"
        @keydown.meta.enter.prevent="submit"
        @keydown.ctrl.enter.prevent="submit"
      />
      <div class="ragp-bar">
        <div class="opts">
          <label v-if="showTopK" class="opt">
            <span>top_k</span>
            <input type="range" min="1" max="8" v-model.number="topK" />
            <b>{{ topK }}</b>
          </label>
          <label v-if="showMode" class="opt">
            <span>模式</span>
            <select v-model="mode">
              <option value="sync">同步 ask</option>
              <option value="stream">流式 chat</option>
            </select>
          </label>
          <span v-if="tenant" class="opt-tag">多租户：{{ tenant }}</span>
        </div>
        <div class="acts">
          <button v-if="hint" type="button" class="hint" @click="fillHint">{{ hint }}</button>
          <button class="btn btn-primary" :disabled="!question.trim() || busy" @click="submit">
            {{ busy ? '生成中…' : '提问' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 回答区：占满整个高度时滚动 -->
    <div v-if="hasResult || busy" class="ragp-out" :class="{ 'has-stuff': hasResult || busy }">
      <!-- 状态标签 -->
      <div class="ragp-meta" v-if="lastResult">
        <StatusTag :status="modeOf(lastResult.mode)" />
        <span class="m-text">{{ explain(lastResult.mode) }}</span>
        <span v-if="lastResult.sub_questions?.length > 1" class="m-sub">
          问题拆分为 {{ lastResult.sub_questions.length }} 个子问
        </span>
        <button v-if="resetAble" class="link-btn" @click="reset">清空</button>
      </div>

      <!-- 主体答案 -->
      <div v-if="streamText || lastResult?.answer" class="ragp-answer" @click="onAnswerClick">
        <span v-if="streamText">{{ streamText }}<span class="cursor">▍</span></span>
        <span v-else>{{ lastResult.answer }}</span>
      </div>

      <!-- 拒答 / 空态 -->
      <div v-else-if="lastResult && (lastResult.mode === 'refusal' || lastResult.mode === 'empty')" class="ragp-empty">
        <span class="ico">{{ lastResult.mode === 'empty' ? '🪶' : '🛑' }}</span>
        <h4>{{ lastResult.mode === 'empty' ? '知识库中暂无相关内容' : '未找到密切相关的资料' }}</h4>
        <p v-if="lastResult.mode === 'refusal'">
          最接近的资料块距离 {{ lastResult.sources?.[0]?.distance?.toFixed(3) }}，
          超过阈值 {{ threshold }} —— 出于严谨未作回答，但下列资料可能对你有用：
        </p>
        <p v-else>请换个问法试试，或直接联系客服 →</p>
      </div>

      <!-- 命中块引用面板（始终展示 sources） -->
      <div v-if="lastResult?.sources?.length" class="ragp-sources">
        <div class="rs-head">
          <span>📚 引用溯源 <em>{{ lastResult.sources.length }}</em></span>
          <small>距离越小越相关</small>
        </div>
        <ul class="rs-list">
          <li v-for="(src, i) in lastResult.sources" :key="i" :data-source="i + 1">
            <div class="rs-no" :style="{ background: catColor(parseProduct(src)?.category?.key) }">
              {{ parseProduct(src)?.category?.icon || (i + 1) }}
            </div>
            <div class="rs-body">
              <!-- 标品卡（解析后） -->
              <template v-if="parseProduct(src)?.title">
                <div class="prod-head">
                  <span class="prod-cat" :style="{ color: catColor(parseProduct(src)?.category?.key) }">
                    {{ parseProduct(src)?.category?.icon }} {{ parseProduct(src)?.category?.label }}
                  </span>
                  <span class="prod-title">{{ parseProduct(src)?.title }}</span>
                  <span v-if="src.doc_id" class="prod-doc">📄 {{ src.doc_id }}</span>
                </div>
                <div class="prod-fields">
                  <span v-if="parseProduct(src)?.fields?.city">🌆 {{ parseProduct(src)?.fields?.city }}</span>
                  <span v-if="parseProduct(src)?.fields?.address">📍 {{ parseProduct(src)?.fields?.address }}</span>
                  <span v-if="parseProduct(src)?.fields?.level">⭐ {{ parseProduct(src)?.fields?.level }}</span>
                  <span v-if="parseProduct(src)?.fields?.open_time">🕐 {{ parseProduct(src)?.fields?.open_time }}</span>
                  <span v-if="parseProduct(src)?.fields?.ticket">🎫 {{ parseProduct(src)?.fields?.ticket }}</span>
                </div>
                <div v-if="parseProduct(src)?.fields?.description" class="prod-desc">
                  {{ parseProduct(src)?.fields?.description }}
                </div>
              </template>
              <!-- 兜底：解析失败时显示原文 -->
              <div v-else class="rs-text">{{ src.content }}</div>
              <div class="rs-foot">
                <span class="rs-meta">
                  <em v-if="src.tenant_id">· {{ src.tenant_id }}</em>
                </span>
                <span class="rs-bar" :title="`距离 ${src.distance?.toFixed(3)}`">
                  <i :style="{ width: `${distancePct(src.distance)}%`, background: distanceColor(src.distance) }" />
                </span>
                <b class="rs-d" :style="{ color: distanceColor(src.distance) }">
                  {{ src.distance?.toFixed(3) }}
                </b>
                <button v-if="swappable && parseProduct(src)?.title" class="swap-btn"
                        @click.stop="onSwap(src, i, parseProduct(src))"
                        title="把行程里的某个标品替换为这条">
                  🔁 替换到行程
                </button>
              </div>
            </div>
          </li>
        </ul>
      </div>

      <!-- 子问题拆分 -->
      <div v-if="lastResult?.sub_questions?.length > 1" class="ragp-subs">
        <div class="rs-head"><span>🧩 子问题拆分</span></div>
        <ol>
          <li v-for="(q, i) in lastResult.sub_questions" :key="i">{{ q }}</li>
        </ol>
      </div>
    </div>

    <!-- 错误 -->
    <div v-if="errMsg" class="ragp-err">
      <span>⚠ {{ errMsg }}</span>
      <button @click="errMsg = ''">×</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { ragApi } from '../api'
import StatusTag from './StatusTag.vue'
import { parseProduct } from '../lib/productParser'

const props = defineProps({
  compact: { type: Boolean, default: false },
  mode: { type: String, default: 'both' }, // 'sync' | 'stream' | 'both'
  topK: { type: Number, default: 3 },
  tenant: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  hint: { type: String, default: '' },
  showTopK: { type: Boolean, default: true },
  showMode: { type: Boolean, default: true },
  resetAble: { type: Boolean, default: true },
  swappable: { type: Boolean, default: false }, // 是否在标品卡上显示「替换到行程」
  planId: { type: String, default: '' },          // 当前行程 ID（swap 接口要用）
})
const emit = defineEmits(['answered', 'swap'])

const question = ref('')
const topK = ref(props.topK)
const mode = ref(props.mode === 'both' ? 'stream' : props.mode)

const busy = ref(false)
const streamText = ref('')
const lastResult = ref(null) // 最近一次完整结果
const errMsg = ref('')

let streamAbort = null
const threshold = 0.8

const hasResult = computed(() => !!lastResult.value)

function fillHint() {
  if (props.hint) question.value = props.hint
}

function reset() {
  question.value = ''
  streamText.value = ''
  lastResult.value = null
  errMsg.value = ''
  if (streamAbort) { streamAbort(); streamAbort = null }
}

async function submit() {
  const q = question.value.trim()
  if (!q || busy.value) return
  errMsg.value = ''
  streamText.value = ''
  lastResult.value = null
  busy.value = true

  if (mode.value === 'sync') {
    try {
      const r = await ragApi.ask(q, topK.value, props.tenant || null)
      lastResult.value = r
      emit('answered', r)
    } catch (e) {
      errMsg.value = e.message || '请求失败'
    } finally {
      busy.value = false
    }
    return
  }

  // 流式
  const handle = ragApi.chat(q, topK.value, props.tenant || null, {
    onMeta: ({ sources = [], sub_questions = [] }) => {
      // 先用 meta 预填 sources 展示
      lastResult.value = { mode: 'streaming', answer: '', sources, sub_questions }
    },
    onToken: (text) => {
      streamText.value += text
    },
    onDone: (evt) => {
      // 收尾整合：保留 meta 的 sources / sub_questions
      const meta = lastResult.value || {}
      lastResult.value = {
        mode: evt.mode || 'llm',
        answer: evt.answer || streamText.value || '',
        sources: evt.sources || meta.sources || [],
        sub_questions: evt.sub_questions || meta.sub_questions || [q],
      }
      streamText.value = ''
      busy.value = false
      streamAbort = null
      emit('answered', lastResult.value)
    },
    onError: (evt) => {
      errMsg.value = evt.message || '生成失败'
      busy.value = false
      streamAbort = null
    },
  })
  streamAbort = handle.abort
  handle.promise
}

function modeOf(m) {
  return m || 'unknown'
}
function explain(m) {
  return ({
    llm: 'LLM 有据生成',
    refusal: '距离超阈值，未生成',
    empty: '知识库为空',
    retrieval: '命中但生成不可用',
    streaming: '正在流式接收…',
  })[m] || (m || '未知模式')
}
function distancePct(d) {
  if (typeof d !== 'number') return 0
  // 0 -> 100%, 1+ -> 0%
  return Math.max(0, Math.min(100, (1 - d) * 100))
}
function distanceColor(d) {
  if (typeof d !== 'number') return '#94a3b8'
  if (d < 0.4) return '#10b981'  // 紧相关 绿
  if (d < 0.65) return '#38bdf8' // 可参考 青
  if (d < 0.8) return '#f59e0b'  // 边缘 黄
  return '#ef4444'               // 超阈值 红
}
function catColor(key) {
  return ({
    sight: '#6366f1', food: '#f97316', hotel: '#0ea5e9',
    transit: '#22c55e', shop: '#ec4899', culture: '#a78bfa', other: '#94a3b8',
  })[key] || '#94a3b8'
}
function onAnswerClick(e) {
  // 简单：点击答案里的 [n] 滚动到对应 sources
  const target = e.target
  if (target?.dataset?.ref) {
    const el = document.querySelector(`[data-source="${target.dataset.ref}"]`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}
function onSwap(src, i, parsed) {
  emit('swap', {
    source: src,
    source_index: i,
    product: parsed,
    plan_id: props.planId,
  })
}

onBeforeUnmount(() => { if (streamAbort) streamAbort() })
</script>

<style scoped>
.ragp {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ragp.is-compact { padding: 14px; }

.ragp-input textarea {
  width: 100%; box-sizing: border-box;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px; color: var(--text); font-size: 14px;
  resize: vertical; line-height: 1.5;
  font-family: inherit;
}
.ragp-input textarea:focus { outline: none; border-color: var(--brand); }

.ragp-bar { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; gap: 12px; flex-wrap: wrap; }
.opts { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
.opt { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-dim); }
.opt input[type="range"] { width: 110px; accent-color: var(--brand); }
.opt b { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--text); }
.opt select {
  background: var(--bg); border: 1px solid var(--line); color: var(--text);
  border-radius: 6px; padding: 3px 6px; font-size: 12px;
}
.opt-tag { font-size: 11px; color: var(--text-faint); background: var(--bg); border: 1px solid var(--line); padding: 2px 8px; border-radius: 999px; }

.acts { display: flex; gap: 8px; align-items: center; }
.hint { background: none; border: 1px dashed var(--line); color: var(--text-dim); padding: 5px 10px; border-radius: 7px; font-size: 12px; cursor: pointer; }
.hint:hover { color: var(--brand); border-color: var(--brand); }

.ragp-out { display: flex; flex-direction: column; gap: 14px; }
.ragp-out.has-stuff { border-top: 1px dashed var(--line); padding-top: 14px; }

.ragp-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: 13px; }
.m-text { color: var(--text-dim); }
.m-sub { font-size: 12px; color: var(--text-faint); margin-left: 4px; }
.link-btn { margin-left: auto; background: none; border: none; color: var(--text-faint); font-size: 12px; cursor: pointer; }
.link-btn:hover { color: var(--danger); }

.ragp-answer {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
  line-height: 1.7; font-size: 14px; color: var(--text);
  white-space: pre-wrap; word-break: break-word;
}
.cursor { animation: blinker 1s steps(2) infinite; }
@keyframes blinker { 50% { opacity: 0; } }

.ragp-empty {
  background: var(--bg); border: 1px dashed var(--line);
  border-radius: 10px; padding: 22px 18px; text-align: center;
}
.ragp-empty .ico { font-size: 28px; display: block; margin-bottom: 6px; }
.ragp-empty h4 { margin: 0 0 6px; font-size: 15px; }
.ragp-empty p { margin: 0; font-size: 13px; color: var(--text-dim); }

.ragp-sources { display: flex; flex-direction: column; gap: 8px; }
.rs-head { display: flex; justify-content: space-between; align-items: baseline; font-size: 13px; color: var(--text); font-weight: 700; }
.rs-head small { color: var(--text-faint); font-weight: 400; font-size: 11.5px; }
.rs-head em { font-style: normal; background: var(--brand); color: #04202E; padding: 0 6px; border-radius: 4px; font-size: 11.5px; margin-left: 4px; }
.rs-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.rs-list li {
  display: flex; gap: 10px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px;
}
.rs-no {
  flex: none; width: 24px; height: 24px; border-radius: 6px;
  background: var(--brand); color: #04202E; display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 12.5px;
}
.rs-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.rs-text { font-size: 13px; line-height: 1.6; color: var(--text); word-break: break-word; }
.rs-foot { display: flex; align-items: center; gap: 10px; font-size: 11.5px; color: var(--text-faint); flex-wrap: wrap; }
.rs-meta em { font-style: normal; margin-right: 4px; }
.rs-bar { flex: 1; min-width: 80px; height: 4px; border-radius: 2px; background: var(--line); overflow: hidden; position: relative; }
.rs-bar i { display: block; height: 100%; transition: width .3s; }
.rs-d { font-variant-numeric: tabular-nums; font-weight: 700; }

.ragp-subs ol { margin: 6px 0 0; padding-left: 22px; color: var(--text-dim); font-size: 13px; line-height: 1.7; }

.ragp-err {
  display: flex; align-items: center; justify-content: space-between;
  background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.3);
  border-radius: 8px; padding: 8px 12px; font-size: 13px; color: var(--danger);
}
.ragp-err button { background: none; border: none; color: var(--danger); cursor: pointer; font-size: 16px; }

.is-compact .ragp-answer { padding: 10px 12px; font-size: 13px; }
.is-compact .rs-text { font-size: 12.5px; }

.prod-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.prod-cat {
  font-size: 11px; font-weight: 700;
  background: rgba(99,102,241,.08);
  padding: 2px 7px; border-radius: 5px;
  letter-spacing: .3px;
}
.prod-title { font-size: 14px; font-weight: 700; color: var(--text); }
.prod-doc { font-size: 11px; color: var(--text-faint); }
.prod-fields {
  display: flex; flex-wrap: wrap; gap: 4px 10px;
  font-size: 12px; color: var(--text-dim);
  background: var(--panel);
  border: 1px dashed var(--line);
  border-radius: 6px;
  padding: 6px 8px;
}
.prod-fields span { display: inline-flex; align-items: center; gap: 2px; }
.prod-desc {
  font-size: 12.5px; color: var(--text-dim);
  line-height: 1.55;
  padding: 4px 0 0;
}
.swap-btn {
  margin-left: auto; padding: 3px 9px;
  background: rgba(14,165,233,.08); color: var(--brand);
  border: 1px solid var(--brand); border-radius: 5px;
  font-size: 11px; cursor: pointer; font-weight: 600;
  white-space: nowrap;
}
.swap-btn:hover { background: var(--brand); color: #fff; }
</style>