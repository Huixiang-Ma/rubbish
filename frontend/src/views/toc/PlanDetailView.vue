<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { AGENT_FLOW, GUIDES, SWARM_REPORTS, COUNTERFACTS, DEBATES, tripById, catMeta } from './mock.js'
import { plansApi, expApi, ragApi, assistApi, planShopApi } from '../../api/index.js'
import RealMapView from '../../components/RealMapView.vue'
import { tripsStore, itineraryToTrip } from '../../stores/trips.js'

const route = useRoute()
const jobId = computed(() => route.params.jobId)

/* —— 任务状态（GET /api/plans/{id} 轮询 + result 拿结构化行程） —— */
const STATUS = {
  COMPLETED: { label: '已完成', cls: 'ok' },
  RUNNING:   { label: '规划中', cls: 'run' },
  QUEUED:    { label: '排队中', cls: 'wait' },
  PENDING:   { label: '排队中', cls: 'wait' },
  WAITING_BUDGET_APPROVAL: { label: '预算审批中', cls: 'run' },
  WAITING_SAFETY_REVIEW:   { label: '安全复核中', cls: 'run' },
  FAILED:    { label: '失败', cls: 'wait' },
}
const job = ref({
  id: jobId.value, status: 'PENDING', version: 1, currentAgent: null, progress: 0,
  dest: '', origin: '', days: 0, budget: 0, people: 0, customer: '', created: '', parent: null,
  error: '', completedNodes: [],
})
const st = computed(() => STATUS[job.value.status] || STATUS.PENDING)
const isBusy = computed(() => ['RUNNING', 'QUEUED', 'PENDING', 'WAITING_BUDGET_APPROVAL', 'WAITING_SAFETY_REVIEW'].includes(job.value.status))

// 行程书：优先取真实结果（itinerary → 本地行程书），拿不到回退演示数据
const trip = ref(tripById('t001'))
const hasRealTrip = ref(false)

async function refresh() {
  let meta = null
  try {
    meta = await plansApi.status(jobId.value)
  } catch { return }
  job.value = {
    ...job.value,
    id: meta.job_id,
    status: meta.status,
    currentAgent: meta.current_agent || null,
    progress: meta.progress || 0,
    version: meta.version || 1,
    parent: meta.parent_job_id || null,
    created: (meta.created_at || '').replace('T', ' ').slice(0, 16),
    error: meta.error || '',
    completedNodes: meta.completed_nodes || [],
  }
  if (meta.status === 'COMPLETED' && !hasRealTrip.value) {
    try {
      const result = await plansApi.result(jobId.value)
      const converted = itineraryToTrip(result, meta.job_id)
      if (converted) {
        tripsStore.save(converted)
        trip.value = converted
        hasRealTrip.value = true
        job.value.dest = converted.city
        job.value.days = converted.days
        job.value.people = converted.people
        job.value.budget = converted.budget
      }
      loadSameCity()
    } catch { /* 结果尚未生成 */ }
  }
}

let pollTimer = null
function startPolling() {
  stopPolling()
  refresh()
  pollTimer = setInterval(async () => {
    await refresh()
    if (!isBusy.value) stopPolling()
  }, 3000)
}
function stopPolling() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }
onMounted(startPolling)
onBeforeUnmount(stopPolling)
watch(jobId, startPolling)

/* —— tabs —— */
const TABS = [
  { key: 'book',      label: '行程书' },
  { key: 'pipeline',  label: '智能体管线' },
  { key: 'debate',    label: '辩论实录' },
  { key: 'guides',    label: '名导团' },
  { key: 'swarm',     label: '踩点与反事实' },
  { key: 'map',       label: '每日动线' },
  { key: 'rag',       label: 'AI 导游问答' },
  { key: 'assistant', label: '智能问答助手' },
  { key: 'diff',      label: '版本对比' },
]
const tab = ref('book')

/* —— 挂起审批（WAITING_* 状态时出现，POST /api/plans/{id}/approval） —— */
const approvals = computed(() => {
  const s = job.value.status
  if (s === 'WAITING_BUDGET_APPROVAL') {
    return [{ key: 'budget', title: '预算超限审批', desc: job.value.error || `方案总额超出预算,已挂起等待人工审批(当前 v${job.value.version})。`, level: 'warn' }]
  }
  if (s === 'WAITING_SAFETY_REVIEW') {
    return [{ key: 'safety', title: '安全合规提示', desc: job.value.error || '行程触发安全复核规则,已挂起等待人工确认。', level: 'info' }]
  }
  return []
})
const resolved = ref({})
const resolving = ref(false)
async function resolve(k, ok) {
  resolving.value = true
  try {
    await plansApi.approval(jobId.value, {
      decision: ok ? 'approve' : 'reject',
      operator: 'toc-user',
      reason: ok ? '游客端确认放行' : '游客端拒绝,申请调整',
      base_version: job.value.version || 1,
    })
    resolved.value[k] = ok ? '放行' : '拒绝'
    refresh()
  } catch (e) {
    resolved.value[k] = e.message || '提交失败'
  } finally {
    resolving.value = false
  }
}

/* —— 管线（completed_nodes + current_agent） —— */
const agentIdx = computed(() => {
  const i = AGENT_FLOW.findIndex(a => a.key === job.value.currentAgent)
  return i >= 0 ? i : (job.value.status === 'COMPLETED' ? AGENT_FLOW.length : 0)
})
const agentState = (i) => {
  if (job.value.completedNodes.includes(AGENT_FLOW[i].key)) return 'done'
  if (i === agentIdx.value && isBusy.value) return 'now'
  if (job.value.status === 'COMPLETED') return 'done'
  return i < agentIdx.value ? 'done' : 'todo'
}

/* —— 名导团（GET /plans/{id}/guides + POST dialogue） ——
 * guidesSource: real=后端角色（dialogue 可用）；fallback=内置演示角色（本地模拟回复）
 */
