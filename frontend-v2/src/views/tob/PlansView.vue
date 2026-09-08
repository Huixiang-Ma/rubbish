<template>
  <div>
    <div class="page-head">
      <div>
        <h1>方案列表</h1>
        <div class="desc" style="color:var(--text-faint)">全部行程任务 · 点击行打开详情抽屉（审批 / 重规划 / 干预 / diff）</div>
      </div>
      <div style="display:flex;gap:10px;align-items:flex-end">
        <select v-model="filter.status" class="select" style="width:170px" @change="load">
          <option value="">全部状态</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
        </select>
        <input v-model.trim="filter.customer" class="input" style="width:160px" placeholder="客户筛选" @keyup.enter="load" />
        <button class="btn btn-primary btn-sm" @click="load">查询</button>
      </div>
    </div>

    <div class="card" style="overflow:hidden">
      <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
      <div v-else-if="!items.length" class="empty"><div class="icon">🗂</div><p>没有符合条件的任务</p></div>
      <table v-else class="table">
        <thead>
          <tr>
            <th>任务</th><th>目的地</th><th>客户</th><th>状态</th><th>版本</th><th>进度</th><th>更新时间</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.job_id" class="clickable" @click="open(it)">
            <td style="font-family:var(--mono);font-size:12px;color:var(--text-faint)">{{ it.job_id }}</td>
            <td><b>{{ it.destination }}</b><span v-if="it.origin" style="color:var(--text-faint);font-size:12px"> · {{ it.origin }}</span></td>
            <td>{{ it.customer || '—' }}</td>
            <td><StatusTag :status="it.status" /></td>
            <td><span class="tag tag-gray">v{{ it.version }}</span></td>
            <td style="min-width:110px">
              <div class="progress" style="height:6px"><div :style="{ width: (it.progress ?? 0) + '%' }"></div></div>
            </td>
            <td style="font-family:var(--mono);font-size:12px;color:var(--text-faint)">{{ (it.updated_at || '').replace('T', ' ').slice(0, 16) }}</td>
            <td style="color:var(--text-faint)">›</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 详情抽屉 -->
    <AppDrawer v-if="cur" :title="`任务详情 · ${cur.job_id}`" @close="cur = null">
      <div class="d-head-info">
        <StatusTag :status="detail?.status || cur.status" />
        <span class="d-dest">{{ cur.destination }}</span>
        <span class="d-meta">{{ cur.days }} 天 · ¥{{ Number(cur.budget || 0).toLocaleString() }}{{ cur.origin ? ` · ${cur.origin}出发` : '' }}</span>
      </div>

      <div v-if="detailLoading" class="loading-block"><div class="spinner spin"></div></div>
      <template v-else-if="detail">
        <div class="d-sec">
          <div class="d-sec-title">管线状态</div>
          <div class="steps">
            <div v-for="a in FLOW" :key="a" class="step"
                 :class="{ done: doneSet.has(a), doing: detail.current_agent === a }">
              <div class="node">{{ doneSet.has(a) ? '✓' : '●' }}</div>
              <div class="label">{{ a }}</div>
            </div>
          </div>
          <div v-if="detail.error" class="d-err">⚠ {{ detail.error }}</div>
        </div>

        <div class="d-sec">
          <div class="d-sec-title">HITL 审批</div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <input v-model.trim="ap.operator" class="input" style="width:130px" placeholder="操作人" />
            <input v-model.trim="ap.reason" class="input" style="flex:1" placeholder="审批意见" />
            <button class="btn btn-ok btn-sm" :disabled="approving" @click="approve('approve')">放行</button>
            <button class="btn btn-danger btn-sm" :disabled="approving" @click="approve('reject')">拒绝</button>
          </div>
          <p class="d-hint">仅 WAITING_* 挂起态可审批；base_version={{ detail.version }}（乐观锁）</p>
        </div>

        <div class="d-sec">
          <div class="d-sec-title">运行态强干预 <span class="d-hint">（热替换 user_input，下一节点边界生效）</span></div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <select v-model="iv.field" class="select" style="width:150px">
              <option v-for="f in ['constraints', 'preferences', 'budget', 'mood']" :key="f" :value="f">{{ f }}</option>
            </select>
            <input v-model.trim="iv.new_value" class="input" style="flex:1" placeholder="新值（多个用逗号分隔）" />
            <select v-model="iv.mode" class="select" style="width:100px">
              <option value="append">追加</option><option value="remove">移除</option>
            </select>
            <button class="btn btn-soft btn-sm" :disabled="intervening" @click="intervene">执行干预</button>
          </div>
          <div v-if="ivList.length" class="iv-list">
            <div v-for="(x, i) in ivList" :key="i" class="iv-item">
              <span class="tag tag-purple">{{ x.field }}</span>
              <span class="iv-val">{{ short(x.old_value) }} → <b>{{ short(x.new_value) }}</b></span>
              <span class="iv-meta">{{ x.operator }} · {{ (x.created_at || '').slice(0, 16) }}</span>
            </div>
          </div>
        </div>

        <div class="d-sec">
          <div class="d-sec-title">任务记忆（多轮沉淀三元组）</div>
          <div v-if="!memory.length" class="d-hint">暂无记忆条目</div>
          <div v-else class="tri-list">
            <div v-for="(t, i) in memory" :key="i" class="tri">
              <b>{{ t.head }}</b><span>—{{ t.relation }}→</span><b>{{ t.tail }}</b>
              <em v-if="t.tail_type" class="tag tag-gray">{{ t.tail_type }}</em>
            </div>
          </div>
        </div>

        <div class="d-sec">
          <div class="d-sec-title">操作</div>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <button class="btn btn-ghost btn-sm" @click="loadDetail(true); showDiff = !showDiff">🔀 {{ showDiff ? '收起' : '查看' }}版本 Diff</button>
            <button class="btn btn-ghost btn-sm" @click="gotoPlan">在游客端打开行程书 ↗</button>
          </div>
          <div v-if="showDiff && diff" class="diff-view">
            <div v-for="(l, i) in diff.lines.slice(0, 400)" :key="i" class="dl" :class="l.type">
              <span class="dl-sign">{{ l.type === 'add' ? '+' : l.type === 'del' ? '−' : ' ' }}</span>
              <span>{{ l.text }}</span>
            </div>
          </div>
        </div>
      </template>
    </AppDrawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { plansApi } from '../../api'
