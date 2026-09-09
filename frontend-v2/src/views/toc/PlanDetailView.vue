<template>
  <div class="container detail">
    <!-- 头部：任务状态卡 -->
    <div class="card head-card rise">
      <div class="head-main">
        <div>
          <div class="head-title">
            <StatusTag :status="job?.status || '…'" />
            <span class="dest">{{ job?.destination || jobId }}</span>
            <span v-if="job?.origin" class="route">从 {{ job.origin }} 出发</span>
            <span v-if="job?.version != null" class="tag tag-gray">v{{ job.version }}</span>
          </div>
          <div class="head-meta" v-if="job">
            {{ job.days }} 天 · 预算 ¥{{ Number(job.budget || 0).toLocaleString() }}
            <template v-if="job.parent_job_id"> · <router-link :to="{ name: 'plan-detail', params: { jobId: job.parent_job_id } }">父任务</router-link></template>
          </div>
        </div>
        <div class="head-actions">
          <button class="btn btn-ghost btn-sm" @click="copyShare">🔗 分享链接</button>
          <button class="btn btn-ghost btn-sm" @click="feedbackOpen = true">📣 反馈</button>
          <button class="btn btn-soft btn-sm" @click="ratingOpen = true">⭐ 评分{{ ratingAvg ? ` ${ratingAvg}` : '' }}</button>
          <button class="btn btn-soft btn-sm" @click="replanOpen = true">✦ 增量重规划</button>
        </div>
      </div>

      <!-- 进度 -->
      <div v-if="job" style="margin-top:18px">
        <div class="progress"><div :style="{ width: (job.progress ?? (job.status === 'COMPLETED' ? 100 : 8)) + '%' }"></div></div>
        <div class="prog-meta">
          <span v-if="polling">智能体流水线运行中（{{ job.current_agent || '排队' }}）…</span>
          <span v-else-if="job.error" class="err">{{ job.error }}</span>
          <span v-else-if="job.status === 'COMPLETED'">全部节点完成 ✓</span>
          <span v-else>{{ job.status }}</span>
        </div>
      </div>
    </div>

    <!-- 挂起审批提示 -->
    <div v-if="job && (job.status === 'WAITING_BUDGET_APPROVAL' || job.status === 'WAITING_SAFETY_REVIEW')" class="card wait-card rise">
      <div class="wait-icon">{{ job.status === 'WAITING_BUDGET_APPROVAL' ? '💰' : '🛡' }}</div>
      <div style="flex:1">
        <b>{{ job.status === 'WAITING_BUDGET_APPROVAL' ? '行程超预算，已挂起' : '检测到风险内容，待人工安全审核' }}</b>
        <p>{{ job.error || '需要你确认后，任务才会从挂起节点继续执行' }}</p>
      </div>
      <div style="display:flex;gap:10px">
        <button class="btn btn-ok" @click="approve('approve')">✓ 放行续跑</button>
        <button class="btn btn-danger" @click="approve('reject')">✕ 拒绝</button>
      </div>
    </div>

    <!-- 标签页 -->
    <div class="tabs" style="margin-top:22px; background:#fff; border-radius: var(--r-lg) var(--r-lg) 0 0; padding: 0 10px;">
      <button v-for="t in TABS" :key="t.key" class="tab" :class="{ active: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
    </div>

    <div class="tab-body card" style="border-radius: 0 0 var(--r-lg) var(--r-lg); border-top: none; min-height: 300px;">
      <!-- 行程书 -->
      <div v-if="tab === 'book'">
        <div v-if="!result && polling" class="loading-block"><div class="spinner spin"></div>行程书生成中，完成后自动展示…</div>
        <div v-else-if="!result" class="empty"><div class="icon">📕</div><p>暂无行程书（{{ job?.status }}）</p></div>
        <template v-else>
          <BookSplit :source="result.travel_plan_md" :sha="result.sha256 || ''"
                     :spots="bookSpots" @replace-spot="openSpotReplace" />
        </template>
      </div>

      <!-- 管线 -->
      <div v-else-if="tab === 'pipeline'">
        <div class="sec-title">智能体管线</div>
        <p class="sec-desc">当前版本 v{{ job?.version ?? '-' }}，已完成 {{ (job?.completed_nodes || []).length }} 个节点</p>
        <div class="steps">
          <div v-for="a in AGENT_FLOW" :key="a.name" class="step"
               :class="{ done: doneSet.has(a.name), doing: job?.current_agent === a.name }">
            <div class="node">{{ doneSet.has(a.name) ? '✓' : a.emoji }}</div>
            <div class="label">{{ a.name }}</div>
          </div>
        </div>
        <div class="sec-title" style="margin-top:36px">审计事件</div>
        <div v-if="!audit.length" class="empty"><div class="icon">📜</div><p>暂无审计事件</p></div>
        <div v-else class="audit-list">
          <div v-for="(a, i) in audit" :key="i" class="audit-item">
            <span class="au-time">{{ a.created_at || a.ts || '' }}</span>
            <span class="tag" :class="auditCls(a)">{{ a.event || a.action || a.type }}</span>
            <span class="au-detail">{{ a.detail || a.message || a.reason || (typeof a.data === 'object' ? JSON.stringify(a.data) : a.data) || a.job_id }}</span>
          </div>
        </div>
      </div>

      <!-- 体验层 -->
      <DebatePanel v-else-if="tab === 'debate'" :job-id="jobId" />
      <GuidePanel v-else-if="tab === 'guides'" :job-id="jobId" />
      <SwarmPanel v-else-if="tab === 'swarm'" :job-id="jobId" />
      <MapPanel v-else-if="tab === 'map'" :job-id="jobId" />

      <!-- AI 导游问答（RAG：基于知识库检索 + LLM 生成） -->
      <div v-else-if="tab === 'rag'">
        <div class="sec-title">AI 导游 · 知识问答</div>
        <p class="sec-desc">
          基于知识库检索（pgvector 向量）+ LLM 有据生成，带距离阈值拒答。问题可被自动拆分为多子问。
          <em style="color:var(--brand); font-style:normal;">命中标品后可一键替换行程里的某个时段</em>。
        </p>
        <RagPanel
          :plan-id="jobId"
          :swappable="true"
          @swap="onSwapRequest"
          placeholder="例：拙政园的门票淡旺季分别多少？哪些景点适合雨天？"
          hint="拙政园门票淡旺季分别多少？"
        />
        <div class="empty" style="margin-top:18px">
          <div class="icon">💡</div>
          <p>回答带 [n] 引用编号 · 距离越小越相关 · 拒答时只列参考不编造 · 命中标品后可点击「替换到行程」一键改写 itinerary</p>
        </div>
      </div>

      <!-- 智能问答助手（需求3：知识库未命中自动联网搜索） -->
      <AssistantPanel v-else-if="tab === 'assistant'" :job-id="jobId" />

      <!-- 版本 diff -->
      <div v-else-if="tab === 'diff'">
        <div class="sec-title">版本对比</div>
        <p class="sec-desc">增量重规划后，与父任务的行级差异（复用节点不重复生成）</p>
        <div v-if="diffErr" class="empty"><div class="icon">🔀</div><p>{{ diffErr }}</p></div>
        <div v-else-if="!diff" class="loading-block"><div class="spinner spin"></div>加载 diff…</div>
        <template v-else>
          <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
            <span class="tag tag-green">+{{ diff.added }} 新增</span>
            <span class="tag tag-red">-{{ diff.removed }} 删除</span>
            <span class="tag tag-gray">= {{ diff.unchanged }} 不变</span>
            <span v-if="diff.truncated" class="tag tag-amber">已截断至 2000 行</span>
          </div>
          <div class="diff-view">
            <div v-for="(l, i) in diff.lines" :key="i" class="dl" :class="l.type">
              <span class="dl-sign">{{ l.type === 'add' ? '+' : l.type === 'del' ? '−' : ' ' }}</span>
              <span class="dl-text">{{ l.text }}</span>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 反馈弹窗 -->
    <AppModal v-if="feedbackOpen" title="提交反馈" @close="feedbackOpen = false">
      <div class="field">
        <label>类型</label>
        <select v-model="fb.kind" class="select">
          <option value="praise">👍 表扬</option>
          <option value="complaint">👎 投诉</option>
        </select>
      </div>
      <div class="field" style="margin-top:12px">
        <label>内容</label>
        <textarea v-model.trim="fb.content" class="textarea" placeholder="说说你的感受…"></textarea>
      </div>
      <template #foot>
        <button class="btn btn-primary" :disabled="!fb.content || fbBusy" @click="sendFeedback">{{ fbBusy ? '提交中…' : '提交' }}</button>
      </template>
    </AppModal>

    <!-- 行程书景点搜索替换（需求6） -->
    <AppModal v-if="spotReplace.open" :title="`🔁 替换「${spotReplace.name}」`" @close="spotReplace.open = false">
      <form class="sp-search" @submit.prevent="searchSpot">
        <input v-model.trim="spotReplace.q" class="input" placeholder="搜索想去的景点 / 餐饮 / 住宿，如「虎丘」「苏帮菜」" />
        <button class="btn btn-primary" :disabled="spotReplace.busy || !spotReplace.q.trim()">搜索</button>
      </form>
      <p class="sp-note">选中新景点后提交增量重规划，只重跑受影响节点（更快更省）。</p>
      <div class="sp-results">
        <div v-for="p in spotReplace.results" :key="p.id" class="sp-row" @click="confirmSpotReplace(p)">
          <span class="sp-emoji">{{ p.category === '餐饮' ? '🍜' : p.category === '住宿' ? '🏨' : '📍' }}</span>
          <div class="sp-body">
            <b>{{ p.name }}</b>
            <em>{{ p.city }} · {{ p.category }} · {{ p.price_min ? '¥' + p.price_min + ' 起' : '免费' }}</em>
          </div>
          <button class="btn btn-ghost btn-sm">替换</button>
        </div>
        <div v-if="!spotReplace.results.length && !spotReplace.busy" class="sp-none">输入关键词搜索标品库</div>
      </div>
    </AppModal>

    <!-- 评分弹窗（需求2）：高分行程可沉淀知识库攻略 / 上架为线路方案 -->
    <AppModal v-if="ratingOpen" title="⭐ 为这趟行程打分" @close="ratingOpen = false">
      <div class="rate-stars">
        <button v-for="n in 5" :key="n" class="star" :class="{ on: n <= ratingForm.score }" @click="ratingForm.score = n">{{ n <= ratingForm.score ? '★' : '☆' }}</button>
        <b class="rate-num">{{ ratingForm.score }} 星</b>
      </div>
      <textarea v-model.trim="ratingForm.comment" class="textarea" style="margin-top:12px" maxlength="200"
                placeholder="这趟行程哪里让你惊喜 / 哪里想调整？（选填，将随攻略一起沉淀）"></textarea>
      <div v-if="ratingGood" class="rate-good">
        ✨ 平均 {{ ratingAvg }} 分 · 可将本行程沉淀为
        <button class="btn btn-ghost btn-sm" :disabled="ingestBusy" @click="ingestGuide">{{ ingestBusy ? '沉淀中…' : '📚 知识库攻略' }}</button>
        <button class="btn btn-ghost btn-sm" :disabled="listingBusy" @click="toListing">{{ listingBusy ? '上架中…' : '🏷 线路方案' }}</button>
      </div>
      <template #foot>
        <button class="btn btn-primary" :disabled="!ratingForm.score || ratingBusy" @click="submitRating">{{ ratingBusy ? '提交中…' : '提交评分' }}</button>
      </template>
    </AppModal>

    <!-- 重规划弹窗 -->
    <AppModal v-if="replanOpen" title="增量重规划" @close="replanOpen = false">
      <p style="font-size:13.5px;color:var(--ink-500);margin-bottom:14px">
        描述你的变更需求，系统只重跑受影响节点（未变部分直接复用，更快更省）。<br />
        例：「预算改为 3000 元，减少打车」
      </p>
      <div class="field">
        <label>变更需求</label>
        <textarea v-model.trim="replanText" class="textarea" placeholder="预算改为3000元，减少打车"></textarea>
      </div>
      <template #foot>
        <button class="btn btn-primary" :disabled="!replanText || rpBusy" @click="doReplan">{{ rpBusy ? '提交中…' : '开始重规划' }}</button>
      </template>
    </AppModal>

    <!-- 替换标品到行程（由 RAG 命中触发） -->
    <AppModal v-if="swapDialog.open" title="🔁 用此标品替换行程" @close="swapDialog.open = false">
      <div class="swap-preview">
        <div class="sp-row">
          <span class="sp-tag">命中标品</span>
          <b>{{ swapDialog.payload?.product?.title }}</b>
          <span class="sp-cat">{{ swapDialog.payload?.product?.category?.label }}</span>
        </div>
        <div class="sp-fields">
          <span v-if="swapDialog.payload?.product?.fields?.city">🌆 {{ swapDialog.payload?.product?.fields?.city }}</span>
          <span v-if="swapDialog.payload?.product?.fields?.level">⭐ {{ swapDialog.payload?.product?.fields?.level }}</span>
          <span v-if="swapDialog.payload?.product?.fields?.open_time">🕐 {{ swapDialog.payload?.product?.fields?.open_time }}</span>
          <span v-if="swapDialog.payload?.product?.fields?.ticket">🎫 {{ swapDialog.payload?.product?.fields?.ticket }}</span>
        </div>
        <div v-if="swapDialog.inspect?.grounding" class="sp-grounding" style="margin-top:8px;font-size:12px;color:var(--ok)">
          📖 知识背书通过（{{ (swapDialog.inspect.grounding.score * 100).toFixed(0) }}%）：{{ swapDialog.inspect.grounding.snippet }}
        </div>
        <div v-else class="sp-grounding" style="margin-top:8px;font-size:12px;color:var(--warn)">
          ⚠ 知识库暂无该标品语料，替换以素材库数据为准
        </div>
      </div>

      <p style="font-size:12.5px;color:var(--ink-500);margin:14px 0 8px">选择要替换的时段</p>
      <div class="field">
        <label>第几天</label>
        <select v-model.number="swapDialog.day" class="textarea" style="min-height:auto;padding:8px 10px">
          <option v-for="d in 3" :key="d" :value="d">第 {{ d }} 天</option>
        </select>
      </div>
      <div class="field">
        <label>时段</label>
        <select v-model.number="swapDialog.slot" class="textarea" style="min-height:auto;padding:8px 10px">
          <option v-for="s in 5" :key="s - 1" :value="s - 1">第 {{ s }} 个时段</option>
        </select>
      </div>

      <div v-if="swapDialog.diff" class="swap-diff">
        <b>替换影响：</b>
        <div class="diff-row"><span>时长变化</span><b>{{ swapDialog.diff.time_delta }}</b></div>
        <div class="diff-row"><span>成本变化</span><b>{{ swapDialog.diff.cost_delta > 0 ? '+' : '' }}¥ {{ swapDialog.diff.cost_delta }}</b></div>
        <div class="diff-row"><span>距离变化</span><b>{{ swapDialog.diff.distance_delta }}</b></div>
        <div v-if="swapDialog.diff.warnings?.length" class="diff-warn">
          ⚠ {{ swapDialog.diff.warnings[0] }}
        </div>
      </div>

      <template #foot>
        <button class="btn btn-primary" :disabled="swapDialog.busy" @click="confirmSwap">
          {{ swapDialog.busy ? '替换中…' : (swapDialog.diff ? '✓ 已替换' : '确认替换') }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { plansApi, swapApi, assistApi, composerApi } from '../../api'
import { toast } from '../../composables/toast'
import { useJobPolling } from '../../composables/useJobPolling'
import StatusTag from '../../components/StatusTag.vue'
import MdView from '../../components/MdView.vue'
import BookSplit from '../../components/BookSplit.vue'
import AppModal from '../../components/AppModal.vue'
import DebatePanel from './panels/DebatePanel.vue'
import GuidePanel from './panels/GuidePanel.vue'
import SwarmPanel from './panels/SwarmPanel.vue'
import MapPanel from './panels/MapPanel.vue'
import RagPanel from '../../components/RagPanel.vue'
import AssistantPanel from './panels/AssistantPanel.vue'

const route = useRoute()
const router = useRouter()
const jobId = route.params.jobId

const TABS = [
  { key: 'book', label: '📕 行程书' },
  { key: 'pipeline', label: '⚙️ 智能体管线' },
  { key: 'debate', label: '⚔️ 辩论实录' },
  { key: 'guides', label: '🎓 名导团' },
  { key: 'swarm', label: '👥 踩点与反事实' },
  { key: 'map', label: '🗺 每日动线' },
  { key: 'rag', label: '🧠 AI 导游问答' },
  { key: 'assistant', label: '💬 智能问答助手' },
  { key: 'diff', label: '🔀 版本对比' },
]
const tab = ref('book')

const AGENT_FLOW = [
  { name: 'Intake', emoji: '📋' }, { name: 'Researcher', emoji: '🔍' }, { name: 'Planner', emoji: '🧭' },
  { name: 'Itinerary', emoji: '🗓' }, { name: 'Budget', emoji: '💰' }, { name: 'Validator', emoji: '✅' },
  { name: 'Sentiment', emoji: '📰' }, { name: 'Debate', emoji: '⚔️' }, { name: 'Mood', emoji: '🎭' }, { name: 'Reporter', emoji: '📕' },
]

const result = ref(null)
const audit = ref([])
const diff = ref(null)
const diffErr = ref('')

const { data: job, polling, start } = useJobPolling(() => plansApi.status(jobId), 2000)

const doneSet = computed(() => new Set(job.value?.completed_nodes || []))

const feedbackOpen = ref(false)
const fb = reactive({ kind: 'praise', content: '' })
const fbBusy = ref(false)

// 评分（需求2）：1-5 星 → 高分可沉淀知识库攻略 / 上架线路方案
const ratingOpen = ref(false)
const ratingForm = reactive({ score: 0, comment: '' })
const ratingAvg = ref(null)
const ratingGood = ref(false)
const ratingBusy = ref(false)
const ingestBusy = ref(false)
const listingBusy = ref(false)

async function loadRating() {
  try {
    const r = await assistApi.getRating(jobId)
    ratingAvg.value = r.avg
    ratingGood.value = !!r.can_ingest
  } catch { /* 静默 */ }
}

async function submitRating() {
  ratingBusy.value = true
  try {
    const r = await assistApi.rate(jobId, { score: ratingForm.score, comment: ratingForm.comment })
    ratingAvg.value = r.avg
    ratingGood.value = !!r.good
    toast(`已评分：${r.avg} 分${r.good ? ' · 可沉淀攻略/上架方案' : ''}`, 'ok')
  } catch (e) { toast(e.message || '评分失败', 'err') } finally { ratingBusy.value = false }
}

async function ingestGuide() {
  ingestBusy.value = true
  try {
    const r = await assistApi.rateIngest(jobId)
    toast(`已沉淀为知识库攻略（${r.kb_id}，RAG 可检索）`, 'ok')
    ratingOpen.value = false
  } catch (e) { toast(e.message || '沉淀失败', 'err') } finally { ingestBusy.value = false }
}

async function toListing() {
  listingBusy.value = true
  try {
    const r = await assistApi.rateListing(jobId)
    toast(`已上架为线路方案「${r.title}」`, 'ok')
    ratingOpen.value = false
  } catch (e) { toast(e.message || '上架失败', 'err') } finally { listingBusy.value = false }
}

const replanOpen = ref(false)
const replanText = ref('')
const rpBusy = ref(false)

// 替换标品到行程
const swapDialog = reactive({ open: false, payload: null, day: 1, slot: 0, diff: null, inspect: null, busy: false })
const itineraryDays = computed(() => {
  // 从 result 里抽出每天有多少个 slot；拿不到时给个兜底
  const days = result.value?.itinerary || (result.value?.itinerary_md ? 2 : 2)
  if (Array.isArray(days)) return days
  return [{ day: 1, blocks: [] }, { day: 2, blocks: [] }]
})
async function onSwapRequest(payload) {
  swapDialog.open = true
  swapDialog.payload = payload
  swapDialog.day = 1
  swapDialog.slot = 0
  swapDialog.diff = null
  // 先做替换影响预检（后端按 RAG 语料背书 + 时长/费用/距离 diff）
  const newId = resolveProductId(payload)
  if (newId && result.value?.itinerary?.length) {
    try {
      swapDialog.inspect = await swapApi.inspect(jobId, {
        day: Number(swapDialog.day), slot_index: Number(swapDialog.slot), new_product_id: newId,
      })
    } catch { swapDialog.inspect = null }
  }
}

// 行程书景点（需求6）：从 result.itinerary 提取停留点名，供行程书内点击替换
const bookSpots = computed(() => {
  const out = []
  for (const d of (result.value?.itinerary || [])) {
    for (const it of (d.items || [])) {
      const n = it?.spot?.name || it?.title
      if (n && !out.includes(n)) out.push(n)
    }
  }
  return out
})

// 行程书内点击景点 → 搜索替换（走增量重规划，只重跑受影响节点）
const spotReplace = reactive({ open: false, name: '', q: '', results: [], busy: false })
function openSpotReplace(name) {
  spotReplace.open = true
  spotReplace.name = name
  spotReplace.q = ''
  spotReplace.results = []
}
async function searchSpot() {
  const q = spotReplace.q.trim()
  if (!q) return
  spotReplace.busy = true
  try {
    const r = await composerApi.searchProducts(q, { top_k: 8 })
    spotReplace.results = (r.results || []).map(x => x.product)
  } catch (e) { toast('搜索失败：' + (e.message || e), 'err') } finally { spotReplace.busy = false }
}
async function confirmSpotReplace(p) {
  spotReplace.busy = true
  try {
    await plansApi.replan(jobId, {
      change_request: `把行程中的「${spotReplace.name}」替换为「${p.name}」，并更新对应景点信息`,
      base_version: Number(result.value?.version || job.value?.version || 1),
    })
    toast(`已提交增量重规划：${spotReplace.name} → ${p.name}，正在重新生成受影响节点`, 'ok')
    spotReplace.open = false
    start(async (j) => { if (j.status === 'COMPLETED') { loadResult(); loadAudit(); toast('重规划完成，行程书已更新', 'ok') } })
  } catch (e) {
    toast(e.message || '重规划提交失败', 'err')
  } finally { spotReplace.busy = false }
}

// RAG 命中块 → 真实标品 id：标品语料块 job_id 形如 cat:p_xxx；
// 非标品语料（amap/文件/url）时回退素材库按名解析
function resolveProductId(payload) {
  const jobId0 = payload?.product?.sourceMeta?.job_id || payload?.source?.job_id || ''
  if (String(jobId0).startsWith('cat:')) return String(jobId0).slice(4)
  return payload?.product?.title || ''
}

async function confirmSwap() {
  swapDialog.busy = true
  try {
    const newId = resolveProductId(swapDialog.payload) || (swapDialog.payload?.product?.title || 'unknown')
    const r = await swapApi.swap(jobId, {
      day: Number(swapDialog.day),
      slot_index: Number(swapDialog.slot),
      new_product_id: newId,
      reason: `RAG 命中替换：${swapDialog.payload?.product?.title}`,
    })
    swapDialog.diff = r.diff
    toast(`已替换第 ${swapDialog.day} 天第 ${Number(swapDialog.slot) + 1} 时段`, 'ok')
    // 重新拉一次行程
    loadResult()
  } catch (e) {
    toast(e.message || '替换失败', 'err')
  } finally {
    swapDialog.busy = false
  }
}

async function loadResult() {
  try { result.value = await plansApi.result(jobId) } catch { result.value = null }
}
async function loadAudit() {
  try { audit.value = (await plansApi.audit(jobId)).items || (await plansApi.audit(jobId)).events || (await plansApi.audit(jobId)) } catch { audit.value = [] }
}

onMounted(() => {
  start(async (j) => {
    if (j.status === 'COMPLETED') {
      toast('行程书已生成 🎉', 'ok')
      loadResult()
      loadAudit()
    }
  })
  loadResult()
  loadAudit()
  loadRating()
})

watch(() => job.value?.status, (s) => {
  if (['WAITING_BUDGET_APPROVAL', 'WAITING_SAFETY_REVIEW', 'REPLAN_REQUIRED'].includes(s)) {
    // 挂起态下 error 信息即原因
  }
})

watch(tab, async (t) => {
  if (t === 'diff' && !diff.value && !diffErr.value) {
    try { diff.value = await plansApi.diff(jobId) }
    catch (e) { diffErr.value = e.message }
  }
})

async function approve(decision) {
  try {
    await plansApi.approval(jobId, {
      decision, operator: '旅者',
      reason: decision === 'approve' ? '用户确认放行' : '用户拒绝',
      base_version: job.value.version,
    })
    toast(decision === 'approve' ? '已放行，任务续跑' : '已拒绝', 'ok')
    start(async (j) => { if (j.status === 'COMPLETED') { loadResult(); loadAudit() } })
  } catch (e) { toast(e.message, 'err') }
}

async function sendFeedback() {
  fbBusy.value = true
  try {
    await plansApi.feedback(jobId, { kind: fb.kind, operator: '旅者', content: fb.content })
    toast('反馈已提交', 'ok')
    feedbackOpen.value = false
    fb.content = ''
  } catch (e) { toast(e.message, 'err') } finally { fbBusy.value = false }
}

async function doReplan() {
  rpBusy.value = true
  try {
    const r = await plansApi.replan(jobId, { change_request: replanText.value, base_version: job.value?.version ?? 1 })
    toast('已创建重规划子任务', 'ok')
    replanOpen.value = false
    router.push({ name: 'plan-detail', params: { jobId: r.job_id } })
  } catch (e) { toast(e.message, 'err') } finally { rpBusy.value = false }
}

function copyShare() {
  const url = `${location.origin}${location.pathname}#/s/${jobId}`
  navigator.clipboard?.writeText(url)
    .then(() => toast('分享链接已复制', 'ok'))
    .catch(() => toast(url))
}

function auditCls(a) {
  const ev = (a.event || a.action || a.type || '') + ''
  if (ev.includes('safety') || ev.includes('block')) return 'tag-red'
  if (ev.includes('approval') || ev.includes('wait')) return 'tag-amber'
  if (ev.includes('complete')) return 'tag-green'
  return 'tag-blue'
}
</script>

<style scoped>
.detail { padding-top: 28px; }
.head-card { padding: 24px 28px; }
.head-main { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.head-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.dest { font-size: 22px; font-weight: 900; letter-spacing: -.02em; }
.route { font-size: 13.5px; color: var(--ink-500); }
.head-meta { font-size: 13.5px; color: var(--ink-500); margin-top: 6px; }
.head-actions { display: flex; gap: 9px; flex-wrap: wrap; }

.sp-search { display: flex; gap: 8px; }
.sp-search .input { flex: 1; }
.sp-note { font-size: 12px; color: var(--ink-400); margin: 8px 0 10px; }
.sp-results { display: flex; flex-direction: column; gap: 7px; max-height: 320px; overflow-y: auto; }
.sp-row { display: grid; grid-template-columns: 30px 1fr auto; gap: 8px; align-items: center; border: 1px solid var(--ink-100); border-radius: 11px; padding: 9px 12px; cursor: pointer; }
.sp-row:hover { border-color: var(--brand-500); background: var(--brand-50); }
.sp-emoji { font-size: 19px; text-align: center; }
.sp-body b { display: block; font-size: 13.5px; }
.sp-body em { font-style: normal; font-size: 11.5px; color: var(--ink-400); }
.sp-none { text-align: center; color: var(--ink-400); font-size: 12.5px; padding: 18px 0; }

/* 评分弹窗（需求2） */
.rate-stars { display: flex; align-items: center; gap: 6px; }
.star { border: none; background: none; font-size: 34px; cursor: pointer; color: var(--ink-200); transition: transform .12s, color .12s; padding: 0 2px; }
.star:hover { transform: scale(1.15); }
.star.on { color: #F59E0B; }
.rate-num { margin-left: 8px; font-size: 15px; color: var(--ink-700); }
.rate-good {
  margin-top: 14px; padding: 12px 14px; background: #ECFDF5; border: 1px solid #10B981;
  border-radius: 10px; font-size: 13px; color: #065F46; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.prog-meta { font-size: 12.5px; color: var(--ink-400); margin-top: 8px; }
.prog-meta .err { color: var(--danger); }

.wait-card {
  margin-top: 14px; padding: 18px 24px; display: flex; align-items: center; gap: 16px;
  background: var(--warn-bg); border-color: #FDE68A; flex-wrap: wrap;
}
.wait-icon { font-size: 30px; }
.wait-card b { color: #92400E; font-size: 15px; }
.wait-card p { font-size: 13px; color: #A16207; margin-top: 3px; }

.tab-body { padding: 26px 30px; }
.book-tools { display: flex; justify-content: flex-end; margin-bottom: 6px; }
.sha { font-family: var(--mono); font-size: 11.5px; color: var(--ink-400); }

.audit-list { display: flex; flex-direction: column; gap: 8px; max-height: 420px; overflow-y: auto; }
.audit-item { display: flex; align-items: center; gap: 10px; font-size: 13px; padding: 9px 13px; background: var(--ink-50); border-radius: var(--r-sm); }
.au-time { font-family: var(--mono); font-size: 11.5px; color: var(--ink-400); flex: none; }
.au-detail { color: var(--ink-700); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.diff-view { border: 1.5px solid var(--ink-100); border-radius: var(--r-md); overflow: hidden; font-family: var(--mono); font-size: 12.5px; max-height: 560px; overflow-y: auto; }
.dl { display: flex; padding: 2px 0; line-height: 1.75; }
.dl-sign { width: 30px; text-align: center; flex: none; color: var(--ink-400); user-select: none; }
.dl.add { background: #ECFDF5; } .dl.add .dl-sign { color: var(--ok); font-weight: 700; }
.dl.del { background: #FEF2F2; } .dl.del .dl-sign { color: var(--danger); font-weight: 700; }
.dl-text { white-space: pre-wrap; word-break: break-all; padding-right: 12px; }

.swap-preview { background: var(--ink-50); border: 1px dashed var(--brand); border-radius: 10px; padding: 12px 14px; }
.sp-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.sp-tag { font-size: 11px; padding: 2px 8px; background: var(--brand); color: #fff; border-radius: 5px; font-weight: 700; }
.sp-row b { font-size: 15px; }
.sp-cat { font-size: 11px; padding: 2px 8px; background: rgba(99,102,241,.1); color: #6366F1; border-radius: 5px; }
.sp-fields { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 12px; color: var(--ink-500); }
.sp-fields span { background: #fff; padding: 2px 8px; border-radius: 5px; border: 1px solid var(--ink-100); }
.swap-diff { background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 9px; padding: 10px 14px; margin-top: 14px; }
.swap-diff b { color: var(--ok); font-size: 13px; display: block; margin-bottom: 6px; }
.diff-row { display: flex; justify-content: space-between; font-size: 12.5px; padding: 2px 0; }
.diff-row span { color: var(--ink-500); }
.diff-row b { color: var(--ink-900); font-weight: 700; display: inline; }
.diff-warn { font-size: 11.5px; color: var(--warn); margin-top: 6px; padding-top: 6px; border-top: 1px dashed #A7F3D0; }
</style>
