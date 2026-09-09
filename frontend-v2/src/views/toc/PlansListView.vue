<template>
  <div class="container list-page">
    <div class="page-head">
      <div>
        <div class="sec-title">我的行程</div>
        <p class="sec-desc">上：用标品模板编排的行程书，可随时打开、编辑、删除；下：AI 智能体流水线生成的任务。</p>
      </div>
      <button class="btn btn-primary" @click="showPicker = true">✦ 新建规划</button>
    </div>

    <!-- 概要条 -->
    <div v-if="!loading && (tripList.length || items.length)" class="stats card card-pad">
      <div class="stat"><b>{{ tripList.length }}</b><span>本地行程书</span></div>
      <div class="stat"><b>{{ totalStops }}</b><span>编排停留点</span></div>
      <div class="stat"><b>{{ aiCount }}</b><span>AI 任务</span></div>
      <div class="stat stat-done"><b>{{ doneCount }}</b><span>已完成行程书</span></div>
    </div>

    <!-- 全空引导 -->
    <div v-if="!loading && !tripList.length && !items.length" class="empty card">
      <div class="icon">🧳</div>
      <p>还没有任何行程。两种玩法任选：</p>
      <div class="empty-acts">
        <button class="btn btn-primary" @click="showPicker = true">✦ 用标品模板编排行程</button>
        <router-link :to="{ name: 'home' }" class="btn btn-ghost">🤖 让 AI 智能体生成行程书</router-link>
      </div>
    </div>

    <!-- 本地编排的行程书 -->
    <div v-if="tripList.length" class="sub-sec">
      <div class="sub-title">🧩 我编排的行程书
        <span class="sub-count">{{ tripList.length }}</span>
        <span class="sub-hint">基于标品库 · 本地保存</span>
        <button class="btn btn-primary btn-sm" style="margin-left:auto" @click="showPicker = true">✦ 新建规划</button>
      </div>
      <div class="plans local-plans">
        <div v-for="t in tripList" :key="t.id" class="card plan-card local-card card-hover"
             @click="$router.push({ name: 'trip-detail', params: { id: t.id } })">
          <div class="lp-top">
            <span class="lp-cover" :style="{ background: (t.cover && t.cover.gradient) || 'linear-gradient(135deg,#60A5FA,#8B5CF6)' }">{{ (t.cover && t.cover.emoji) || '🧩' }}</span>
            <div class="lp-meta">
              <div class="p-dest">{{ t.title || '未命名行程' }}</div>
              <div class="p-meta">{{ t.city || '未定城市' }} · {{ t.days }} 天 · {{ stopCount(t) }} 个停留</div>
            </div>
          </div>
          <div class="lp-sub">
            <span v-if="dateRange(t)" class="lp-line">📅 {{ dateRange(t) }}</span>
            <span v-if="budgetText(t)" class="lp-line">💰 {{ budgetText(t) }}</span>
            <span v-if="t.travelers" class="lp-line">👥 {{ t.travelers }} 人</span>
          </div>
          <div class="p-foot">
            <div class="foot-left">
              <span class="lp-tag">本地编排</span>
              <span v-if="t.template_id" class="lp-tag tag-gray">模板</span>
            </div>
            <div class="foot-right">
              <span class="p-date">{{ (t.updated_at || '').replace('T', ' ').slice(0, 16) }}</span>
              <button v-if="!isDeleting(t.id)" class="del-btn" title="删除行程" @click.stop="askDelete(t)">删除</button>
              <span v-else class="del-confirm">
                <button class="btn btn-danger btn-xs" @click.stop="confirmDelete(t.id)">确认删除</button>
                <button class="btn btn-ghost btn-xs" @click.stop="cancelDelete">取消</button>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 智能体生成任务 -->
    <div class="sub-sec">
      <div class="sub-title">🤖 AI 智能体生成的任务
        <span class="sub-count">{{ items.length }}</span>
        <span class="sub-hint">10 Agent 协作 · 云端生成</span>
      </div>
      <div class="filters card card-pad" style="margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
        <div class="field" style="min-width:160px">
          <label>状态</label>
          <select v-model="filter.status" class="select" @change="load">
            <option value="">全部</option>
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <div class="field" style="min-width:160px">
          <label>客户（toB 归属）</label>
          <input v-model.trim="filter.customer" class="input" placeholder="留空查全部" @keyup.enter="load" />
        </div>
        <button class="btn btn-primary" @click="load">查询</button>
      </div>

      <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
      <div v-else-if="!items.length" class="empty card"><div class="icon">🧳</div><p>还没有智能体生成的任务，去首页让 10 个智能体吵出一趟旅程吧</p>
        <router-link :to="{ name: 'home' }" class="btn btn-primary btn-sm" style="margin-top:14px">✦ 生成我的行程书</router-link>
      </div>

      <div v-else class="plans">
        <div v-for="it in items" :key="it.job_id" class="card plan-card card-hover" @click="$router.push({ name: 'plan-detail', params: { jobId: it.job_id } })">
          <div class="p-top">
            <StatusTag :status="it.status" />
            <span v-if="it.version != null" class="tag tag-gray">v{{ it.version }}</span>
            <span class="p-date">{{ (it.created_at || '').replace('T', ' ').slice(0, 16) }}</span>
          </div>
          <div class="p-dest">{{ it.destination }}<span v-if="it.origin" class="p-origin"> · {{ it.origin }}出发</span></div>
          <div class="p-meta">{{ it.days }} 天 · ¥{{ Number(it.budget || 0).toLocaleString() }}<span v-if="it.customer"> · {{ it.customer }}</span></div>
          <div class="p-foot">
            <span class="p-id">{{ it.job_id }}</span>
            <button class="promote-btn" disabled
                    title="转正功能本轮未开放，数据模型 status='job' 字段已就位（下轮启用）"
                    @click.stop="onPromoteStub(it)">⇆ 转为行程书</button>
            <span class="p-go">查看行程书 →</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 选模板弹层：右上"新建规划"按钮 或 URL ?new=1 触发 -->
  <TemplatePickerSheet
    v-if="showPicker"
    :seed="seedProduct"
    @picked="onPicked"
    @close="showPicker = false"
  />
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { plansApi, productsApi } from '../../api'
import {
  useTripStore, tripList,
  tripDateRange, tripBudgetText, tripStopCount,
} from '../../composables/tripStore'
import StatusTag from '../../components/StatusTag.vue'
import TemplatePickerSheet from '../../components/TemplatePickerSheet.vue'
import { toast } from '../../composables/toast'

