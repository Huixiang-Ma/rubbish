<script setup>
import { ref, onMounted } from 'vue'
import TobIcon from '../../components/TobIcon.vue'
import { govApi, plansApi } from '../../api/index.js'

/* 审批队列：GET /api/approvals/pending + POST /api/plans/{job}/approval */
const FALLBACK = [
  {
    job: 'plan_9c1e77', status: '预算挂起', statusCls: 'tag-warn',
    dest: '大理', origin: '成都', customer: '云途旅行', version: 2,
    days: 5, budget: 6000, resume: 'route_planner',
    updated: '2026-09-09 13:48', err: '',
  },
]
const items = ref(FALLBACK)

const ZH = { WAITING_BUDGET_APPROVAL: { label: '预算挂起', cls: 'tag-warn' }, WAITING_SAFETY_REVIEW: { label: '安全挂起', cls: 'tag-danger' } }
function toRow(j) {
  const meta = ZH[j.status] || { label: j.status, cls: 'tag-warn' }
  return {
    job: j.job_id, status: meta.label, statusCls: meta.cls,
    dest: j.destination || '—', origin: j.origin || '',
    customer: j.customer || '（散客 toC）', version: j.version || 1,
    days: j.days || 0, budget: j.budget || 0, resume: j.resume_from || 'intake',
    updated: (j.updated_at || '').replace('T', ' ').slice(0, 16),
    err: j.error || '',
    operator: 'admin', reason: '',
  }
}

async function load() {
  try {
    const res = await govApi.pendingApprovals()
    const rows = (res && res.items) || []
    if (rows.length || res.total === 0) items.value = rows.map(toRow)
  } catch { /* 回退演示数据 */ }
}
onMounted(load)

const acting = ref(false)
async function decide(it, ok) {
  if (acting.value) return
  acting.value = true
  try {
    await plansApi.approval(it.job, {
      decision: ok ? 'approve' : 'reject',
      operator: it.operator || 'admin',
      reason: it.reason || (ok ? '审核通过放行' : '审核拒绝'),
      base_version: it.version || 1,
    })
    items.value = items.value.filter(x => x.job !== it.job)
  } catch (e) {
    window.alert(e.message || '审批提交失败')
  } finally { acting.value = false }
}
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">治理 · 人机协同</div>
        <h1 class="page-title">HITL 审核台</h1>
        <p class="page-desc">Human-in-the-Loop:预算挂起 + 安全挂起的待审批队列,放行后任务自动续跑</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="load"><TobIcon name="refresh" :size="14" />刷新</button>
      </div>
    </div>

    <!-- 队列 -->
    <div class="queue">
      <div v-for="it in items" :key="it.job" class="card q-card">
        <div class="q-top">
          <span class="tag" :class="it.statusCls">{{ it.status }}</span>
          <span class="q-dest">{{ it.dest }}<template v-if="it.origin"> · {{ it.origin }}出发</template></span>
          <span class="tag tag-accent-2">{{ it.customer }}</span>
          <span class="tag">v{{ it.version }}</span>
          <span class="q-time">{{ it.updated }}</span>
        </div>
        <div class="q-info">
          <span class="mono-xs" style="color:var(--text-3)">{{ it.job }}</span>
          <span>{{ it.days }} 天 · ¥{{ it.budget.toLocaleString() }}</span>
          <span>放行后从 <b>{{ it.resume }}</b> 节点续跑</span>
        </div>
        <div v-if="it.err" class="q-err">
          <TobIcon name="shield" :size="14" style="flex:none;margin-top:2px" />
          <span>{{ it.err }}</span>
        </div>
        <div class="q-actions">
          <input v-model.trim="it.operator" class="input" style="width:120px;height:36px" placeholder="操作人" value="admin" />
          <input v-model.trim="it.reason" class="input" style="flex:1;height:36px" placeholder="审批意见(可选)" />
          <button class="btn btn-primary-soft btn-sm" :disabled="acting" @click="decide(it, true)"><TobIcon name="check" :size="14" />放行续跑</button>
          <button class="btn btn-ghost btn-sm" style="color:var(--danger)" :disabled="acting" @click="decide(it, false)"><TobIcon name="x" :size="14" />拒绝</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.queue { display: flex; flex-direction: column; gap: var(--s-4); }
.q-card { padding: var(--s-5); }
.q-top { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.q-dest { font-size: var(--fs-md); font-weight: var(--fw-semi); letter-spacing: -0.01em; }
.q-time { margin-left: auto; font-family: var(--mono); font-size: var(--fs-xs); color: var(--text-faint); }
.q-info {
  display: flex; gap: var(--s-5); margin-top: var(--s-3);
  font-size: var(--fs-sm); color: var(--text-2); flex-wrap: wrap;
}
.q-info b { color: var(--accent-2); font-weight: var(--fw-medium); }
.q-err {
  margin-top: var(--s-4);
  display: flex; gap: var(--s-2);
  background: var(--danger-soft); color: var(--danger);
  font-size: var(--fs-sm); line-height: var(--lh-base);
  padding: var(--s-3) var(--s-4);
  border-radius: var(--r);
}
.q-actions { display: flex; gap: var(--s-2); margin-top: var(--s-5); flex-wrap: wrap; }
</style>
