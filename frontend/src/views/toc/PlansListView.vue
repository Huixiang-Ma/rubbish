<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { TRIPS, PLAN_JOBS, catMeta } from './mock.js'
import { plansApi } from '../../api/index.js'
import { tripsStore } from '../../stores/trips.js'

const statusFilter = ref('all')
const custFilter = ref('')

/* —— 本地行程书（localStorage 仓 + mock 兜底） —— */
tripsStore.load()
const localTrips = ref([...tripsStore.items])
const TRIPS_LIST = computed(() => localTrips.value.length ? localTrips.value : TRIPS)

const stats = computed(() => ({
  trips: TRIPS_LIST.value.length,
  stops: TRIPS_LIST.value.reduce((s, t) => s + (t.stops || t.dayPlans.reduce((n, d) => n + d.items.length, 0)), 0),
  jobs: JOB_LIST.value.length,
  done: JOB_LIST.value.filter(j => j.status === 'COMPLETED').length,
}))

/* —— AI 规划任务（GET /api/plans/mine，未登录回退演示数据） —— */
const STATUS = {
  all:   { label: '全部' },
  COMPLETED: { label: '已完成', cls: 'st-ok' },
  RUNNING:   { label: '规划中', cls: 'st-run' },
  WAITING:   { label: '审批中', cls: 'st-run' },
  QUEUED:    { label: '排队中', cls: 'st-wait' },
  PENDING:   { label: '排队中', cls: 'st-wait' },
  FAILED:    { label: '失败', cls: 'st-wait' },
}
const JOB_FALLBACK = PLAN_JOBS.map(j => ({
  id: j.id, status: j.status.toUpperCase(), version: j.version, dest: j.dest, origin: j.origin,
  days: j.days, budget: j.budget, people: j.people, customer: j.customer,
  created: j.created, currentAgent: j.currentAgent, progress: j.progress, tripId: j.tripId, parent: j.parent,
}))
const JOB_LIST = ref(JOB_FALLBACK)

function statusGroup(s) {
  if (['WAITING_BUDGET_APPROVAL', 'WAITING_SAFETY_REVIEW'].includes(s)) return 'WAITING'
  return STATUS[s] ? s : 'PENDING'
}

onMounted(async () => {
  try {
    const res = await plansApi.mine()
    const rows = (res && res.items) || []
    if (rows.length) {
      JOB_LIST.value = rows.map(j => ({
        id: j.job_id,
        status: statusGroup(j.status),
        version: `v${j.version || 1}`,
        dest: j.destination || '—',
        origin: j.origin || '—',
        days: j.days || 0,
        budget: j.budget || 0,
        people: j.travelers || 2,
        customer: j.customer || '',
        created: (j.updated_at || j.created_at || '').replace('T', ' ').slice(0, 16),
        currentAgent: j.current_node || '',
        progress: j.progress || 0,
        tripId: null,
        parent: null,
      }))
    }
  } catch { /* 未登录/网络异常：回退演示任务 */ }
})

const jobs = computed(() => JOB_LIST.value.filter(j =>
  (statusFilter.value === 'all' || j.status === statusFilter.value) &&
  (!custFilter.value || j.customer === custFilter.value)
))

const custs = [...new Set(JOB_LIST.value.map(j => j.customer).filter(Boolean))]
const delTarget = ref(null)
function doDelete() {
  if (delTarget.value) {
    tripsStore.remove(delTarget.value.id)
    localTrips.value = [...tripsStore.items]
  }
  delTarget.value = null
}
</script>

