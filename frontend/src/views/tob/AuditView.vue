<script setup>
import { ref, onMounted } from 'vue'
import TobIcon from '../../components/TobIcon.vue'
import { plansApi, govApi } from '../../api/index.js'

/* 审计日志：GET /api/plans/{job_id}/audit（audit.log 逐行 JSONL） */
const jobId = ref('')

const CLS_MAP = {
  task_completed: 'tag-ok', approval: 'tag-warn', waiting_budget: 'tag-warn',
  waiting_safety: 'tag-warn', safety_block: 'tag-danger', replan: 'tag-info',
  feedback: 'tag-info', task_created: '', approve: 'tag-warn', reject: 'tag-danger',
}
const events = ref([])
const loading = ref(false)

async function load() {
  if (!jobId.value.trim()) return
  loading.value = true
  try {
    const res = await plansApi.audit(jobId.value.trim())
    const rows = (res && res.events) || []
    events.value = rows.slice().reverse().map(e => {
      const action = e.action || e.event || 'event'
      return {
        time: (e.created_at || e.ts || e.time || '').replace('T', ' ').slice(0, 19),
        event: action,
        cls: CLS_MAP[action] || 'tag-info',
        detail: e.detail || e.reason || e.operator || JSON.stringify(e),
      }
    })
  } catch (e) {
    events.value = [{ time: '', event: 'error', cls: 'tag-danger', detail: e.message || '任务不存在或无审计日志' }]
  }
  loading.value = false
}
onMounted(() => {})

function exportCsv() { window.open(govApi.auditCsvUrl(), '_blank') }
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">治理 · 审计</div>
        <h1 class="page-title">合规审计</h1>
        <p class="page-desc">按任务查询全量审计事件(安全扫描、审批、完成等),支持 CSV 全量导出</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" @click="exportCsv"><TobIcon name="download" :size="14" />导出全量审计 CSV</button>
      </div>
    </div>

    <!-- 查询 -->
    <div class="card toolbar">
      <div class="search-box" style="flex:1;max-width:420px">
        <span class="s-ico"><TobIcon name="search" :size="15" /></span>
        <input v-model.trim="jobId" placeholder="plan_xxxx(从方案列表复制)" />
      </div>
      <button class="btn btn-primary btn-sm" :disabled="loading" @click="load">{{ loading ? "查询中…" : "查询审计轨迹" }}</button>
    </div>

    <!-- 事件表 -->
    <div class="card table-card">
      <table class="table">
        <thead><tr><th style="width:180px">时间</th><th style="width:180px">事件</th><th>详情</th></tr></thead>
        <tbody>
          <tr v-for="(a, i) in events" :key="i">
            <td><span class="mono-xs">{{ a.time }}</span></td>
            <td><span class="tag" :class="a.cls">{{ a.event }}</span></td>
            <td style="color:var(--text-2);font-size:var(--fs-sm)">{{ a.detail }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
