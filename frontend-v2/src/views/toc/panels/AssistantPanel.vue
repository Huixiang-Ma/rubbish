<template>
  <div>
    <div class="sec-title">💬 智能问答助手</div>
    <p class="sec-desc">
      基于知识库检索优先回答；知识库未命中时自动联网搜索（Bing 实时检索 + LLM 有据综合）。
      <em style="color:var(--brand); font-style:normal;">回答会标明来源（知识库 / 联网），命中标品后仍可一键替换行程时段。</em>
    </p>

    <div class="ab-card">
      <div class="ab-log" ref="logRef">
        <div v-if="!messages.length" class="ab-empty">
          <p>问点实际的：门票优惠、近期活动、雨天备选……知识库里有的直接答，没有的帮你联网查。</p>
        </div>
        <div v-for="(m, i) in messages" :key="i" class="ab-msg" :class="m.role">
          <div class="ab-bubble">
            <span v-if="m.source" class="ab-source" :class="m.source">{{ m.source === 'kb' ? '📚 知识库' : m.source === 'web' ? '🌐 联网' : '📋 检索' }}</span>
            <div v-html="renderMd(m.text)"></div>
          </div>
        </div>
        <div v-if="busy" class="ab-msg assistant"><div class="ab-bubble typing">助手思考中…</div></div>
      </div>
      <form class="ab-input" @submit.prevent="send">
        <input v-model.trim="draft" class="input" placeholder="问助手：拙政园对老年人有优惠吗？" />
        <button class="btn btn-primary" :disabled="!draft || busy">发送</button>
      </form>
    </div>
  </div>
</template>

<script setup>
// 需求3：toC RAG 对话助手（知识库未命中走 agent 联网搜索）
import { ref, nextTick } from 'vue'
import { assistApi } from '../../../api'

const props = defineProps({ jobId: { type: String, default: '' } })

const messages = ref([])
const draft = ref('')
const busy = ref(false)
const logRef = ref(null)

function renderMd(text) {
  // 轻量渲染：换行 + 引用编号高亮（防 XSS：先转义再替换）
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return esc(text).replace(/\n/g, '<br>').replace(/\[(\d)\]/g, '<sup class="cite">[$1]</sup>')
}

async function send() {
  const q = draft.value.trim()
  if (!q || busy.value) return
  messages.value.push({ role: 'user', text: q })
  draft.value = ''
  busy.value = true
  scrollBottom()
  try {
    await assistApi.assistantChat(q, 3, {
      onMeta: (m) => { /* 来源模式在 done 时统一入栈 */ },
      onDone: (evt) => {
        messages.value.push({ role: 'assistant', text: evt.answer || '（未取得回答）', source: evt.mode })
        busy.value = false
        scrollBottom()
      },
      onError: (e) => {
        messages.value.push({ role: 'assistant', text: `（助手暂时不可用：${e.message}）`, source: '' })
        busy.value = false
        scrollBottom()
      },
    })
  } catch (e) {
    messages.value.push({ role: 'assistant', text: `（助手暂时不可用：${e.message}）`, source: '' })
    busy.value = false
    scrollBottom()
  }
}

function scrollBottom() { nextTick(() => logRef.value?.scrollTo({ top: 1e9, behavior: 'smooth' })) }
</script>

<style scoped>
.ab-card { margin-top: 18px; border: 1px solid var(--line); border-radius: 14px; overflow: hidden; background: var(--panel); }
.ab-log { max-height: 380px; overflow-y: auto; padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; }
.ab-empty { text-align: center; color: var(--text-faint); font-size: 13px; padding: 22px 0; }
.ab-msg { display: flex; }
.ab-msg.user { justify-content: flex-end; }
.ab-bubble { max-width: 82%; padding: 11px 15px; border-radius: 15px; font-size: 13.5px; line-height: 1.75; }
.ab-msg.assistant .ab-bubble { background: var(--bg-hover); color: var(--text); border-bottom-left-radius: 4px; }
.ab-msg.user .ab-bubble { background: var(--brand); color: #fff; border-bottom-right-radius: 4px; }
.ab-source { display: inline-block; font-size: 10.5px; font-weight: 700; padding: 1px 8px; border-radius: 999px; margin-bottom: 5px; }
.ab-source.kb { background: #ECFDF5; color: #065F46; }
.ab-source.web { background: #EFF6FF; color: #1D4ED8; }
.ab-source.web_retrieval, .ab-source.kb_refusal { background: #FFFBEB; color: #92400E; }
.cite { color: var(--brand); font-weight: 700; }
.typing { color: var(--text-faint); font-style: italic; }
.ab-input { display: flex; gap: 10px; padding: 13px 16px; border-top: 1px solid var(--line); background: var(--bg-hover); }
.ab-input .input { flex: 1; }
</style>
