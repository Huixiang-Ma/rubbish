<template>
  <div>
    <div class="page-head">
      <div>
        <h1>合规审计</h1>
        <div class="desc" style="color:var(--text-faint)">按任务查询全量审计事件（安全扫描、审批、完成等），支持 CSV 全量导出</div>
      </div>
      <a class="btn btn-primary btn-sm" :href="csvUrl" target="_blank" rel="noopener" @click="toast('CSV 导出中…')">⬇ 导出全量审计 CSV</a>
    </div>

    <div class="card card-pad" style="margin-bottom:16px;display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap">
      <div class="field" style="flex:1;min-width:260px">
        <label>任务 job_id</label>
        <input v-model.trim="jobId" class="input" placeholder="plan_xxxx（从方案列表复制）" @keyup.enter="query" />
      </div>
      <button class="btn btn-primary" :disabled="!jobId || loading" @click="query">{{ loading ? '查询中…' : '🔍 查询审计轨迹' }}</button>
    </div>

    <div class="card" style="overflow:hidden">
      <div v-if="!queried" class="empty"><div class="icon">📜</div><p>输入 job_id 查询该任务的完整审计轨迹</p></div>
      <div v-else-if="loading" class="loading-block"><div class="spinner spin"></div></div>
      <div v-else-if="!events.length" class="empty"><div class="icon">🕳</div><p>该任务暂无审计事件</p></div>
      <table v-else class="table">
        <thead><tr><th style="width:170px">时间</th><th style="width:170px">事件</th><th>详情</th></tr></thead>
        <tbody>
          <tr v-for="(a, i) in events" :key="i">
            <td style="font-family:var(--mono);font-size:12px;color:var(--text-faint)">{{ (a.created_at || a.ts || '').replace('T', ' ').slice(0, 19) }}</td>
            <td><span class="tag" :class="cls(a)">{{ a.event || a.action || a.type }}</span></td>
            <td style="color:var(--text-dim);font-size:13px">{{ det(a) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { govApi, plansApi } from '../../api'
import { toast } from '../../composables/toast'

const jobId = ref('')
const events = ref([])
const loading = ref(false)
const queried = ref(false)
const csvUrl = govApi.auditCsvUrl()

async function query() {
  if (!jobId.value) return
  loading.value = true
  queried.value = true
  try {
    const r = await plansApi.audit(jobId.value)
    events.value = r.items || r.events || (Array.isArray(r) ? r : [])
  } catch (e) { toast(e.message, 'err'); events.value = [] } finally { loading.value = false }
}

function cls(a) {
  const ev = (a.event || a.action || a.type || '') + ''
  if (ev.includes('safety') || ev.includes('block')) return 'tag-red'
  if (ev.includes('approval') || ev.includes('wait')) return 'tag-amber'
  if (ev.includes('complete')) return 'tag-green'
  return 'tag-blue'
}
function det(a) {
  if (a.detail) return typeof a.detail === 'object' ? JSON.stringify(a.detail) : a.detail
  return a.message || a.reason || (typeof a.data === 'object' ? JSON.stringify(a.data) : a.data) || a.operator || '—'
}
</script>
