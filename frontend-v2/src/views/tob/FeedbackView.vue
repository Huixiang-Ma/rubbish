<template>
  <div>
    <div class="page-head">
      <div>
        <h1>客户之声</h1>
        <div class="desc" style="color:var(--text-faint)">toC 反馈聚合：表扬 / 投诉 / 建议，直达行程质量改进</div>
      </div>
      <button class="btn btn-ghost btn-sm" @click="load">↻ 刷新</button>
    </div>

    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
    <template v-else-if="fb">
      <div class="stat-grid">
        <div class="card stat-card"><div class="k">反馈总数</div><div class="v">{{ fb.total }}</div></div>
        <div class="card stat-card"><div class="k">👍 表扬</div><div class="v" style="color:var(--ok)">{{ fb.praise_count }}</div></div>
        <div class="card stat-card"><div class="k">👎 投诉</div><div class="v" style="color:var(--danger)">{{ fb.complaint_count }}</div></div>
        <div class="card stat-card"><div class="k">好评率</div><div class="v">{{ fb.total ? Math.round((fb.praise_count / fb.total) * 100) : 0 }}%</div></div>
      </div>

      <div class="fb-list">
        <div v-if="!(fb.items || []).length" class="empty card"><div class="icon">📣</div><p>还没有客户反馈</p></div>
        <div v-for="(it, i) in fb.items || []" :key="i" class="card fb-card">
          <div class="fb-top">
            <span class="tag" :class="it.kind === 'praise' ? 'tag-green' : 'tag-red'">{{ it.kind === 'praise' ? '👍 表扬' : '👎 投诉' }}</span>
            <b class="fb-op">{{ it.operator }}</b>
            <span v-if="it.customer" class="tag tag-blue">{{ it.customer }}</span>
            <span v-if="it.destination" class="fb-dest">· {{ it.destination }}</span>
            <span class="fb-time">{{ (it.created_at || '').replace('T', ' ').slice(0, 16) }}</span>
          </div>
          <p class="fb-content">{{ it.content }}</p>
          <router-link v-if="it.job_id" :to="{ name: 'plan-detail', params: { jobId: it.job_id } }" class="fb-link">查看关联行程 →</router-link>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { govApi } from '../../api'

const fb = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try { fb.value = await govApi.feedbacks() } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.fb-list { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
.fb-card { padding: 18px 22px; }
.fb-top { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.fb-op { font-size: 14px; }
.fb-dest { color: var(--text-faint); font-size: 13px; }
.fb-time { margin-left: auto; font-family: var(--mono); font-size: 12px; color: var(--text-faint); }
.fb-content { margin-top: 10px; font-size: 14px; color: var(--text-dim); line-height: 1.7; }
.fb-link { font-size: 12.5px; margin-top: 8px; display: inline-block; text-decoration: none; }
.fb-link:hover { text-decoration: underline; }
</style>