<template>
  <div class="plans-list">
    <div class="container-wide">

      <header class="page-head">
        <div>
          <span class="eyebrow">AI 行程规划</span>
          <h1 class="page-title">我的行程</h1>
          <p class="page-sub">本地行程书与 AI 规划任务统一在此管理 · 跨设备同步</p>
        </div>
        <div class="head-actions">
          <RouterLink to="/manual" class="btn btn-ghost">手动组装行程书</RouterLink>
          <RouterLink to="/planner" class="btn btn-primary">新建 AI 规划</RouterLink>
        </div>
      </header>

      <!-- 统计条 -->
      <section class="stat-row">
        <div class="stat"><div class="k">本地行程书</div><div class="v">{{ stats.trips }}</div></div>
        <div class="stat"><div class="k">编排停留点</div><div class="v">{{ stats.stops }}</div></div>
        <div class="stat"><div class="k">AI 任务</div><div class="v">{{ stats.jobs }}</div></div>
        <div class="stat"><div class="k">已完成</div><div class="v" style="color: var(--ok)">{{ stats.done }}</div></div>
      </section>

      <!-- 我编排的行程书 -->
      <section class="sec">
        <div class="sec-head">
          <h2 class="sec-title">我编排的行程书</h2>
          <span class="sec-sub">由手动组装器生成 / 可继续编辑</span>
        </div>
        <div class="trip-grid">
          <article v-for="t in TRIPS_LIST" :key="t.id" class="trip card card-hover">
            <RouterLink :to="`/trip/${t.id}`" class="trip-cover">
              <img :src="`/covers/c1043.jpg`" :alt="t.title" loading="lazy" />
              <span class="trip-days">{{ t.days }} 日</span>
            </RouterLink>
            <div class="trip-body">
              <div class="trip-meta">
                <span class="tag tag-accent">{{ t.theme }}</span>
                <span class="t-3 t-xs">📍 {{ t.city }} · {{ t.pace }}节奏</span>
              </div>
              <RouterLink :to="`/trip/${t.id}`" class="trip-name">{{ t.title }}</RouterLink>
              <div class="trip-info">
                <span>{{ t.date }} 出发</span>
                <span>预算 ¥{{ t.budget.toLocaleString() }}</span>
                <span>{{ t.people }} 人</span>
              </div>
              <div class="trip-cats">
                <span v-for="n in t.dayPlans.length" :key="n" class="day-dot">D{{ n }}</span>
                <span class="t-faint t-xs">共 {{ t.stops }} 个停留点</span>
              </div>
              <div class="trip-foot">
                <RouterLink :to="`/trip/${t.id}/map`" class="foot-op">查看动线</RouterLink>
                <RouterLink :to="`/trip/${t.id}/edit`" class="foot-op">编辑</RouterLink>
                <button class="foot-op danger" @click="delTarget = t">删除</button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- AI 规划任务 -->
      <section class="sec">
        <div class="sec-head">
          <h2 class="sec-title">AI 规划任务</h2>
          <div class="sec-filter">
            <select v-model="custFilter" class="select-mini">
              <option value="">全部客户画像</option>
              <option v-for="c in custs" :key="c" :value="c">{{ c }}</option>
            </select>
            <div class="tabs-mini">
              <button v-for="(s, k) in STATUS" :key="k" :class="{ on: statusFilter === k }" @click="statusFilter = k">{{ s.label }}</button>
            </div>
          </div>
        </div>

        <div class="job-list">
          <article v-for="j in jobs" :key="j.id" class="job card card-hover">
            <div class="job-top">
              <span class="pill" :class="STATUS[j.status].cls">{{ STATUS[j.status].label }}</span>
              <span class="job-ver">{{ j.version }}</span>
              <span class="mono-xs job-id">{{ j.id }}</span>
              <span class="job-time">{{ j.created }}</span>
            </div>
            <div class="job-main">
              <div class="job-route">
                <b>{{ j.origin }}</b>
                <svg class="ico" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
                <b>{{ j.dest }}</b>
                <span class="job-chips">{{ j.days }} 天 · 预算 ¥{{ j.budget.toLocaleString() }} · {{ j.people }} 人</span>
              </div>
              <div class="job-cust">画像:{{ j.customer }}</div>
              <div v-if="['RUNNING','WAITING','QUEUED','PENDING'].includes(j.status)" class="job-progress">
                <div class="progress"><span :style="{ width: j.progress + '%' }"></span></div>
                <span class="t-xs t-3">当前节点:{{ j.currentAgent }} · {{ j.progress }}%</span>
              </div>
            </div>
            <div class="job-foot">
              <RouterLink :to="`/plan/${j.id}`" class="btn btn-ghost btn-sm">查看任务详情</RouterLink>
              <RouterLink v-if="j.status === 'COMPLETED'" :to="`/trip/${j.tripId}`" class="btn btn-primary-soft btn-sm">打开行程书</RouterLink>
            </div>
          </article>
          <div v-if="!jobs.length" class="empty card">该筛选条件下暂无任务</div>
        </div>
      </section>
    </div>

    <!-- 删除确认 -->
    <div v-if="delTarget" class="modal-mask" @click.self="delTarget = null">
      <div class="modal card">
        <h3 class="modal-title">删除行程书?</h3>
        <p class="modal-desc">「{{ delTarget.title }}」将被移入回收站,30 天内可恢复。</p>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="delTarget = null">取消</button>
          <button class="btn btn-primary" @click="doDelete">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plans-list { padding: var(--s-7) 0 var(--s-9); display: flex; flex-direction: column; gap: var(--s-6); }
