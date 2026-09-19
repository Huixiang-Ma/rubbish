<script setup>
import { ref, onMounted } from 'vue'
import TobIcon from '../../components/TobIcon.vue'
import { plansApi } from '../../api/index.js'

/* 客户归属：GET /api/plans 按客户聚合（staff 口径；失败回退演示数据） */
const FALLBACK = [
  { name: '远山国旅', total: 86, done: 72, pending: 6, last: '2026-09-09 14:20' },
  { name: '云途旅行', total: 54, done: 41, pending: 5, last: '2026-09-09 13:48' },
  { name: '海风假期', total: 47, done: 44, pending: 1, last: '2026-09-08 22:41' },
]
const rows = ref(FALLBACK)

async function load() {
  try {
    const res = await plansApi.list({ limit: 500 })
    const arr = (res && res.items) || []
    if (arr.length) {
      const groups = {}
      arr.forEach(j => {
        const name = j.customer || '（散客 toC）'
        const g = groups[name] = groups[name] || { name, total: 0, done: 0, pending: 0, last: '' }
        g.total++
        if (j.status === 'COMPLETED') g.done++
        if (['WAITING_BUDGET_APPROVAL', 'WAITING_SAFETY_REVIEW'].includes(j.status)) g.pending++
        const t = (j.updated_at || j.created_at || '').replace('T', ' ').slice(0, 16)
        if (t > g.last) g.last = t
      })
      rows.value = Object.values(groups).sort((a, b) => b.total - a.total)
    }
  } catch { /* 回退演示数据 */ }
}
onMounted(load)
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">经营分析</div>
        <h1 class="page-title">客户管理</h1>
        <p class="page-desc">按 toB 客户归属聚合的任务量、完成率与活跃度</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="load"><TobIcon name="refresh" :size="14" />刷新</button>
      </div>
    </div>

    <!-- 汇总卡 -->
    <div class="stat-grid">
      <div class="stat-card"><div class="k">合作客户</div><div class="v">{{ rows.length }}</div><div class="sub">含散客归集</div></div>
      <div class="stat-card"><div class="k">任务总量</div><div class="v">{{ rows.reduce((s, r) => s + r.total, 0) }}</div><div class="sub">全部任务</div></div>
      <div class="stat-card"><div class="k">已完成</div><div class="v" style="color:var(--ok)">{{ rows.reduce((s, r) => s + r.done, 0) }}</div><div class="sub">交付完成</div></div>
      <div class="stat-card"><div class="k">挂起 / 失败</div><div class="v" style="color:var(--warn)">{{ rows.reduce((s, r) => s + r.pending, 0) }}</div><div class="sub">需跟进处理</div></div>
    </div>

    <!-- 表格 -->
    <div class="card table-card">
      <table class="table">
        <thead>
          <tr><th>客户</th><th>任务数</th><th>已完成</th><th>挂起/失败</th><th style="min-width:170px">完成率</th><th>最近活跃</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.name" class="clickable-row">
            <td><b style="font-weight:var(--fw-medium)">{{ r.name }}</b></td>
            <td class="tnum">{{ r.total }}</td>
            <td class="tnum" style="color:var(--ok)">{{ r.done }}</td>
            <td class="tnum" style="color:var(--warn)">{{ r.pending }}</td>
            <td>
              <div style="display:flex;align-items:center;gap:var(--s-3)">
                <div class="progress" style="width:100px"><span :style="{ width: Math.round(r.done / r.total * 100) + '%' }" /></div>
                <span class="mono-xs">{{ Math.round(r.done / r.total * 100) }}%</span>
              </div>
            </td>
            <td><span class="mono-xs">{{ r.last }}</span></td>
            <td style="color:var(--text-faint)"><TobIcon name="chevron" :size="14" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tnum { font-variant-numeric: tabular-nums; }
.clickable-row { cursor: pointer; }
.progress > span { background: linear-gradient(90deg, #7E97B0, #A9BCCB); }
</style>
