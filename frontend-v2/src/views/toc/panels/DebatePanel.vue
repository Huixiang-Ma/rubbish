<template>
  <div class="panel">
    <div class="head-row">
      <div class="sec-title" style="margin:0">辩论实录</div>
      <div style="display:flex;gap:10px;align-items:center">
        <span v-if="voteInfo" class="tag tag-purple">{{ voteInfo }}</span>
        <button class="btn btn-ghost btn-sm" @click="liveOpen = !liveOpen">
          {{ liveOpen ? '◼ 停止直播' : '▶ 直播一场新辩论' }}
        </button>
      </div>
    </div>
    <p class="sec-desc">每个关键决策，规划方与游客方各执一词，由裁决官给出最终结论</p>

    <!-- SSE 直播 -->
    <div v-if="liveOpen" class="live-box card">
      <div class="live-title"><span class="dot-red pulse-dot"></span>辩论直播中…</div>
      <div class="live-log" ref="logRef">
        <div v-for="(line, i) in liveLines" :key="i" class="live-line" :class="line.side">
          <b v-if="line.side === 'plan'">[规划方]</b>
          <b v-else-if="line.side === 'traveler'">[游客方]</b>
          <b v-else>[主持]</b>
          {{ line.text }}
        </div>
      </div>
    </div>

    <!-- 辩论双栏 -->
    <div v-if="!debates.length" class="empty"><div class="icon">⚔️</div><p>暂无辩论数据（任务完成后生成）</p></div>
    <div v-else class="debates">
      <div v-for="(d, i) in debates" :key="i" class="card debate-card">
        <div class="d-topic">议题 {{ i + 1 }} · {{ d.topic }}</div>
        <div class="d-cols">
          <div class="d-col plan">
            <div class="d-head">🔵 {{ d.plan_side.role }}</div>
            <p>{{ d.plan_side.point }}</p>
          </div>
          <div class="vs">VS</div>
          <div class="d-col traveler">
            <div class="d-head">🟠 {{ d.traveler_side.role }}</div>
            <p>{{ d.traveler_side.point }}</p>
          </div>
        </div>
        <div class="d-verdict">
          <span class="tag tag-green">裁决 · {{ d.verdict.decision }}</span>
          <span class="v-reason">{{ d.verdict.reason }}</span>
        </div>
      </div>

      <!-- 投票 -->
      <div class="card vote-card">
        <div style="font-weight:800">🗳 你站哪一边？</div>
        <div style="display:flex;gap:12px;margin-top:12px">
          <button class="btn btn-ghost" :disabled="voted" @click="vote('规划方')">我站规划方</button>
          <button class="btn btn-ghost" :disabled="voted" @click="vote('游客方')">我站游客方</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { expApi, api } from '../../../api'
import { toast } from '../../../composables/toast'

const props = defineProps({ jobId: { type: String, required: true } })

const debates = ref([])
const liveOpen = ref(false)
const liveLines = ref([])
const voted = ref(false)
const voteInfo = ref('')
const logRef = ref(null)
let es = null

onMounted(async () => {
  try {
    const r = await expApi.debates(props.jobId)
    debates.value = r.debates || []
  } catch { /* 未完成时 404 */ }
})

function toggleLive() {
  liveOpen.value ? stopLive() : startLive()
}
function startLive() {
  liveLines.value = []
  liveOpen.value = true
  es = api.sse(`/plans/${props.jobId}/debate/live`, (ev) => {
    // 事件格式：{side: 'plan'|'traveler'|'host', text}
    const side = ev.side || (typeof ev === 'string' ? 'host' : 'host')
    const text = ev.text || ev.point || JSON.stringify(ev)
    liveLines.value.push({ side, text })
    nextTick(() => { logRef.value?.scrollTo({ top: 1e9, behavior: 'smooth' }) })
  }, () => {
    liveLines.value.push({ side: 'host', text: '—— 本场辩论结束 ——' })
  })
}
function stopLive() {
  es?.close()
  liveOpen.value = false
}
onUnmounted(() => es?.close())

async function vote(side) {
  try {
    await expApi.debateVote(props.jobId, side)
    voted.value = true
    voteInfo.value = `已投给${side}，票数已写回行程书`
    toast('投票成功', 'ok')
  } catch (e) { toast(e.message, 'err') }
}

defineExpose({ toggleLive })
</script>

<style scoped>
.head-row { display: flex; justify-content: space-between; align-items: center; }
.live-box { padding: 18px 20px; margin-bottom: 18px; background: var(--ink-900); border-color: var(--ink-900); }
.live-title { color: #FCA5A5; font-weight: 700; font-size: 13.5px; display: flex; align-items: center; gap: 7px; margin-bottom: 10px; }
.dot-red { width: 9px; height: 9px; border-radius: 50%; background: #EF4444; }
.live-log { max-height: 260px; overflow-y: auto; font-family: var(--mono); font-size: 13px; line-height: 1.9; }
.live-line { color: #CBD5E1; padding: 2px 0; animation: rise .3s var(--ease); }
.live-line b { margin-right: 4px; }
.live-line.plan b { color: #60A5FA; }
.live-line.traveler b { color: #FBBF24; }
.live-line.host b { color: #94A3B8; }

.debates { display: flex; flex-direction: column; gap: 14px; }
.debate-card { padding: 22px 24px; }
.d-topic { font-weight: 800; font-size: 15.5px; color: var(--ink-900); margin-bottom: 14px; }
.d-cols { display: grid; grid-template-columns: 1fr 46px 1fr; gap: 10px; align-items: stretch; }
.d-col { border-radius: var(--r-md); padding: 15px 17px; font-size: 13.5px; line-height: 1.75; }
.d-col.plan { background: var(--info-bg); }
.d-col.traveler { background: var(--warn-bg); }
.d-head { font-weight: 700; font-size: 13px; margin-bottom: 7px; }
.d-col.plan .d-head { color: var(--brand-700); }
.d-col.traveler .d-head { color: #B45309; }
.vs { display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 12px; color: var(--ink-400); }
.d-verdict { display: flex; align-items: center; gap: 10px; margin-top: 14px; padding-top: 14px; border-top: 1.5px dashed var(--ink-200); font-size: 13.5px; }
.v-reason { color: var(--ink-500); }
.vote-card { padding: 18px 22px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
@media (max-width: 720px) { .d-cols { grid-template-columns: 1fr; } .vs { padding: 4px 0; } }
</style>