.container-wide { display: flex; flex-direction: column; gap: var(--s-6); }

.page-head { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--s-5); flex-wrap: wrap; }
.page-title { font-size: var(--fs-3xl); font-weight: var(--fw-bold); margin-top: var(--s-3); }
.page-sub { color: var(--text-3); margin-top: var(--s-2); font-size: var(--fs-sm); }
.head-actions { display: flex; gap: var(--s-2); }

/* 统计 */
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--s-4); }
.stat { background: var(--surface); border: 1px solid var(--border-soft); border-radius: var(--r-md); padding: var(--s-4) var(--s-5); }
.stat .k { font-size: var(--fs-xs); color: var(--text-3); font-weight: var(--fw-medium); }
.stat .v { margin-top: var(--s-2); font-size: var(--fs-xl); font-weight: var(--fw-semi); font-variant-numeric: tabular-nums; }

/* 分区 */
.sec-head { display: flex; justify-content: space-between; align-items: center; gap: var(--s-4); margin-bottom: var(--s-4); flex-wrap: wrap; }
.sec-title { font-size: var(--fs-lg); font-weight: var(--fw-semi); }
.sec-sub { font-size: var(--fs-xs); color: var(--text-faint); margin-left: var(--s-3); }
.sec-filter { display: flex; gap: var(--s-2); align-items: center; }
.select-mini { height: 32px; padding: 0 var(--s-3); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); font-size: var(--fs-sm); color: var(--text-2); }
.tabs-mini { display: inline-flex; background: var(--bg-soft); border: 1px solid var(--border-soft); border-radius: var(--r); padding: 3px; gap: 2px; }
.tabs-mini button { height: 26px; padding: 0 var(--s-3); border: none; border-radius: calc(var(--r) - 3px); background: transparent; font-size: var(--fs-xs); color: var(--text-3); font-weight: var(--fw-medium); }
.tabs-mini button.on { background: var(--surface); color: var(--text); box-shadow: var(--shadow-xs); }

