<template>
  <div>
    <div class="page-head">
      <div>
        <h1>HITL 审核台</h1>
        <div class="desc" style="color:var(--text-faint)">Human-in-the-Loop：预算挂起 + 安全挂起的待审批队列，放行后任务自动续跑</div>
      </div>
      <button class="btn btn-ghost btn-sm" @click="load">↻ 刷新</button>
    </div>

    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
    <div v-else-if="!items.length" class="empty card"><div class="icon">⚖️</div><p>队列清空，没有待审批任务 ✓</p></div>

    <div v-else class="queue">
      <div v-for="it in items" :key="it.job_id" class="card q-card">
        <div class="q-top">
          <StatusTag :status="it.status" />
          <span class="q-dest">{{ it.destination }}<template v-if="it.origin"> · {{ it.origin }}出发</template></span>
          <span v-if="it.customer" class="tag tag-blue">{{ it.customer }}</span>
          <span class="tag tag-gray">v{{ it.version }}</span>
          <span class="q-time">{{ (it.updated_at || '').replace('T', ' ').slice(0, 16) }}</span>
        </div>
        <div class="q-info">
          <span class="q-item">{{ it.days }} 天 · ¥{{ Number(it.budget || 0).toLocaleString() }}</span>
          <span v-if="it.resume_from" class="q-item">放行后从 <b>{{ it.resume_from }}</b> 节点续跑</span>
        </div>
        <div v-if="it.error" class="q-err">⚠ {{ it.error }}</div>
        <div class="q-actions">
          <input v-model="opName" class="input" style="width:120px" placeholder="操作人" />
          <input v-model="reasons[it.job_id]" class="input" style="flex:1" placeholder="审批意见（可选）" />
          <button class="btn btn-ok" :disabled="busy === it.job_id" @click="decide(it, 'approve')">✓ 放行续跑</button>
          <button class="btn btn-danger" :disabled="busy === it.job_id" @click="decide(it, 'reject')">✕ 拒绝</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { govApi, plansApi } from '../../api'
import { toast } from '../../composables/toast'
import StatusTag from '../../components/StatusTag.vue'

const items = ref([])
const loading = ref(true)
const busy = ref('')
const opName = ref('admin')
const reasons = reactive({})

async function load() {
  loading.value = true
  try { items.value = (await govApi.pendingApprovals()).items || [] }
  catch (e) { toast(e.message, 'err') } finally { loading.value = false }
}
onMounted(load)

async function decide(it, decision) {
  busy.value = it.job_id
  try {
    await plansApi.approval(it.job_id, {
      decision, operator: opName.value || 'admin',
      reason: reasons[it.job_id] || (decision === 'approve' ? '审核放行' : '审核拒绝'),
      base_version: it.version,
    })
    toast(decision === 'approve' ? `${it.job_id} 已放行续跑` : `${it.job_id} 已拒绝`, 'ok')
    load()
  } catch (e) { toast(e.message, 'err') } finally { busy.value = '' }
}
</script>

<style scoped>
.queue { display: flex; flex-direction: column; gap: 14px; }
.q-card { padding: 20px 24px; }
.q-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.q-dest { font-size: 17px; font-weight: 800; }
.q-time { margin-left: auto; font-family: var(--mono); font-size: 12px; color: var(--text-faint); }
.q-info { display: flex; gap: 18px; margin-top: 9px; font-size: 13px; color: var(--text-dim); flex-wrap: wrap; }
.q-info b { color: var(--brand); }
.q-err { margin-top: 10px; background: rgba(248,113,113,.1); color: var(--danger); font-size: 13px; padding: 10px 14px; border-radius: var(--r-sm); line-height: 1.6; }
.q-actions { display: flex; gap: 9px; margin-top: 14px; flex-wrap: wrap; }
</style>
