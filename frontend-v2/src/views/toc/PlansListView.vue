<template>
  <div class="container list-page">
    <div class="sec-title">我的行程</div>
    <p class="sec-desc">全部行程任务与实时状态，点击查看行程书</p>

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
    <div v-else-if="!items.length" class="empty card"><div class="icon">🧳</div><p>还没有行程，去首页创建一趟吧</p>
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
          <span class="p-go">查看行程书 →</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { plansApi } from '../../api'
import StatusTag from '../../components/StatusTag.vue'

const STATUSES = ['QUEUED', 'RUNNING', 'COMPLETED', 'WAITING_SAFETY_REVIEW', 'WAITING_BUDGET_APPROVAL', 'FAILED']

const items = ref([])
const loading = ref(true)
const filter = reactive({ status: '', customer: '' })

async function load() {
  loading.value = true
  try {
    const r = await plansApi.list({ status: filter.status || undefined, customer: filter.customer || undefined, limit: 100 })
    items.value = r.items || []
  } catch { items.value = [] } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.list-page { padding-top: 32px; }
.plans { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
.plan-card { padding: 20px 22px; cursor: pointer; }
.p-top { display: flex; align-items: center; gap: 8px; }
.p-date { margin-left: auto; font-size: 12px; color: var(--ink-400); font-family: var(--mono); }
.p-dest { font-size: 19px; font-weight: 900; margin-top: 12px; letter-spacing: -.01em; }
.p-origin { font-size: 13px; color: var(--ink-400); font-weight: 500; }
.p-meta { font-size: 13px; color: var(--ink-500); margin-top: 5px; }
.p-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 13px; border-top: 1px dashed var(--ink-200); }
.p-id { font-family: var(--mono); font-size: 11.5px; color: var(--ink-400); }
.p-go { font-size: 13px; font-weight: 700; color: var(--brand-600); }
</style>