const GUIDES_LIST = ref(GUIDES)
const guidesSource = ref('fallback')
const activeGuide = ref(GUIDES[0].id)
const guide = computed(() => GUIDES_LIST.value.find(g => g.id === activeGuide.value) || GUIDES_LIST.value[0])
const chat = ref([{ role: 'guide', text: GUIDES[0].hello }])
const draft = ref('')
const thinking = ref(false)
async function loadGuides() {
  try {
    const res = await expApi.guides(jobId.value)
    const rows = (res && res.reviews) || []
    if (rows.length) {
      const colors = ['#7B8DA0', '#B08968', '#6B7A5C', '#8B7A9E']
      guidesSource.value = 'real'
      GUIDES_LIST.value = rows.map((g, i) => ({
        id: g.id, name: g.name, persona: g.persona || '', tone: g.tone || '',
        review: g.review || '', avatar: (g.name || '导')[0], color: colors[i % colors.length],
        hello: g.review || '这条线的取舍我认可，细节可以继续问我。',
      }))
      activeGuide.value = GUIDES_LIST.value[0].id
      if (chat.value.length <= 1) chat.value = [{ role: 'guide', text: GUIDES_LIST.value[0].hello }]
    }
  } catch { /* 回退内置名导 */ }
}
async function send() {
  if (!draft.value.trim() || thinking.value) return
  chat.value.push({ role: 'me', text: draft.value.trim() })
  const message = draft.value.trim()
  draft.value = ''
  thinking.value = true
  // 演示名导（后端无此角色）：本地模拟回复,避免"未找到该角色"
  if (guidesSource.value !== 'real') {
    setTimeout(() => {
      thinking.value = false
      chat.value.push({ role: 'guide', text: `（演示模式）关于「${message.slice(0, 16)}」——这条线的取舍我认可,细节可以继续问我。` })
    }, 900)
    draft.value = ''
    return
  }
  try {
    const res = await expApi.dialogue(jobId.value, {
      guide_id: activeGuide.value,
      message,
      history: chat.value.slice(-6, -1).map(m => ({ role: m.role === 'me' ? 'user' : 'assistant', content: m.text })),
    })
    chat.value.push({ role: 'guide', text: res.reply || '（对方暂时离线）' })
  } catch (e) {
    chat.value.push({ role: 'guide', text: `网络开小差了:${e.message || '稍后再试'}` })
  } finally {
    thinking.value = false
  }
}
function pickGuide(g) {
  activeGuide.value = g.id
  chat.value = [{ role: 'guide', text: g.hello }]
}

/* —— RAG 问答（POST /api/rag/ask，知识库真实检索） —— */
const ragQ = ref('')
const ragA = ref(null)
const ragBusy = ref(false)
const RAG_FAQ = [
  { q: '第一天的景点需要提前预约吗?', a: '', src: [] },
  { q: '当地十月穿什么?', a: '', src: [] },
  { q: '晚上出行安全吗?', a: '', src: [] },
]
async function askRag(item) {
  const q = item ? item.q : ragQ.value
  if (!q || ragBusy.value) return
  ragBusy.value = true
  try {
    const res = await ragApi.ask(q, 3)
    ragA.value = {
      q,
      a: res.answer || '知识库暂未命中该问题,已转人工管家(预计 10 分钟内回复)。',
      src: (res.sources || []).map(s => s.source || s.title || s.doc || '').filter(Boolean),
      jobIds: (res.sources || []).map(s => s.job_id).filter(Boolean),
    }
  } catch (e) {
    ragA.value = { q, a: `问答服务暂不可用(${e.message || '网络异常'}),请稍后再试。`, src: [] }
  } finally {
    ragBusy.value = false
  }
}

/* 语料反馈：对回答 👍/👎（回传被引用的语料 job_id） */
const ragVerdict = ref('')
async function ragVote(v) {
  if (!ragA.value || ragVerdict.value) return
  ragVerdict.value = v
  try {
    await ragApi.ragFeedback(ragA.value.q, v, ragA.value.jobIds || [])
  } catch { /* 反馈失败静默 */ }
}

/* 环6 转化：COMPLETED 后推荐同城在售方案 */
const sameCityPlans = ref([])
async function loadSameCity() {
  const city = job.value.dest || trip.value?.city
  if (!city) return
  try {
    const res = await planShopApi.list({ city, page: 1, page_size: 3 })
    sameCityPlans.value = (res.items || []).map(p => ({
      id: p.id, name: p.name || p.title, city: p.city, days: p.days,
      perPrice: p.per_price,
      emoji: (p.cover && p.cover.emoji) || '🧭',
      gradient: (p.cover && p.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)',
    })).filter(p => p.name)
  } catch { /* 未登录/网络异常：不展示 */ }
}

/* —— 踩点与反事实（GET swarm / counterfactual） —— */
const SWARM_LIST = ref(SWARM_REPORTS)
const CF_LIST = ref(COUNTERFACTS)
async function loadSwarm() {
  try {
    const res = await expApi.swarm(jobId.value)
    const rows = (res && res.reports) || []
    if (rows.length) {
      SWARM_LIST.value = rows.map(r => ({
        persona: r.persona, style: r.style, day: `Day ${r.day}`, theme: r.theme,
        verdict: /合适|友好|良好/.test(r.verdict || '') ? '合适' : '偏累',
        tip: r.tip || r.verdict || '',
      }))
    }
  } catch { /* 回退演示数据 */ }
  try {
    const res = await expApi.counterfactual(jobId.value)
    const cards = (res && res.cards) || []
    if (cards.length) {
      CF_LIST.value = cards.map(c => ({
        giveup: c.gave_up || c.giveup || '', got: c.got || '',
        reason: c.reason || '', cost: c.cost_note || c.cost || '',
      }))
    }
  } catch { /* 回退演示数据 */ }
}