import { toast } from '../../composables/toast'
import StatusTag from '../../components/StatusTag.vue'
import AppDrawer from '../../components/AppDrawer.vue'

const router = useRouter()
const STATUSES = ['QUEUED', 'RUNNING', 'COMPLETED', 'WAITING_SAFETY_REVIEW', 'WAITING_BUDGET_APPROVAL', 'FAILED']
const FLOW = ['Intake', 'Researcher', 'Planner', 'Itinerary', 'Budget', 'Validator', 'Sentiment', 'Debate', 'Mood', 'Reporter']

const items = ref([])
const loading = ref(true)
const filter = reactive({ status: '', customer: '' })

const cur = ref(null)
const detail = ref(null)
const detailLoading = ref(false)
const memory = ref([])
const ivList = ref([])
const diff = ref(null)
const showDiff = ref(false)

const ap = reactive({ operator: 'admin', reason: '' })
const approving = ref(false)
const iv = reactive({ field: 'constraints', new_value: '', mode: 'append' })
const intervening = ref(false)

const doneSet = computed(() => new Set(detail.value?.completed_nodes || []))

async function load() {
  loading.value = true
  try {
    const r = await plansApi.list({ status: filter.status || undefined, customer: filter.customer || undefined, limit: 200 })
    items.value = r.items || []
  } catch (e) { toast(e.message, 'err') } finally { loading.value = false }
}
load()

