<script setup>
import { ref, onMounted } from 'vue'
import TobIcon from '../../components/TobIcon.vue'
import { govApi } from '../../api/index.js'

/* 客户之声：GET /api/feedbacks（从任务审计日志聚合 praise/complaint） */
const FALLBACK = {
  total: 128, praise_count: 96, complaint_count: 21, suggestion_count: 11,
  items: [
    { kind: 'praise', operator: '导游 · 小雪', customer: '远山国旅', dest: '苏州', content: '拙政园的时间安排很合理,避开了上午的人流高峰。', time: '2026-09-09 12:40' },
    { kind: 'complaint', operator: '导游 · 阿凯', customer: '云途旅行', dest: '大理', content: '白族家访体验实际到店发现当日停办,方案里没有备选项。', time: '2026-09-09 09:15' },
  ],
}
const fb = ref(FALLBACK)

async function load() {
  try {
    const res = await govApi.feedbacks({ limit: 100 })
    if (res && (res.items || res.total !== undefined)) fb.value = { ...FALLBACK, ...res }
  } catch { /* 回退演示数据 */ }
}
onMounted(load)

function kindMeta(k) {
  return {
    praise: { label: '表扬', cls: 'tag-ok', icon: 'megaphone' },
    complaint: { label: '投诉', cls: 'tag-danger', icon: 'megaphone' },
    suggestion: { label: '建议', cls: 'tag-warn', icon: 'megaphone' },
  }[k]
}
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">治理 · 反馈</div>
        <h1 class="page-title">客户之声</h1>
        <p class="page-desc">toC 反馈聚合:表扬 / 投诉 / 建议,直达行程质量改进</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="load"><TobIcon name="refresh" :size="14" />刷新</button>
      </div>
    </div>

    <!-- 统计 -->
    <div class="stat-grid">
      <div class="stat-card"><div class="k">反馈总数</div><div class="v">{{ fb.total }}</div><div class="sub">近 90 天</div></div>
      <div class="stat-card"><div class="k">表扬</div><div class="v" style="color:var(--ok)">{{ fb.praise_count }}</div><div class="sub">正向反馈</div></div>
      <div class="stat-card"><div class="k">投诉</div><div class="v" style="color:var(--danger)">{{ fb.complaint_count }}</div><div class="sub">需跟进改进</div></div>
      <div class="stat-card"><div class="k">好评率</div><div class="v">{{ Math.round(fb.praise_count / fb.total * 100) }}%</div><div class="sub">表扬 / 总数</div></div>
    </div>

    <!-- 反馈列表 -->
    <div class="fb-list">
      <div v-for="(it, i) in fb.items" :key="i" class="card fb-card">
        <div class="fb-top">
          <span class="tag" :class="kindMeta(it.kind).cls">{{ kindMeta(it.kind).label }}</span>
          <b>{{ it.operator }}</b>
          <span v-if="it.customer" class="tag tag-accent-2">{{ it.customer }}</span>
          <span class="fb-dest">· {{ it.dest }}</span>
          <span class="fb-time">{{ it.time }}</span>
        </div>
        <p class="fb-content">{{ it.content }}</p>
        <a class="fb-link">查看关联行程 <TobIcon name="arrowRight" :size="12" /></a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fb-list { display: flex; flex-direction: column; gap: var(--s-3); }
.fb-card { padding: var(--s-4) var(--s-5); }
.fb-top { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.fb-top b { font-size: var(--fs-sm); font-weight: var(--fw-medium); }
.fb-dest { color: var(--text-faint); font-size: var(--fs-sm); }
.fb-time { margin-left: auto; font-family: var(--mono); font-size: var(--fs-xs); color: var(--text-faint); }
.fb-content { margin-top: var(--s-3); font-size: var(--fs-sm); color: var(--text-2); line-height: var(--lh-loose); }
.fb-link {
  margin-top: var(--s-3);
  display: inline-flex; align-items: center; gap: var(--s-1);
  font-size: var(--fs-xs); color: var(--text-3);
  transition: color var(--dur-1) var(--ease);
  cursor: pointer;
}
.fb-link:hover { color: var(--text); }
</style>
