<template>
  <div>
    <div class="sec-title">名导团点评</div>
    <p class="sec-desc">虚拟名导视角的行程点评，可继续追问细节</p>

    <div v-if="!guides.length" class="empty"><div class="icon">🎓</div><p>暂无点评（任务完成后生成）</p></div>
    <div class="guides">
      <div v-for="g in guides" :key="g.id" class="card guide-card card-hover" :class="{ picked: active?.id === g.id }" @click="pick(g)">
        <div class="g-avatar">{{ g.name[0] }}</div>
        <div class="g-name">{{ g.name }}</div>
        <div class="g-persona">{{ g.persona }}</div>
        <p class="g-review">“{{ g.review }}”</p>
        <div class="g-tone"><span class="tag tag-gray">{{ g.tone }}</span></div>
      </div>
    </div>

    <!-- 对话 -->
    <div v-if="active" class="card dlg-card">
      <div class="dlg-head">💬 与 {{ active.name }} 对话 · <span class="hint-s">{{ active.persona }}</span></div>
      <div class="dlg-log" ref="logRef">
        <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
          <div class="bubble">{{ m.text }}</div>
        </div>
        <div v-if="thinking" class="msg guide"><div class="bubble typing">{{ active.name }} 正在斟酌…</div></div>
      </div>
      <form class="dlg-input" @submit.prevent="send">
        <input v-model.trim="draft" class="input" :placeholder="`问 ${active.name}：Day1 会不会太赶？`" />
        <button class="btn btn-primary" :disabled="!draft || thinking">发送</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { expApi } from '../../../api'
import { toast } from '../../../composables/toast'

const props = defineProps({ jobId: { type: String, required: true } })

const guides = ref([])
const active = ref(null)
const messages = ref([])
const draft = ref('')
const thinking = ref(false)
const logRef = ref(null)

onMounted(async () => {
  try {
    const r = await expApi.guides(props.jobId)
    guides.value = r.reviews || []
    if (guides.value.length) pick(guides.value[0])
  } catch { /* 未完成时 404 */ }
})

function pick(g) {
  active.value = g
  messages.value = [{ role: 'guide', text: g.review }]
}

async function send() {
  if (!draft.value || thinking.value) return
  const q = draft.value
  messages.value.push({ role: 'user', text: q })
  draft.value = ''
  thinking.value = true
  scrollBottom()
  try {
    const r = await expApi.dialogue(props.jobId, {
      guide_id: active.value.id,
      message: q,
      history: messages.value.slice(-10).map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text })),
    })
    messages.value.push({ role: 'guide', text: r.reply || r.answer || r.message || JSON.stringify(r) })
  } catch (e) {
    messages.value.push({ role: 'guide', text: `（${active.value.name}一时语塞：${e.message}）` })
  } finally {
    thinking.value = false
    scrollBottom()
  }
}

function scrollBottom() { nextTick(() => logRef.value?.scrollTo({ top: 1e9, behavior: 'smooth' })) }
</script>

<style scoped>
.guides { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; margin-bottom: 20px; }
.guide-card { padding: 20px 22px; cursor: pointer; }
.guide-card.picked { border-color: var(--brand-500); box-shadow: 0 0 0 3px rgba(59,130,246,.15); }
.g-avatar {
  width: 44px; height: 44px; border-radius: 13px; background: linear-gradient(135deg, var(--purple), #6366F1);
  color: #fff; font-size: 19px; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 10px;
}
.g-name { font-weight: 800; font-size: 15.5px; }
.g-persona { font-size: 12.5px; color: var(--ink-400); margin-top: 2px; }
.g-review { font-size: 13.5px; color: var(--ink-700); margin-top: 10px; line-height: 1.75; }
.g-tone { margin-top: 10px; }

.dlg-card { padding: 0; overflow: hidden; }
.dlg-head { padding: 15px 22px; border-bottom: 1px solid var(--ink-100); font-weight: 700; font-size: 14.5px; background: var(--ink-50); }
.hint-s { font-size: 12.5px; color: var(--ink-400); font-weight: 400; }
.dlg-log { max-height: 340px; overflow-y: auto; padding: 20px 22px; display: flex; flex-direction: column; gap: 12px; }
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 76%; padding: 11px 16px; border-radius: 16px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; }
.msg.guide .bubble { background: var(--ink-100); color: var(--ink-900); border-bottom-left-radius: 4px; }
.msg.user .bubble { background: var(--brand-600); color: #fff; border-bottom-right-radius: 4px; }
.typing { color: var(--ink-400); font-style: italic; }
.dlg-input { display: flex; gap: 10px; padding: 14px 18px; border-top: 1px solid var(--ink-100); background: var(--ink-50); }
</style>