/* —— 每日动线图（真实地图） —— */
const mapSpots = computed(() => {
  const out = []
  trip.value.dayPlans.forEach((d, di) => {
    d.items.forEach((it, ii) => {
      if (it.stop.x != null) out.push({ name: it.stop.name, lat: it.stop.y, lng: it.stop.x, day: di + 1, cat: it.stop.cat })
    })
  })
  return out
})
watch(tab, async (k) => {
  if (k === 'guides' && GUIDES_LIST.value === GUIDES) loadGuides()
  if (k === 'swarm' && SWARM_LIST.value === SWARM_REPORTS) loadSwarm()
  if (k === 'debate' && DEBATES_LIST.value === DEBATES) loadDebates()
  if (k === 'diff' && DIFF.value === DIFF_FALLBACK) loadDiff()
})

/* —— 辩论实录（GET /plans/{id}/debates） —— */
const DEBATES_FALLBACK = DEBATES
const DEBATES_LIST = ref(DEBATES)
async function loadDebates() {
  try {
    const res = await expApi.debates(jobId.value)
    const rows = (res && res.debates) || []
    if (rows.length) {
      DEBATES_LIST.value = rows.map(d => ({
        topic: d.topic || '',
        plan: (d.plan_side && d.plan_side.point) || '',
        traveler: (d.traveler_side && d.traveler_side.point) || '',
        verdict: [d.verdict && d.verdict.decision, d.verdict && d.verdict.reason].filter(Boolean).join(' · ') || '',
        pro: 68,
      }))
    }
  } catch { /* 回退演示数据 */ }
}

/* —— 版本对比（GET /plans/{id}/diff，父版本行级 diff） —— */
const DIFF_FALLBACK = [
  { v: 'v1', date: '', note: '首版', removed: [], added: [], budget: 0 },
]
const DIFF = ref(DIFF_FALLBACK)
async function loadDiff() {
  if (!job.value.parent) return // 非重规划任务无父版本，保留占位
  try {
    const res = await plansApi.diff(jobId.value)
    const addLines = (res.lines || []).filter(l => l.type === 'add').map(l => l.text).filter(t => t && !t.startsWith('#')).slice(0, 6)
    const delLines = (res.lines || []).filter(l => l.type === 'del').map(l => l.text).filter(t => t && !t.startsWith('#')).slice(0, 6)
    DIFF.value = [{
      v: `v${job.value.version}`,
      date: (job.value.created || '').slice(5, 16),
      note: `与父版本 ${res.parent_job_id} 的行级对比:新增 ${res.added} 行 / 删除 ${res.removed} 行`,
      removed: delLines,
      added: addLines,
      budget: job.value.budget || 0,
    }]
  } catch { /* 无父版本或结果未生成:保留占位 */ }
}

/* —— 头部动作：分享 / 反馈 / 增量重规划 / 评分 —— */
const toastMsg = ref('')
let toastTimer = null
function toast(text) {
  toastMsg.value = text
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 2600)
}
function share() {
  const url = `${location.origin}${location.pathname}#/share/${jobId.value}`
  navigator.clipboard?.writeText(url).then(
    () => toast('分享链接已复制'),
    () => toast(url),
  )
}
const replanning = ref(false)
async function replan(preset) {
  const change = preset || window.prompt('描述要调整的内容,例如:Day3 加一个下午茶 / 预算压到 2500')
  if (!change || replanning.value) return
  replanning.value = true
  try {
    const res = await plansApi.replan(jobId.value, { change_request: change, base_version: job.value.version || 1 })
    toast(`已创建增量重规划任务 ${res.job_id}`)
    window.location.hash = `#/plan/${res.job_id}`
  } catch (e) {
    toast(e.message || '重规划失败')
  } finally {
    replanning.value = false
  }
}
async function sendFeedback() {
  const content = window.prompt('写下你对本行程的反馈(表扬 / 投诉都可以):')
  if (!content) return
  try {
    await plansApi.feedback(jobId.value, { kind: 'praise', operator: '游客', content })
    toast('反馈已提交,感谢你的声音')
  } catch (e) {
    toast(e.message || '反馈提交失败')
  }
}

/* —— 评分 modal（POST /plans/{id}/rating + 沉淀 / 上架） —— */
const showRate = ref(false)
const stars = ref(5)
const toKnowledge = ref(true)
const toShelf = ref(true)
const rating = ref(false)
async function submitRate() {
  if (rating.value) return
  rating.value = true
  try {
    await assistApi.rate(jobId.value, { score: stars.value, comment: '' })
    const tips = []
    if (stars.value >= 4 && toKnowledge.value) { try { await assistApi.rateIngest(jobId.value); tips.push('已沉淀至知识库') } catch {} }
    if (stars.value >= 4 && toShelf.value) { try { await assistApi.rateListing(jobId.value); tips.push('已提交上架审核') } catch {} }
    toast(tips.length ? `评分已提交,${tips.join('、')}` : '评分已提交')
    showRate.value = false
  } catch (e) {
    toast(e.message || '评分提交失败')
  } finally {
    rating.value = false
  }
}
</script>