async function open(it) {
  cur.value = it
  detail.value = null
  memory.value = []
  ivList.value = []
  diff.value = null
  showDiff.value = false
  await loadDetail()
  try { memory.value = (await plansApi.memory(it.job_id)).triples || [] } catch {}
  try { ivList.value = (await plansApi.interventions(it.job_id)).items || [] } catch {}
}

async function loadDetail(withDiff) {
  detailLoading.value = true
  try {
    detail.value = await plansApi.status(cur.value.job_id)
    if (withDiff && !diff.value) {
      try { diff.value = await plansApi.diff(cur.value.job_id) }
      catch (e) { toast(e.message) }
    }
  } catch (e) { toast(e.message, 'err') } finally { detailLoading.value = false }
}

async function approve(decision) {
  approving.value = true
  try {
    await plansApi.approval(cur.value.job_id, {
      decision, operator: ap.operator || 'admin', reason: ap.reason || (decision === 'approve' ? '放行' : '拒绝'),
      base_version: detail.value.version,
    })
    toast(decision === 'approve' ? '已放行' : '已拒绝', 'ok')
    await loadDetail()
    load()
  } catch (e) { toast(e.message, 'err') } finally { approving.value = false }
}

async function intervene() {
  if (!iv.new_value) return
  intervening.value = true
  let value = iv.new_value
  if (iv.field === 'budget') value = Number(value)
  else if (iv.mode === 'append' || iv.mode === 'remove') value = value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
  try {
    await plansApi.intervene(cur.value.job_id, {
      field: iv.field, new_value: value, mode: iv.mode,
      operator: ap.operator || 'admin', reason: '工作台干预', base_version: detail.value.version,
    })
    toast('干预已落盘', 'ok')
    iv.new_value = ''
    await loadDetail()
    ivList.value = (await plansApi.interventions(cur.value.job_id)).items || []
  } catch (e) { toast(e.message, 'err') } finally { intervening.value = false }
}

function gotoPlan() {
  router.push({ name: 'plan-detail', params: { jobId: cur.value.job_id } })
}
function short(v) {
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')
  return s.length > 24 ? s.slice(0, 24) + '…' : s
}
</script>

<style scoped>
.d-head-info { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.d-dest { font-size: 19px; font-weight: 800; }
.d-meta { font-size: 13px; color: var(--text-dim); }
.d-sec { margin-bottom: 26px; }
.d-sec-title { font-weight: 700; font-size: 14.5px; margin-bottom: 12px; display: flex; gap: 8px; align-items: baseline; }
.d-err { margin-top: 10px; background: rgba(248,113,113,.12); color: var(--danger); border-radius: var(--r-sm); padding: 10px 14px; font-size: 13px; }
.d-hint { font-size: 12px; color: var(--text-faint); font-weight: 400; margin-top: 6px; }
.iv-list { margin-top: 12px; display: flex; flex-direction: column; gap: 7px; }
.iv-item { display: flex; align-items: center; gap: 10px; font-size: 12.5px; background: var(--bg-raised); padding: 8px 13px; border-radius: var(--r-sm); }
.iv-val { color: var(--text-dim); flex: 1; }
.iv-val b { color: var(--text); }
.iv-meta { color: var(--text-faint); font-size: 11.5px; }
.tri-list { display: flex; flex-direction: column; gap: 6px; }
.tri { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-dim); background: var(--bg-raised); padding: 8px 13px; border-radius: var(--r-sm); }
.tri b { color: var(--text); }
.diff-view { margin-top: 12px; border: 1px solid var(--line); border-radius: var(--r-sm); overflow-y: auto; max-height: 320px; font-family: var(--mono); font-size: 12px; }
.dl { display: flex; padding: 1px 0; }
.dl-sign { width: 26px; text-align: center; color: var(--text-faint); flex: none; }
.dl.add { background: rgba(52,211,153,.1); } .dl.add .dl-sign { color: var(--ok); }
.dl.del { background: rgba(248,113,113,.1); } .dl.del .dl-sign { color: var(--danger); }
</style>