const route = useRoute()
const router = useRouter()

const STATUSES = ['QUEUED', 'RUNNING', 'COMPLETED', 'WAITING_SAFETY_REVIEW', 'WAITING_BUDGET_APPROVAL', 'FAILED']

const items = ref([])
const loading = ref(true)
const filter = reactive({ status: '', customer: '' })
const showPicker = ref(false)
const seedProduct = ref(null)  // 来自 ?seed= 深链的预置商品
const seedId = ref('')          // 持久保留直到选完模板

// —— 本地行程库：绑定响应式单例，删除/保存后即时刷新 ----------------------
const store = useTripStore()
const dateRange = tripDateRange
const budgetText = tripBudgetText
const stopCount = tripStopCount

const deletingId = ref('')
function isDeleting(id) { return deletingId.value === id }
function askDelete(t) { deletingId.value = t.id }
function cancelDelete() { deletingId.value = '' }
function confirmDelete(id) {
  store.remove(id)
  deletingId.value = ''
}

const totalStops = computed(() => tripList.value.reduce((s, t) => s + tripStopCount(t), 0))
const aiCount = computed(() => items.value.length)
const doneCount = computed(() => tripList.value.length + items.value.filter(i => i.status === 'COMPLETED').length)

// —— AI 任务列表 ----------------------------------------------------------
async function load() {
  loading.value = true
  try {
    const r = await plansApi.list({ status: filter.status || undefined, customer: filter.customer || undefined, limit: 100 })
    items.value = r.items || []
  } catch { items.value = [] } finally { loading.value = false }
}

let off
async function fetchSeedProduct(id) {
  try {
    const r = await productsApi.detail(id)
    return r || null
  } catch { return null }
}

onMounted(async () => {
  off = store.subscribe(() => { deletingId.value = '' })
  load()
  // /plans?new=1 自动打开选模板弹层；?seed= 同时预置商品（来自标品详情"用它排行程"）
  if (route.query.new) {
    seedId.value = String(route.query.seed || '')
    if (seedId.value) {
      const p = await fetchSeedProduct(seedId.value)
      seedProduct.value = p
      if (!p) toast('未找到预置商品，仍可选模板继续', 'info')
    }
    showPicker.value = true
    router.replace({ name: 'my-plans' })
  }
})
onBeforeUnmount(() => { if (off) off() })

