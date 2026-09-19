<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { plansApi } from '../../api/index.js'

const route = useRoute()
const result = ref(null)
const status = ref('loading')

onMounted(async () => {
  try {
    result.value = await plansApi.result(route.params.jobId)
    status.value = 'ok'
  } catch {
    status.value = 'gone'
  }
})
const ui = computed(() => {
  const r = result.value
  if (!r) return null
  const input = r.user_input || {}
  const itin = Array.isArray(r.itinerary) ? r.itinerary : []
  return {
    dest: input.destination || '目的地',
    days: input.days || itin.length || 1,
    stops: itin.reduce((n, d) => n + (d.items || []).length, 0),
    daysList: itin.map(d => ({ day: d.day, theme: d.theme || `第 ${d.day} 天`, stops: (d.items || []).map(i => (i.spot && i.spot.name) || i.title || '') })),
  }
})
</script>

<template>
  <div class="share">
    <RouterLink to="/" class="brand"><span class="mark">迹</span><b>迹程智游</b></RouterLink>

    <div v-if="status === 'ok' && ui" class="card share-card">
      <span class="eyebrow">AI 行程书 · 已生成</span>
      <h1>{{ ui.dest }} {{ ui.days }} 日行程</h1>
      <p class="sub">共 {{ ui.stops }} 个停留点 · 由 10 个智能体协作规划 · 行程可编辑可整订</p>
      <div v-for="d in ui.daysList" :key="d.day" class="day-row">
        <span class="day-no">D{{ d.day }}</span>
        <div>
          <b>{{ d.theme }}</b>
          <p>{{ d.stops.join(' → ') || '自由安排' }}</p>
        </div>
      </div>
      <div class="cta">
        <RouterLink to="/planner" class="btn btn-primary">✦ 生成我的行程</RouterLink>
        <RouterLink to="/malls" class="btn btn-ghost">逛逛在售方案</RouterLink>
      </div>
    </div>
    <div v-else-if="status === 'gone'" class="card share-card">
      <p>该行程不存在或已过期。</p>
      <RouterLink to="/planner" class="btn btn-primary">去生成我的行程</RouterLink>
    </div>
    <p v-else class="loading">加载中…</p>
  </div>
</template>

<style scoped>
.share { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--s-5); padding: var(--s-6) var(--s-4); background: var(--bg); }
.brand { display: flex; align-items: center; gap: var(--s-2); text-decoration: none; }
.mark { width: 30px; height: 30px; border-radius: 8px; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: var(--fw-bold); }
.brand b { color: var(--text); }
.share-card { width: min(560px, 100%); padding: var(--s-7) var(--s-6); text-align: center; }
.share-card h1 { font-size: var(--fs-2xl); margin: var(--s-3) 0; letter-spacing: -0.02em; }
.sub { color: var(--text-2); font-size: var(--fs-sm); margin-bottom: var(--s-5); }
.day-row { display: flex; gap: var(--s-3); text-align: left; padding: var(--s-3) 0; border-top: 1px solid var(--border-soft); }
.day-no { color: var(--accent); font-weight: var(--fw-bold); flex: none; }
.day-row b { font-size: var(--fs-sm); }
.day-row p { margin: 2px 0 0; font-size: var(--fs-xs); color: var(--text-3); }
.cta { display: flex; gap: var(--s-3); justify-content: center; margin-top: var(--s-5); }
.loading { color: var(--text-faint); }
.btn { display: inline-block; text-decoration: none; padding: 10px var(--s-5); border-radius: var(--r-pill); font-weight: var(--fw-medium); }
.btn-primary { background: var(--accent); color: #fff; }
.btn-ghost { border: 1px solid var(--border); color: var(--text-2); }
.eyebrow { font-size: var(--fs-xs); color: var(--accent); letter-spacing: 0.1em; }
</style>
