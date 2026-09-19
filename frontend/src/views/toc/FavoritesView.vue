<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { MALL_PLANS } from './mock.js'
import { favApi } from '../../api/index.js'
import { auth } from '../../stores/auth.js'

const router = useRouter()
const TABS = [
  { key: 'plan', label: '整订方案' },
]
const tab = ref('plan')

/* 收藏：GET /api/favorites（返回方案 summary 列表），未登录回退演示数据 */
function toFavView(raw) {
  return {
    id: raw.id,
    name: raw.name || raw.title,
    category: raw.category || '',
    city: raw.city || '',
    days: raw.days || 1,
    pace: raw.pace_zh ? raw.pace_zh.replace('节奏', '') : (raw.pace || '标准'),
    perPrice: raw.per_price || 0,
    oldPrice: raw.original_per_price && raw.original_per_price > (raw.per_price || 0) ? raw.original_per_price : null,
    rating: raw.rating || 4.8,
    emoji: (raw.cover && raw.cover.emoji) || '🧭',
    gradient: (raw.cover && raw.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)',
  }
}
const favItems = ref(MALL_PLANS.slice(0, 3).map(toFavView))

onMounted(async () => {
  if (!auth.isLogin) return
  try {
    const res = await favApi.list()
    const rows = (res && res.items) || []
    if (rows.length || res.total === 0) {
      favItems.value = rows.map(toFavView)
    }
  } catch { /* 回退演示数据 */ }
})

const list = computed(() => favItems.value)

async function unlike(id) {
  try { await favApi.remove(id) } catch { /* 未登录等场景静默 */ }
  favItems.value = favItems.value.filter(p => p.id !== id)
}
</script>

<template>
  <div class="favorites">
    <div class="container">
      <header class="fv-head">
        <div>
          <h1>我的收藏</h1>
          <p class="fv-sub">收藏方案 {{ list.length }} 个 · 后端收藏账本按登录用户隔离</p>
        </div>
        <RouterLink to="/manual" class="btn btn-primary btn-sm">→ 去组装行程</RouterLink>
      </header>

      <nav class="fv-tabs card">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
      </nav>

      <!-- 方案收藏 -->
      <div v-if="tab === 'plan'" class="fv-grid">
        <div v-for="p in list" :key="p.id" class="card fv-card">
          <RouterLink :to="`/malls/product/${p.id}`" class="fc-cover" :style="{ background: p.gradient }">
            <span>{{ p.emoji }}</span>
          </RouterLink>
          <div class="fc-body">
            <RouterLink :to="`/malls/product/${p.id}`" class="fc-name">{{ p.name }}</RouterLink>
            <span class="fc-meta">{{ p.city }} · {{ p.days }} 天 · {{ p.pace }}节奏 · ★ {{ p.rating }}</span>
            <div class="fc-foot">
              <span class="fc-price">¥{{ p.perPrice.toLocaleString() }}/人起</span>
              <div class="fc-ops">
                <button class="op" title="移出收藏" @click="unlike(p.id)">♡</button>
                <RouterLink :to="`/malls/product/${p.id}`" class="btn btn-primary btn-sm">去整订</RouterLink>
              </div>
            </div>
          </div>
        </div>
        <div v-if="!list.length" class="card fv-empty">
          <p>还没有收藏的方案</p>
          <RouterLink to="/malls" class="btn btn-ghost btn-sm">去方案馆逛逛</RouterLink>
        </div>
      </div>

      <!-- 手动组装入口（后端收藏账本仅方案维度） -->
      <div v-else class="card fv-empty">
        <p>标品收藏请进入手动组装器挑选素材</p>
        <RouterLink to="/manual" class="btn btn-ghost btn-sm">→ 去组装器看看</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.favorites { padding: var(--s-7) 0 var(--s-9); }
.fv-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: var(--s-5); flex-wrap: wrap; gap: var(--s-3); }
.fv-head h1 { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; }
.fv-sub { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-3); }

.fv-tabs { display: flex; gap: 2px; padding: 4px; width: fit-content; margin-bottom: var(--s-4); }
.fv-tabs button { border: none; background: transparent; padding: 8px var(--s-4); border-radius: calc(var(--r) - 3px); font-size: var(--fs-sm); color: var(--text-3); }
.fv-tabs button.on { background: var(--surface-2); color: var(--text); font-weight: var(--fw-bold); }

.fv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: var(--s-4); }
.fv-card { overflow: hidden; }
.fc-cover { height: 120px; display: flex; align-items: center; justify-content: center; font-size: 36px; text-decoration: none; }
.fc-cover.stop { background: var(--surface-2); }
.fc-body { padding: var(--s-4); }
.fc-name { font-size: var(--fs-sm); font-weight: var(--fw-bold); color: var(--text); text-decoration: none; display: block; }
.fc-name:hover { color: var(--accent); }
.fc-meta { font-size: var(--fs-xs); color: var(--text-faint); display: block; margin: 4px 0 var(--s-3); }
.fc-foot { display: flex; justify-content: space-between; align-items: center; }
.fc-price { font-size: var(--fs-sm); color: #B0685C; font-weight: var(--fw-bold); }
.fc-tag { font-size: 10px; color: var(--text-faint); }
.fc-ops { display: flex; align-items: center; gap: var(--s-2); }
.op { border: none; background: none; font-size: 16px; color: #B0685C; cursor: pointer; }
.fv-empty { grid-column: 1 / -1; text-align: center; padding: var(--s-8); color: var(--text-faint); font-size: var(--fs-sm); }
</style>