// 选中模板后跳到编辑页：用一个临时 id 标识"新建中"，seed 一并带上
function onPicked(template) {
  showPicker.value = false
  const query = { template: template.id }
  if (seedId.value) query.seed = seedId.value
  router.push({
    name: 'trip-edit',
    params: { id: '_new' },
    query,
  })
  seedProduct.value = null
  seedId.value = ''
}

// 转正按钮：当前 disabled 埋点；下轮接入 /api/trips/{id}/promote
function onPromoteStub(item) {
  toast(`转正功能下轮开放：${item.destination} 任务的 status='job' 字段已就位`, 'info')
}
</script>

<style scoped>
.list-page { padding-top: 32px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.page-head .sec-title { margin-bottom: 0; }
.page-head .btn { margin-bottom: 2px; }

.stats { display: flex; gap: 8px; margin: 18px 0 24px; padding: 14px 18px; flex-wrap: wrap; }
.stat { display: flex; align-items: baseline; gap: 8px; padding: 2px 18px 2px 0; border-right: 1px solid var(--ink-150, var(--ink-200)); }
.stat:last-child { border-right: none; }
.stat b { font-size: 22px; font-weight: 900; color: var(--brand-600); font-family: var(--mono); }
.stat-done b { color: var(--teal-600, #0D9488); }
.stat span { font-size: 12.5px; color: var(--ink-500); }

.plans { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
.plan-card { padding: 20px 22px; cursor: pointer; }
.p-top { display: flex; align-items: center; gap: 8px; }
.p-date { margin-left: auto; font-size: 12px; color: var(--ink-400); font-family: var(--mono); }
.p-dest { font-size: 19px; font-weight: 900; margin-top: 12px; letter-spacing: -.01em; }
.p-origin { font-size: 13px; color: var(--ink-400); font-weight: 500; }
.p-meta { font-size: 13px; color: var(--ink-500); margin-top: 5px; }
.p-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 13px; border-top: 1px dashed var(--ink-200); }
.foot-left, .foot-right { display: flex; align-items: center; gap: 8px; }
.p-id { font-family: var(--mono); font-size: 11.5px; color: var(--ink-400); }
.p-go { font-size: 13px; font-weight: 700; color: var(--brand-600); }
.promote-btn { font-size: 12px; padding: 4px 10px; border-radius: 6px; border: 1px dashed var(--ink-300); background: transparent; color: var(--ink-400); cursor: not-allowed; font-weight: 600; }
.promote-btn:hover { color: var(--ink-500); }

.sub-sec { margin-bottom: 26px; }
.sub-title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 800; color: var(--ink-900); margin-bottom: 12px; }
.sub-count { background: var(--brand-50); color: var(--brand-700); font-size: 11px; font-weight: 800; padding: 2px 8px; border-radius: 999px; }
.sub-hint { font-size: 12px; font-weight: 500; color: var(--ink-400); }

.empty-acts { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.btn-ghost { background: transparent; border: 1px solid var(--ink-300); color: var(--ink-700); }
.btn-ghost:hover { border-color: var(--brand-500); color: var(--brand-600); }

/* 本地行程卡 */
.local-card { padding: 16px 18px; display: flex; flex-direction: column; }
.local-card .p-dest { margin-top: 0; }
.lp-top { display: flex; align-items: center; gap: 14px; }
.lp-cover { width: 58px; height: 58px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 30px; box-shadow: var(--shadow-sm); flex: none; }
.lp-meta { min-width: 0; }
.lp-meta .p-dest { font-size: 16px; line-height: 1.35; }
.lp-tag { font-size: 11px; color: var(--brand-700); background: var(--brand-50); border: 1px solid var(--brand-200); padding: 2px 9px; border-radius: 999px; font-weight: 700; white-space: nowrap; }
.tag-gray { color: var(--ink-500); background: var(--ink-100); border-color: var(--ink-200); }
.lp-meta .p-meta { margin-top: 4px; }
.local-card .p-foot { margin-top: 12px; padding-top: 11px; }

.lp-sub { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px; }
.lp-line { font-size: 12.5px; color: var(--ink-600); font-weight: 600; }
.del-btn { font-size: 12px; color: var(--ink-400); background: none; border: none; cursor: pointer; padding: 2px 4px; }
.del-btn:hover { color: #E11D48; text-decoration: underline; }
.del-confirm { display: flex; gap: 6px; align-items: center; }
.btn-xs { font-size: 12px; padding: 3px 10px; }
.btn-danger { background: #E11D48; border-color: #E11D48; color: #fff; }
.btn-danger:hover { background: #BE123C; }
</style>