<template>
  <div class="plan-detail">
    <div class="container">

      <!-- 头卡 -->
      <header class="pd-head card">
        <div class="pd-main">
          <div class="pd-line">
            <span class="status-tag" :class="st.cls">{{ st.label }}</span>
            <span class="pd-dest">{{ job.dest }}</span>
            <span class="pd-from">从 {{ job.origin }} 出发</span>
            <span class="pd-ver">{{ job.version }}</span>
          </div>
          <h1 class="pd-title">AI 行程规划任务 <code class="pd-id">{{ job.id }}</code></h1>
          <div class="pd-meta">
            <span>{{ job.days }} 天</span><i>·</i>
            <span>预算 ¥{{ job.budget.toLocaleString() }}</span><i>·</i>
            <span>{{ job.people }} 人</span><i>·</i>
            <span>{{ job.customer }}</span><i>·</i>
            <span>创建于 {{ job.created }}</span>
            <RouterLink v-if="job.parent" :to="`/plan/${job.parent}`" class="pd-parent">← 父任务 {{ job.parent }}</RouterLink>
          </div>
          <div v-if="job.status === 'RUNNING'" class="pd-progress">
            <div class="pg-track"><div class="pg-bar" :style="{ width: job.progress + '%' }"></div></div>
            <span class="pg-text">{{ job.currentAgent || '排队中' }} 智能体工作中 · {{ job.progress }}%</span>
          </div>
          <p v-if="st.label !== '已完成' && job.error" class="pg-text" style="color:#B0685C">⚠ {{ job.error }}</p>
        </div>
        <div class="pd-actions">
          <button class="btn btn-ghost btn-sm" @click="share">分享</button>
          <button class="btn btn-ghost btn-sm" @click="showRate = true">评分</button>
          <button class="btn btn-ghost btn-sm" @click="sendFeedback">反馈</button>
          <button class="btn btn-ghost btn-sm" :disabled="replanning" @click="replan()">增量重规划</button>
          <RouterLink v-if="trip" :to="`/trip/${trip.id}`" class="btn btn-primary btn-sm">查看行程书 →</RouterLink>
        </div>
      </header>

      <!-- 挂起审批 -->
      <section v-if="approvals.length" class="approvals">
        <div v-for="a in approvals" :key="a.key" class="ap-card card" :class="a.level">
          <div class="ap-ico">{{ a.level === 'warn' ? '⚠' : 'ⓘ' }}</div>
          <div class="ap-body">
            <b>{{ a.title }}</b>
            <p>{{ a.desc }}</p>
          </div>
          <div v-if="!resolved[a.key]" class="ap-btns">
            <button class="btn btn-primary btn-sm" :disabled="resolving" @click="resolve(a.key, true)">放行</button>
            <button class="btn btn-ghost btn-sm" :disabled="resolving" @click="resolve(a.key, false)">拒绝</button>
          </div>
          <span v-else class="ap-done" :class="{ ok: resolved[a.key] === '放行' }">{{ resolved[a.key] }}</span>
        </div>
      </section>

      <!-- tabs -->
      <nav class="pd-tabs">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
      </nav>

      <!-- 同城可售方案推荐（转化位） -->
      <section v-if="tab === 'book' && sameCityPlans.length" class="card tab-card">
        <h4 class="sc-title">📍 {{ job.dest }}在售方案 · 懒人可直接整订</h4>
        <div class="sc-row">
          <RouterLink v-for="p in sameCityPlans" :key="p.id" :to="`/malls/product/${p.id}`" class="sc-item">
            <span class="sc-emoji" :style="{ background: p.gradient }">{{ p.emoji }}</span>
            <div class="sc-info">
              <b>{{ p.name }}</b>
              <span>{{ p.city }} · {{ p.days }} 天</span>
            </div>
            <span class="sc-price">¥{{ (p.perPrice || 0).toLocaleString() }}</span>
          </RouterLink>
          <RouterLink to="/malls" class="sc-more">全部方案 →</RouterLink>
        </div>
      </section>

      <!-- ① 行程书 -->
      <section v-if="tab === 'book'" class="card tab-card">
        <div v-for="d in trip.dayPlans" :key="d.day" class="day-block">
          <div class="day-head">
            <span class="day-no">D{{ d.day }}</span>
            <div>
              <b class="day-title">{{ d.title }}</b>
              <p class="day-summary">{{ d.summary }}</p>
            </div>
            <span class="day-stat">{{ d.items.length }} 站</span>
          </div>
          <div v-for="it in d.items" :key="it.stop.id + it.time" class="stop-row">
            <span class="stop-time">{{ it.time }}</span>
            <i class="stop-dot" :style="{ background: catMeta(it.stop.cat).color }"></i>
            <span class="stop-emoji">{{ catMeta(it.stop.cat).emoji }}</span>
            <div class="stop-info">
              <b>{{ it.stop.name }}</b>
              <span>{{ it.stop.dwell }} · {{ it.stop.city }} · {{ it.stop.price ? '¥' + it.stop.price : '免费' }}</span>
            </div>
            <span class="stop-note" :title="it.stop.note">{{ it.stop.note }}</span>
          </div>
        </div>
      </section>

      <!-- ② 管线 -->
      <section v-else-if="tab === 'pipeline'" class="card tab-card">
        <div class="flow">
          <div v-for="(a, i) in AGENT_FLOW" :key="a.key" class="flow-node" :class="agentState(i)">
            <div class="fn-dot">
              <span v-if="agentState(i) === 'done'">✓</span>
              <span v-else-if="agentState(i) === 'now'" class="pulse"></span>
            </div>
            <b class="fn-name">{{ a.label }}</b>
            <span class="fn-key">{{ a.key }}</span>
            <p class="fn-desc">{{ a.desc }}</p>
            <span v-if="agentState(i) === 'now'" class="fn-live">执行中</span>
          </div>
        </div>
        <div class="flow-note">
          当前流水线为 10-Agent 串行架构,{{ AGENT_FLOW[agentIdx]?.label }} 完成后将自动流转至
          {{ AGENT_FLOW[agentIdx + 1]?.label || '终态' }}。
        </div>
      </section>

      <!-- ③ 辩论实录 -->
      <section v-else-if="tab === 'debate'" class="card tab-card">
        <div class="live-box">
          <span class="live-dot"></span> 直播 · Debate 智能体
          <span class="live-line">主持:现在进入第二轮质询,请规划方回应游客方关于 Day2 密度的质疑——</span>
        </div>
        <div v-for="(d, i) in DEBATES_LIST" :key="i" class="debate-card">
          <h4 class="db-topic">议题 {{ i + 1 }} · {{ d.topic }}</h4>
          <div class="db-cols">
            <div class="db-col plan"><span class="db-tag">规划方</span><p>{{ d.plan }}</p></div>
            <div class="db-col traveler"><span class="db-tag">游客方</span><p>{{ d.traveler }}</p></div>
          </div>
          <div class="db-verdict"><b>裁决:</b>{{ d.verdict }}</div>
          <div class="db-vote">
            <div class="vote-track"><div class="vote-bar" :style="{ width: d.pro + '%' }"></div></div>
            <span>{{ d.pro }}% 用户认同该裁决</span>
          </div>
        </div>
      </section>

      <!-- ④ 名导团 -->
      <section v-else-if="tab === 'guides'" class="card tab-card">
        <div class="guide-wrap">
          <aside class="guide-list">
            <button v-for="g in GUIDES" :key="g.id" class="guide-card" :class="{ on: g.id === activeGuide }" @click="pickGuide(g)">
              <span class="g-avatar" :style="{ background: g.color }">{{ g.avatar }}</span>
              <div>
                <b>{{ g.name }}</b>
                <span class="g-persona">{{ g.persona }}</span>
                <span class="g-review">{{ g.review }}</span>
              </div>
            </button>
          </aside>
          <div class="chat-area">
            <div class="chat-head">
              <b>{{ guide.name }}</b><span class="g-tone">{{ guide.tone }}</span>
            </div>
            <div class="chat-body">
              <div v-for="(m, i) in chat" :key="i" class="msg" :class="m.role">{{ m.text }}</div>
              <div v-if="thinking" class="msg guide typing">{{ guide.name }} 正在斟酌措辞…</div>
            </div>
            <div class="chat-input">
              <input v-model="draft" placeholder="向名导提问,例如:带老人走这条线累吗?" @keyup.enter="send" />
              <button class="btn btn-primary btn-sm" @click="send">发送</button>
            </div>
          </div>
        </div>
      </section>

      <!-- ⑤ 踩点与反事实 -->
      <section v-else-if="tab === 'swarm'" class="card tab-card">
        <h4 class="sec-title">虚拟游客踩点报告</h4>
        <div class="swarm-grid">
          <div v-for="(r, i) in SWARM_LIST" :key="i" class="swarm-card">
            <div class="sw-head">
              <b>{{ r.persona }}</b>
              <span class="sw-verdict" :class="r.verdict === '合适' ? 'ok' : 'warn'">{{ r.verdict }}</span>
            </div>
            <span class="sw-style">{{ r.style }} · {{ r.day }} · {{ r.theme }}</span>
            <p>{{ r.tip }}</p>
          </div>
        </div>
        <h4 class="sec-title">反事实推演(为什么放弃这些点)</h4>
        <div class="cf-grid">
          <div v-for="(c, i) in CF_LIST" :key="i" class="cf-card">
            <div class="cf-line"><span class="cf-no">❌ 放弃</span>{{ c.giveup }}</div>
            <div class="cf-line"><span class="cf-yes">✓ 换成</span>{{ c.got }}</div>
            <p class="cf-reason">{{ c.reason }}</p>
            <span class="cf-cost">{{ c.cost }}</span>
          </div>
        </div>
      </section>

      <!-- ⑥ 每日动线 -->
      <section v-else-if="tab === 'map'" class="card tab-card">
        <RealMapView :spots="mapSpots" height="440px" />
        <p class="map-tip">虚线为同一日内的移动顺序;散点颜色代表首个停留点的品类。</p>
      </section>

      <!-- ⑦ RAG 问答 -->
      <section v-else-if="tab === 'rag'" class="card tab-card">
        <div class="rag-ask">
          <input v-model="ragQ" placeholder="问 AI 导游,例如:拙政园要预约吗" @keyup.enter="askRag()" />
          <button class="btn btn-primary btn-sm" @click="askRag()">提问</button>
        </div>
        <div class="rag-faqs">
          <button v-for="f in RAG_FAQ" :key="f.q" class="faq-chip" @click="askRag(f)">{{ f.q }}</button>
        </div>
        <div v-if="ragA" class="rag-answer">
          <b class="ra-q">Q · {{ ragA.q }}</b>
          <p class="ra-a">{{ ragA.a }}</p>
          <div class="rag-vote">
            这个回答有帮助吗？
            <button :class="{ on: ragVerdict === 'up' }" @click="ragVote('up')">👍</button>
            <button :class="{ on: ragVerdict === 'down' }" @click="ragVote('down')">👎</button>
          </div>
          <div class="ra-src">
            <span class="ra-src-tag">Grounding</span>
            <span v-for="s in ragA.src" :key="s" class="ra-src-item">{{ s }}</span>
          </div>
        </div>
      </section>

      <!-- ⑧ 智能问答助手 -->
      <section v-else-if="tab === 'assistant'" class="card tab-card">
        <div class="asst-hello">
          我是本任务的规划助手,可以直接下达指令:<b>「Day3 加一个下午茶」「预算压到 2500」「换成亲子节奏」</b>,我会触发增量重规划。
        </div>
        <div class="asst-cmds">
          <button class="cmd-chip" @click="replan('Day3 加一个下午茶')">Day3 加一个下午茶</button>
          <button class="cmd-chip" @click="replan('预算压到 2500')">预算压到 ¥2,500</button>
          <button class="cmd-chip" @click="replan('换成亲子慢节奏')">换成亲子慢节奏</button>
          <button class="cmd-chip" @click="replan('D2 换掉虎丘')">D2 换掉虎丘</button>
        </div>
      </section>

      <!-- ⑨ 版本对比 -->
      <section v-else-if="tab === 'diff'" class="card tab-card">
        <div class="diff-timeline">
          <div v-for="(v, i) in DIFF" :key="v.v" class="diff-item" :class="{ final: i === DIFF.length - 1 }">
            <div class="df-badge">{{ v.v }}</div>
            <div class="df-body">
              <div class="df-head">
                <b>{{ v.date }}</b>
                <span class="df-budget">预算 ¥{{ v.budget.toLocaleString() }}</span>
                <span v-if="i === DIFF.length - 1" class="df-final-tag">当前版本</span>
              </div>
              <p class="df-note">{{ v.note }}</p>
              <div class="df-changes">
                <span v-for="r in v.removed" :key="r" class="df-ch no">− {{ r }}</span>
                <span v-for="a in v.added" :key="a" class="df-ch yes">+ {{ a }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 轻提示 -->
    <div v-if="toastMsg" class="toast-tip">{{ toastMsg }}</div>

    <!-- 评分 modal -->
    <div v-if="showRate" class="modal-mask" @click.self="showRate = false">
      <div class="modal card">
        <h3>为本次 AI 规划评分</h3>
        <div class="rate-stars">
          <button v-for="n in 5" :key="n" :class="{ on: n <= stars }" @click="stars = n">★</button>
        </div>
        <label class="ck"><input v-model="toKnowledge" type="checkbox" /> 高分方案沉淀至知识库攻略</label>
        <label class="ck"><input v-model="toShelf" type="checkbox" /> 同步上架至方案馆(企业审核后)</label>
        <div class="modal-btns">
          <button class="btn btn-ghost btn-sm" @click="showRate = false">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="rating" @click="submitRate">提交评分</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plan-detail { padding: var(--s-7) 0 var(--s-9); }
.container { display: flex; flex-direction: column; gap: var(--s-5); }

/* 头卡 */
.pd-head { display: flex; justify-content: space-between; gap: var(--s-5); padding: var(--s-5) var(--s-6); flex-wrap: wrap; }
.pd-line { display: flex; align-items: center; gap: var(--s-3); }
.status-tag { font-size: var(--fs-xs); font-weight: var(--fw-bold); padding: 3px 10px; border-radius: var(--r-pill); }
.status-tag.ok { background: var(--ok-soft, #E8F0E6); color: #4C7A5A; }
.status-tag.run { background: #EDF1F7; color: #5C7A9D; }
.status-tag.wait { background: var(--surface-2); color: var(--text-3); }
.pd-dest { font-size: var(--fs-sm); font-weight: var(--fw-bold); }
.pd-from, .pd-ver { font-size: var(--fs-xs); color: var(--text-3); }
.pd-ver { padding: 2px 8px; border-radius: var(--r-sm); background: var(--surface-2); }
.pd-title { font-size: var(--fs-xl); font-weight: var(--fw-bold); margin-top: var(--s-3); letter-spacing: -0.01em; }
.pd-id { font-size: var(--fs-xs); color: var(--text-faint); background: var(--surface-2); padding: 2px 8px; border-radius: var(--r-sm); }
.pd-meta { display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; margin-top: var(--s-3); font-size: var(--fs-sm); color: var(--text-2); }
.pd-meta i { color: var(--text-faint); font-style: normal; }
.pd-parent { font-size: var(--fs-xs); color: var(--accent); margin-left: var(--s-2); }
.pd-actions { display: flex; align-items: flex-start; gap: var(--s-2); flex-wrap: wrap; }
.pd-progress { margin-top: var(--s-4); max-width: 420px; }
.pg-track { height: 6px; background: var(--surface-2); border-radius: var(--r-pill); overflow: hidden; }
.pg-bar { height: 100%; background: var(--accent); border-radius: var(--r-pill); transition: width .6s var(--ease); }
.pg-text { font-size: var(--fs-xs); color: var(--text-3); margin-top: 6px; display: block; }

/* 审批 */
.approvals { display: flex; flex-direction: column; gap: var(--s-3); }
.ap-card { display: flex; align-items: center; gap: var(--s-4); padding: var(--s-4) var(--s-5); border-left: 3px solid var(--accent-3, #7B8DA0); }
.ap-card.warn { border-left-color: var(--warn, #B08968); }
.ap-ico { flex: none; font-size: 18px; }
.ap-body b { font-size: var(--fs-sm); }
.ap-body p { font-size: var(--fs-xs); color: var(--text-3); margin-top: 3px; }
.ap-btns { display: flex; gap: var(--s-2); margin-left: auto; flex: none; }
.ap-done { margin-left: auto; font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--danger, #B0685C); }
.ap-done.ok { color: #4C7A5A; }

/* tabs */
.pd-tabs { display: flex; gap: 2px; padding: 4px; background: var(--surface-2); border-radius: var(--r); width: fit-content; max-width: 100%; overflow-x: auto; }
.pd-tabs button { border: none; background: transparent; padding: 8px var(--s-4); border-radius: calc(var(--r) - 3px); font-size: var(--fs-sm); color: var(--text-3); white-space: nowrap; font-weight: var(--fw-medium); }
.pd-tabs button.on { background: var(--surface); color: var(--text); box-shadow: var(--shadow-xs); font-weight: var(--fw-bold); }
.tab-card { padding: var(--s-5) var(--s-6); }

/* 行程书 */
.day-block + .day-block { margin-top: var(--s-6); padding-top: var(--s-5); border-top: 1px solid var(--border-soft); }
.day-head { display: flex; align-items: flex-start; gap: var(--s-3); margin-bottom: var(--s-3); }
.day-no { font-weight: var(--fw-bold); color: var(--accent); font-size: var(--fs-md); flex: none; }
.day-title { font-size: var(--fs-md); }
.day-summary { font-size: var(--fs-xs); color: var(--text-3); margin-top: 2px; }
.day-stat { margin-left: auto; font-size: var(--fs-xs); color: var(--text-faint); flex: none; }
.stop-row { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0 var(--s-2) var(--s-2); }
.stop-time { width: 96px; flex: none; font-size: var(--fs-xs); color: var(--text-3); font-variant-numeric: tabular-nums; }
.stop-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.stop-emoji { flex: none; }
.stop-info b { font-size: var(--fs-sm); display: block; }
.stop-info span { font-size: var(--fs-xs); color: var(--text-faint); }
.stop-note { margin-left: auto; font-size: var(--fs-xs); color: var(--text-faint); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 管线 */
.flow { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--s-3); }
.flow-node { padding: var(--s-4); border: 1px solid var(--border-soft); border-radius: var(--r); background: var(--surface); position: relative; }
.flow-node.done { border-color: #D6E0D8; background: #F4F7F2; }
.flow-node.now { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(107,122,92,.1); }
.fn-dot { width: 22px; height: 22px; border-radius: 50%; background: var(--surface-2); color: #4C7A5A; display: flex; align-items: center; justify-content: center; font-size: 12px; margin-bottom: var(--s-2); }
.flow-node.done .fn-dot { background: #E8F0E6; }
.flow-node.now .fn-dot { background: var(--accent); }
.pulse { width: 8px; height: 8px; border-radius: 50%; background: #fff; animation: pulse 1.2s infinite; }
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: .3 } }
.fn-name { font-size: var(--fs-sm); display: block; }
.fn-key { font-size: 10px; color: var(--text-faint); }
.fn-desc { font-size: var(--fs-xs); color: var(--text-3); margin-top: var(--s-2); line-height: 1.5; }
.fn-live { position: absolute; top: var(--s-3); right: var(--s-3); font-size: 10px; color: var(--accent); font-weight: var(--fw-bold); }
.flow-note { margin-top: var(--s-4); font-size: var(--fs-xs); color: var(--text-faint); }

/* 辩论 */
.live-box { display: flex; align-items: center; gap: var(--s-2); font-size: var(--fs-xs); color: var(--text-3); background: var(--surface-2); border-radius: var(--r); padding: var(--s-3) var(--s-4); margin-bottom: var(--s-4); }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--danger, #B0685C); animation: pulse 1.4s infinite; }
.live-line { color: var(--text-2); }
.debate-card + .debate-card { margin-top: var(--s-5); }
.db-topic { font-size: var(--fs-md); margin-bottom: var(--s-3); }
.db-cols { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
.db-col { border-radius: var(--r); padding: var(--s-4); font-size: var(--fs-sm); line-height: 1.6; }
.db-col.plan { background: #EDF1F7; }
.db-col.traveler { background: #F5EFE7; }
.db-tag { display: inline-block; font-size: var(--fs-xs); font-weight: var(--fw-bold); margin-bottom: var(--s-2); color: #5C7A9D; }
.db-col.traveler .db-tag { color: #9A7B54; }
.db-verdict { margin-top: var(--s-3); padding: var(--s-3) var(--s-4); background: #EEF0EA; border-radius: var(--r); font-size: var(--fs-sm); }
.db-vote { display: flex; align-items: center; gap: var(--s-3); margin-top: var(--s-3); font-size: var(--fs-xs); color: var(--text-3); }
.vote-track { flex: 1; max-width: 260px; height: 6px; background: var(--surface-2); border-radius: var(--r-pill); overflow: hidden; }
.vote-bar { height: 100%; background: var(--accent); border-radius: var(--r-pill); }

/* 名导团 */
.guide-wrap { display: grid; grid-template-columns: 280px 1fr; gap: var(--s-5); }
.guide-list { display: flex; flex-direction: column; gap: var(--s-3); }
.guide-card { display: flex; gap: var(--s-3); text-align: left; padding: var(--s-4); border: 1px solid var(--border-soft); border-radius: var(--r); background: var(--surface); cursor: pointer; transition: all var(--dur-1) var(--ease); }
.guide-card.on { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(107,122,92,.1); }
.g-avatar { width: 42px; height: 42px; border-radius: 50%; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: var(--fw-bold); flex: none; }
.guide-card b { font-size: var(--fs-sm); display: block; }
.g-persona { font-size: var(--fs-xs); color: var(--text-3); display: block; margin-top: 2px; }
.g-review { font-size: 11px; color: var(--text-faint); display: block; margin-top: 2px; }
.chat-area { display: flex; flex-direction: column; border: 1px solid var(--border-soft); border-radius: var(--r); overflow: hidden; min-height: 420px; }
.chat-head { padding: var(--s-3) var(--s-4); border-bottom: 1px solid var(--border-soft); display: flex; align-items: center; gap: var(--s-3); }
.g-tone { font-size: var(--fs-xs); color: var(--text-faint); }
.chat-body { flex: 1; padding: var(--s-4); display: flex; flex-direction: column; gap: var(--s-3); overflow-y: auto; background: var(--surface-2); }
.msg { max-width: 78%; padding: var(--s-3) var(--s-4); border-radius: 14px; font-size: var(--fs-sm); line-height: 1.6; }
.msg.guide { background: var(--surface); border: 1px solid var(--border-soft); border-bottom-left-radius: 4px; align-self: flex-start; }
.msg.me { background: var(--accent); color: #fff; border-bottom-right-radius: 4px; align-self: flex-end; }
.msg.typing { color: var(--text-faint); font-style: italic; }
.chat-input { display: flex; gap: var(--s-2); padding: var(--s-3); border-top: 1px solid var(--border-soft); }
.chat-input input { flex: 1; }

/* swarm */
.sec-title { font-size: var(--fs-md); margin: var(--s-2) 0 var(--s-3); }
.swarm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--s-3); }
.swarm-card { border: 1px solid var(--border-soft); border-radius: var(--r); padding: var(--s-4); }
.sw-head { display: flex; justify-content: space-between; align-items: center; gap: var(--s-2); }
.sw-head b { font-size: var(--fs-sm); }
.sw-verdict { font-size: var(--fs-xs); font-weight: var(--fw-bold); padding: 2px 10px; border-radius: var(--r-pill); }
.sw-verdict.ok { background: #E8F0E6; color: #4C7A5A; }
.sw-verdict.warn { background: #F5EFE7; color: #9A7B54; }
.sw-style { font-size: var(--fs-xs); color: var(--text-faint); display: block; margin: 4px 0 var(--s-2); }
.swarm-card p { font-size: var(--fs-xs); color: var(--text-2); line-height: 1.6; }
.cf-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--s-3); }
.cf-card { border: 1px dashed var(--border); border-radius: var(--r); padding: var(--s-4); background: var(--surface-2); }
.cf-line { font-size: var(--fs-sm); display: flex; align-items: center; gap: var(--s-2); }
.cf-no { color: var(--danger, #B0685C); font-size: var(--fs-xs); font-weight: var(--fw-bold); flex: none; }
.cf-yes { color: #4C7A5A; font-size: var(--fs-xs); font-weight: var(--fw-bold); flex: none; }
.cf-reason { font-size: var(--fs-xs); color: var(--text-3); margin: var(--s-2) 0; line-height: 1.6; }
.cf-cost { font-size: var(--fs-xs); color: var(--accent); font-weight: var(--fw-medium); }

/* map */
.agent-map { height: 440px; }
.map-tip { font-size: var(--fs-xs); color: var(--text-faint); margin-top: var(--s-3); }

/* rag */
.rag-vote { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs); color: var(--text-3); margin-bottom: var(--s-2); }
.rag-vote button { border: 1px solid var(--border); background: var(--surface); border-radius: var(--r-sm); padding: 2px 10px; cursor: pointer; }
.rag-vote button.on { border-color: var(--accent); background: var(--accent-soft); }
.sc-title { font-size: var(--fs-md); margin-bottom: var(--s-3); }
.sc-row { display: flex; flex-direction: column; gap: var(--s-2); }
.sc-item { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) var(--s-3); border: 1px solid var(--border-soft); border-radius: var(--r); text-decoration: none; color: inherit; }
.sc-item:hover { border-color: var(--accent); }
.sc-emoji { width: 38px; height: 38px; border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center; font-size: 18px; flex: none; }
.sc-info { flex: 1; display: flex; flex-direction: column; }
.sc-info b { font-size: var(--fs-sm); }
.sc-info span { font-size: var(--fs-xs); color: var(--text-faint); }
.sc-price { font-weight: var(--fw-bold); color: #B0685C; }
.sc-more { font-size: var(--fs-xs); color: var(--accent); text-decoration: none; align-self: flex-end; }
/* rag */
.rag-ask { display: flex; gap: var(--s-2); }
.rag-ask input { flex: 1; }
.rag-faqs { display: flex; gap: var(--s-2); flex-wrap: wrap; margin: var(--s-3) 0; }
.faq-chip { border: 1px solid var(--border); background: var(--surface); border-radius: var(--r-pill); padding: 5px var(--s-3); font-size: var(--fs-xs); color: var(--text-2); cursor: pointer; transition: all var(--dur-1) var(--ease); }
.faq-chip:hover { border-color: var(--accent); color: var(--accent); }
.rag-answer { border-top: 1px solid var(--border-soft); padding-top: var(--s-4); }
.ra-q { font-size: var(--fs-md); }
.ra-a { font-size: var(--fs-sm); color: var(--text-2); line-height: 1.7; margin: var(--s-2) 0 var(--s-3); }
.ra-src { display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; }
.ra-src-tag { font-size: 10px; font-weight: var(--fw-bold); color: var(--accent); border: 1px solid var(--accent); border-radius: var(--r-sm); padding: 1px 6px; }
.ra-src-item { font-size: var(--fs-xs); color: var(--text-faint); background: var(--surface-2); padding: 2px 8px; border-radius: var(--r-sm); }

/* assistant */
.asst-hello { font-size: var(--fs-sm); color: var(--text-2); line-height: 1.7; padding: var(--s-4); background: var(--surface-2); border-radius: var(--r); }
.asst-cmds { display: flex; gap: var(--s-2); flex-wrap: wrap; margin-top: var(--s-4); }
.cmd-chip { border: 1px solid var(--accent); color: var(--accent); background: transparent; border-radius: var(--r-pill); padding: 7px var(--s-4); font-size: var(--fs-sm); cursor: pointer; transition: all var(--dur-1) var(--ease); }
.cmd-chip:hover { background: var(--accent); color: #fff; }

/* diff */
.diff-timeline { position: relative; padding-left: var(--s-4); border-left: 2px solid var(--border-soft); display: flex; flex-direction: column; gap: var(--s-5); margin-left: 10px; }
.diff-item { position: relative; }
.df-badge { position: absolute; left: calc(-1 * var(--s-4) - 22px); top: 0; width: 30px; height: 30px; border-radius: 50%; background: var(--surface-2); color: var(--text-3); font-size: var(--fs-xs); font-weight: var(--fw-bold); display: flex; align-items: center; justify-content: center; border: 2px solid var(--surface); }
.diff-item.final .df-badge { background: var(--accent); color: #fff; }
.df-head { display: flex; align-items: center; gap: var(--s-3); font-size: var(--fs-sm); }
.df-budget { font-size: var(--fs-xs); color: var(--text-3); }
.df-final-tag { font-size: 10px; color: var(--accent); border: 1px solid var(--accent); padding: 1px 8px; border-radius: var(--r-pill); }
.df-note { font-size: var(--fs-xs); color: var(--text-3); margin: 4px 0 var(--s-2); }
.df-changes { display: flex; gap: var(--s-2); flex-wrap: wrap; }
.df-ch { font-size: var(--fs-xs); padding: 2px 10px; border-radius: var(--r-sm); }
.df-ch.no { background: #F6EBE9; color: #A8665C; text-decoration: line-through; }
.df-ch.yes { background: #E8F0E6; color: #4C7A5A; }

/* modal */
.toast-tip {
  position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%);
  background: rgba(31,29,26,.86); color: #fff; font-size: var(--fs-sm);
  padding: 10px var(--s-5); border-radius: var(--r-pill); z-index: 120;
  box-shadow: var(--shadow); animation: fade-in .2s ease;
}
@keyframes fade-in { from { opacity: 0; transform: translate(-50%, 6px); } to { opacity: 1; transform: translate(-50%, 0); } }
.modal-mask { position: fixed; inset: 0; background: rgba(46,44,40,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { width: min(420px, 90vw); padding: var(--s-6); }
.modal h3 { font-size: var(--fs-md); margin-bottom: var(--s-4); }
.rate-stars { display: flex; gap: var(--s-2); margin-bottom: var(--s-4); }
.rate-stars button { border: none; background: none; font-size: 26px; color: var(--border); cursor: pointer; }
.rate-stars button.on { color: var(--warn, #B08968); }
.ck { display: flex; align-items: center; gap: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); margin-bottom: var(--s-3); cursor: pointer; }
.modal-btns { display: flex; justify-content: flex-end; gap: var(--s-2); margin-top: var(--s-4); }

@media (max-width: 860px) {
  .db-cols { grid-template-columns: 1fr; }
  .guide-wrap { grid-template-columns: 1fr; }
}
</style>
