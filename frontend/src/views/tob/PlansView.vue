<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TobIcon from '../../components/TobIcon.vue'
import { plansApi } from '../../api/index.js'

const router = useRouter()
const f = ref({ status: '', customer: '' })

const STATUSES = ['COMPLETED', 'RUNNING', 'WAITING_BUDGET', 'WAITING_SAFETY', 'FAILED']
const STATUS_META = {
  COMPLETED: { label: '已完成', cls: 'tag-ok' },
  RUNNING: { label: '运行中', cls: 'tag-info' },
  WAITING_BUDGET: { label: '预算挂起', cls: 'tag-warn' },
  WAITING_SAFETY: { label: '安全挂起', cls: 'tag-danger' },
  FAILED: { label: '失败', cls: 'tag-danger' },
}

/* —— 任务列表：GET /api/plans（staff 口径，AUTH_ENABLED 时需工作台登录；失败回退演示数据） —— */
const FALLBACK = [
  { job: 'plan_a3f8d2', dest: '苏州', origin: '上海', customer: '远山国旅', status: 'RUNNING', version: 3, progress: 62, updated: '2026-09-09 14:20' },
  { job: 'plan_9c1e77', dest: '大理', origin: '成都', customer: '云途旅行', status: 'WAITING_BUDGET', version: 2, progress: 45, updated: '2026-09-09 13:48' },
  { job: 'plan_5b2a10', dest: '杭州', origin: '', customer: '（散客 toC）', status: 'COMPLETED', version: 4, progress: 100, updated: '2026-09-09 11:32' },
]
const items = ref(FALLBACK)

function statusGroup(s) {
  if (s === 'WAITING_BUDGET_APPROVAL') return 'WAITING_BUDGET'
  if (s === 'WAITING_SAFETY_REVIEW') return 'WAITING_SAFETY'
  return s
}
function toRow(j) {
  return {
    job: j.job_id,
    dest: j.destination || '—',
    origin: j.origin || '',
    customer: j.customer || (j.user_id ? `散客 ${j.user_id}` : '（散客 toC）'),
    status: statusGroup(j.status) in STATUS_META ? statusGroup(j.status) : 'RUNNING',
    version: j.version || 1,
    progress: j.progress || 0,
    updated: (j.updated_at || j.created_at || '').replace('T', ' ').slice(0, 16),
  }
}

async function load() {
  try {
    const res = await plansApi.list({ limit: 100 })
    const arr = (res && res.items) || []
    if (arr.length) items.value = arr.map(toRow)
  } catch { /* 未登录/网络异常：回退演示数据 */ }
}
onMounted(load)

const rows = computed(() => items.value.filter(it =>
  (!f.value.status || it.status === f.value.status) &&
  (!f.value.customer || it.customer.includes(f.value.customer))
))
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">任务中枢</div>
        <h1 class="page-title">方案列表</h1>
        <p class="page-desc">全部行程任务 · 点击行打开详情抽屉(审批 / 重规划 / 干预 / diff)</p>
      </div>
      <div class="page-actions">
        <select v-model="f.status" class="select-slim" style="width:160px">
          <option value="">全部状态</option>
          <option v-for="s in STATUSES" :key="s" :value="s">{{ STATUS_META[s].label }}</option>
        </select>
        <div class="search-box" style="flex:0 1 180px; min-width:150px">
          <span class="s-ico"><TobIcon name="search" :size="15" /></span>
          <input v-model.trim="f.customer" placeholder="客户筛选" />
        </div>
        <button class="btn btn-primary btn-sm" @click="load">查询</button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>任务</th>
            <th>目的地</th>
            <th>客户</th>
            <th>状态</th>
            <th>版本</th>
            <th style="min-width:130px">进度</th>
            <th>更新时间</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in rows" :key="it.job" class="clickable-row" @click="router.push(`/plan/${it.job}`)">
            <td><span class="mono-xs" style="color:var(--text-2)">{{ it.job }}</span></td>
            <td>
              <b style="font-weight:var(--fw-medium)">{{ it.dest }}</b>
              <span v-if="it.origin" class="cell-sub" style="display:inline"> · {{ it.origin }}出发</span>
            </td>
            <td style="color:var(--text-2)">{{ it.customer }}</td>
            <td><span class="tag" :class="STATUS_META[it.status].cls">{{ STATUS_META[it.status].label }}</span></td>
            <td><span class="tag">v{{ it.version }}</span></td>
            <td>
              <div class="row gap-2" style="display:flex;align-items:center;gap:var(--s-3)">
                <div class="progress" style="width:80px"><span :style="{ width: it.progress + '%' }" /></div>
                <span class="mono-xs">{{ it.progress }}%</span>
              </div>
            </td>
            <td><span class="mono-xs">{{ it.updated }}</span></td>
            <td style="color:var(--text-faint)"><TobIcon name="chevron" :size="14" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.clickable-row { cursor: pointer; }
.progress > span { background: linear-gradient(90deg, #7E97B0, #A9BCCB); }
</style>