/* 行程书卡 */
.trip-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--s-5); }
.trip { padding: 0; overflow: hidden; display: flex; }
.trip-cover { position: relative; width: 200px; flex: none; overflow: hidden; }
.trip-cover img { width: 100%; height: 100%; object-fit: cover; transition: transform .7s var(--ease); }
.card-hover:hover .trip-cover img { transform: scale(1.05); }
.trip-days { position: absolute; left: var(--s-3); top: var(--s-3); background: rgba(31,29,26,.55); color: #fff; font-size: var(--fs-xs); padding: 2px var(--s-3); border-radius: var(--r-pill); backdrop-filter: blur(6px); }
.trip-body { flex: 1; padding: var(--s-4) var(--s-5); display: flex; flex-direction: column; gap: var(--s-2); min-width: 0; }
.trip-meta { display: flex; align-items: center; gap: var(--s-3); }
.trip-name { font-size: var(--fs-md); font-weight: var(--fw-semi); letter-spacing: -0.005em; transition: color var(--dur-1) var(--ease); }
.trip-name:hover { color: var(--accent); }
.trip-info { display: flex; gap: var(--s-4); font-size: var(--fs-xs); color: var(--text-3); }
.trip-cats { display: flex; align-items: center; gap: var(--s-2); }
.day-dot { width: 26px; height: 20px; border-radius: var(--r-sm); background: var(--bg-soft); color: var(--text-2); font-size: 11px; font-weight: var(--fw-medium); display: inline-flex; align-items: center; justify-content: center; }
.trip-foot { margin-top: auto; padding-top: var(--s-3); border-top: 1px solid var(--border-soft); display: flex; gap: var(--s-4); }
.foot-op { border: none; background: none; padding: 0; font-size: var(--fs-xs); color: var(--text-3); transition: color var(--dur-1) var(--ease); }
.foot-op:hover { color: var(--text); }
.foot-op.danger:hover { color: var(--danger); }

/* AI 任务卡 */
.job-list { display: flex; flex-direction: column; gap: var(--s-3); }
.job { display: flex; flex-direction: column; gap: var(--s-3); }
.job-top { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.pill { display: inline-flex; align-items: center; padding: 2px var(--s-3); border-radius: var(--r-pill); font-size: var(--fs-xs); font-weight: var(--fw-medium); }
.pill::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: currentColor; margin-right: 6px; opacity: .8; }
.st-ok   { background: var(--ok-soft); color: var(--ok); }
.st-run  { background: var(--accent-3-soft); color: var(--accent-3); }
.st-wait { background: var(--bg-soft); color: var(--text-3); }
.job-ver { font-size: var(--fs-xs); color: var(--accent-2); font-weight: var(--fw-semi); background: var(--accent-2-soft); padding: 1px var(--s-2); border-radius: var(--r-sm); }
.job-id { color: var(--text-faint); }
.job-time { margin-left: auto; font-size: var(--fs-xs); color: var(--text-faint); }
.job-main { display: flex; flex-direction: column; gap: var(--s-2); }
.job-route { display: flex; align-items: center; gap: var(--s-3); font-size: var(--fs-md); flex-wrap: wrap; }
.job-route b { font-weight: var(--fw-semi); }
.ico { width: 18px; height: 18px; color: var(--text-faint); fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
.job-chips { font-size: var(--fs-sm); color: var(--text-3); }
.job-cust { font-size: var(--fs-sm); color: var(--text-2); }
.job-progress { display: flex; align-items: center; gap: var(--s-3); max-width: 420px; }
.job-progress .progress { flex: 1; }
.job-foot { display: flex; justify-content: flex-end; gap: var(--s-2); }
.empty { text-align: center; color: var(--text-faint); padding: var(--s-7); font-size: var(--fs-sm); }

/* modal */
.modal-mask { position: fixed; inset: 0; z-index: 200; background: rgba(31,29,26,.35); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; padding: var(--s-5); }
.modal { width: min(400px, 100%); padding: var(--s-6); }
.modal-title { font-size: var(--fs-lg); }
.modal-desc { margin-top: var(--s-3); font-size: var(--fs-sm); color: var(--text-2); line-height: var(--lh-base); }
.modal-actions { display: flex; justify-content: flex-end; gap: var(--s-2); margin-top: var(--s-5); }

.t-3 { color: var(--text-3); } .t-xs { font-size: var(--fs-xs); } .t-faint { color: var(--text-faint); }

@media (max-width: 900px) {
  .trip-grid { grid-template-columns: 1fr; }
  .stat-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .trip { flex-direction: column; }
  .trip-cover { width: 100%; aspect-ratio: 12/5; }
}
</style>
