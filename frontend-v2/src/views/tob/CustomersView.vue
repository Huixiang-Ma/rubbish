<template>
  <div>
    <div class="page-head">
      <div>
        <h1>客户管理</h1>
        <div class="desc" style="color:var(--text-faint)">按 toB 客户归属聚合的任务量、完成率与活跃度</div>
      </div>
      <button class="btn btn-ghost btn-sm" @click="load">↻ 刷新</button>
    </div>

    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
    <div v-else-if="!rows.length" class="empty card"><div class="icon">👥</div><p>暂无客户归属数据（toB 创建的任务会带 customer 字段）</p></div>
    <div v-else class="card" style="overflow:hidden">
      <table class="table">
        <thead><tr><th>客户</th><th>任务数</th><th>已完成</th><th>挂起/失败</th><th>完成率</th><th>最近活跃</th><th></th></tr></thead>
        <tbody>
          <tr v-for="r in rows" :key="r.name" class="clickable" @click="$router.push({ name: 'tob-plans', query: { customer: r.name } })">
            <td><b>{{ r.name }}</b></td>
            <td>{{ r.total }}</td>
            <td style="color:var(--ok)">{{ r.done }}</td>
            <td style="color:var(--warn)">{{ r.pending }}</td>
            <td>
              <div style="display:flex;align-items:center;gap:10px">
                <div class="progress" style="width:90px;height:7px"><div :style="{ width: r.rate + '%' }"></div></div>
                <span style="font-family:var(--mono);font-size:12.5px">{{ r.rate }}%</span>
              </div>
            </td>
            <td style="font-family:var(--mono);font-size:12px;color:var(--text-faint)">{{ r.last }}</td>
            <td style="color:var(--text-faint)">›</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { plansApi } from '../../api'

const rows = ref([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const r = await plansApi.list({ limit: 500 })
    const map = {}
    for (const it of r.items || []) {
      const k = it.customer || '（散客 toC）'
      map[k] = map[k] || { name: k, total: 0, done: 0, pending: 0, last: '' }
      const m = map[k]
      m.total++
      if (it.status === 'COMPLETED') m.done++
      if (String(it.status).startsWith('WAITING') || it.status === 'FAILED') m.pending++
      if (it.updated_at > m.last) m.last = it.updated_at
    }
    rows.value = Object.values(map)
      .map(m => ({ ...m, rate: m.total ? Math.round((m.done / m.total) * 100) : 0, last: m.last.replace('T', ' ').slice(0, 16) }))
      .sort((a, b) => b.total - a.total)
  } finally { loading.value = false }
}
onMounted(load)
</script>
