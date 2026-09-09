<template>
  <div class="container book-page">
    <template v-if="loading">
      <div class="loading-block"><div class="spinner spin"></div>行程书加载中…</div>
    </template>

    <template v-else-if="!trip">
      <div class="empty card big"><div class="icon">🧳</div><p>没有找到这份行程书，可能已被删除</p>
        <div class="act"><router-link :to="{ name: 'planner' }" class="btn btn-primary">✦ 去规划新行程</router-link>
          <router-link :to="{ name: 'my-plans' }" class="btn btn-soft">返回我的行程</router-link></div>
      </div>
    </template>

    <template v-else>
      <!-- ============ 就地编辑态（与规划器共用同一编辑器组件） ============ -->
      <TripDayEditor v-if="editing" :trip="trip" @saved="onEdited" @cancelled="exitEdit" />

      <!-- ============ 只读态：行程书展示 ============ -->
      <template v-else>
      <!-- 行程书头 -->
      <div class="book-hero">
        <div class="bh-main">
          <div class="bh-cover" :style="{ background: trip.cover.gradient || 'linear-gradient(135deg,#60A5FA,#8B5CF6)' }">
            <span>{{ trip.cover.emoji || '🧩' }}</span>
          </div>
          <div class="bh-info">
            <div class="bh-tags">
              <span class="tag-blue">{{ trip.city }} · {{ trip.days }} 天{{ trip.days > 1 ? (trip.days - 1) + ' 晚' : '' }}</span>
              <span v-if="trip.theme" class="tag-purple">{{ trip.theme }}</span>
              <span v-if="trip.pace" class="tag-gray">{{ paceLabel(trip.pace) }}</span>
              <span v-if="trip.audience" class="tag-gray">👥 {{ trip.audience }}</span>
            </div>
            <h1 class="bh-title">{{ trip.title }}</h1>
            <div class="bh-meta">
              <span v-if="trip.travelers">👤 {{ trip.travelers }} 人出行</span>
              <span v-if="trip.start_date">📅 {{ fmtDate(trip.start_date) }} 出发</span>
              <span>🕒 {{ trip.days }} 天 · {{ stopTotal }} 个停留 · 覆盖 {{ catTotal }} 类标品</span>
            </div>
            <div v-if="trip.note" class="bh-note">📝 {{ trip.note }}</div>
          </div>
        </div>
        <div class="bh-side">
          <div class="bh-price">
            <div class="bp-label">预计花费 <small>模板参考 + 调整</small></div>
            <b>¥{{ fmt(totalCost) }}</b>
            <div class="bp-sub">
              <span>模板参考 ¥{{ fmt(trip.base_total || 0) }}</span>
              <span v-if="(trip.delta || 0) !== 0" :class="trip.delta > 0 ? 'up' : 'down'">{{ trip.delta > 0 ? '+' : '−' }}¥{{ fmt(Math.abs(trip.delta || 0)) }} 调整</span>
            </div>
          </div>
          <div class="bh-actions">
            <router-link :to="{ name: 'planner-trip-map', params: { tripId: trip.id } }" class="btn btn-ghost">🗺 地图 / 时间线</router-link>
            <button class="btn btn-primary" @click="enterEdit">✏️ 就地编辑</button>
            <button class="btn btn-ghost" @click="onDelete">🗑 删除行程书</button>
          </div>
        </div>
      </div>

      <!-- 逐日时间轴 -->
      <div class="day-book">
        <section v-for="d in trip.dayPlans" :key="d.day" class="db-day">
          <header class="db-head">
            <div class="db-dayno">{{ d.day }}</div>
            <div class="db-titles">
              <div class="db-title">第 {{ d.day }} 天</div>
              <div class="db-sub">{{ daySummary(d) }}</div>
            </div>
            <div class="db-stat">{{ d.blocks.length }} 个停留 · ¥{{ fmt(dayPrice(d)) }}</div>
          </header>

          <div class="db-body">
            <div v-for="b in d.blocks" :key="b.key" class="db-row">
              <div class="db-time">
                <span class="t">{{ b.start }}</span>
                <span class="p">{{ periodLabel(b.period) }}</span>
              </div>
              <div class="db-line"><i class="dot" :style="{ borderColor: catColor(b.product.category) }"></i></div>
              <router-link :to="{ name: 'malls-product', params: { id: b.product.id } }" class="db-card">
                <span class="dc-emoji" :style="{ background: b.product.cover.gradient }">{{ b.product.cover.emoji }}</span>
                <div class="dc-info">
                  <div class="dc-name">{{ b.product.name }}
                    <span v-if="b.tag" class="dc-tag">{{ b.tag }}</span>
                  </div>
                  <div class="dc-meta">
                    <span class="dc-cat" :style="{ color: catColor(b.product.category) }">{{ b.product.category }}</span>
                    <span v-for="t in (b.product.tags || []).slice(0, 3)" :key="t">{{ t }}</span>
                    <span v-if="b.product.level && b.product.level !== '-'">{{ b.product.level }}</span>
                    <span>★ {{ b.product.rating ? b.product.rating.toFixed(1) : '—' }}</span>
                  </div>
                </div>
                <div class="dc-price">{{ priceText(b.product) }}</div>
                <div class="dc-go">详情 →</div>
              </router-link>
            </div>
          </div>
        </section>
      </div>

      <div class="book-foot">
        <p>本行程书由「行程规划器」基于标品模板编排生成；每个停留点均可回到商城查看规格与 SKU。</p>
        <router-link :to="{ name: 'planner' }" class="link-more">✦ 再规划一条行程 →</router-link>
      </div>
      </template><!-- /只读态 -->
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTripStore } from '../../composables/tripStore'
import { toast } from '../../composables/toast'
import TripDayEditor from '../../components/TripDayEditor.vue'

const route = useRoute()
const router = useRouter()
const store = useTripStore()

const PERIODS = {
  morning: '上午', midday: '午餐', afternoon: '下午', evening: '晚间', night: '夜宿',
}
const CATS = [
  { name: '景点', color: '#0EA5E9' }, { name: '餐饮', color: '#F59E0B' },
  { name: '住宿', color: '#8B5CF6' }, { name: '交通', color: '#10B981' },
  { name: '购物', color: '#EC4899' }, { name: '文化', color: '#6366F1' },
]

const trip = ref(null)
const loading = ref(true)
const editing = ref(false)

const stopTotal = computed(() => (trip.value?.dayPlans || []).reduce((s, d) => s + d.blocks.length, 0))
const catTotal = computed(() => {
  const set = new Set()
  for (const d of trip.value?.dayPlans || []) for (const b of d.blocks) set.add(b.product.category)
  return set.size
})
const totalCost = computed(() => (trip.value?.base_total || 0) + (trip.value?.delta || 0))

onMounted(() => {
  trip.value = store.get(String(route.params.tripId || ''))
  if (route.query.mode === 'edit' && trip.value) editing.value = true
  loading.value = false
})

function syncUrl(query) {
  router.replace({ name: 'planner-trip', params: { tripId: trip.value.id }, query })
}
function enterEdit() {
  if (!trip.value) return
  editing.value = true
  syncUrl({ mode: 'edit' })
}
function exitEdit() {
  editing.value = false
  syncUrl({})
}
function onEdited(savedTrip) {
  trip.value = savedTrip || store.get(trip.value.id)
  editing.value = false
  syncUrl({})
}

function onDelete() {
  if (!window.confirm(`确定删除行程书「${trip.value?.title}」吗？此操作不可恢复。`)) return
  store.remove(trip.value.id)
  toast('行程书已删除', 'ok')
  router.replace({ name: 'my-plans' })
}
function fmt(n) { return Number(n || 0).toLocaleString('zh-CN') }
function fmtDate(s) { return s ? String(s).replace(/-/g, ' / ') : '' }
function paceLabel(p) { return ({ relaxed: '🛋 悠闲', standard: '⚖ 标准', tight: '⚡ 紧凑' })[p] || p }
function periodLabel(k) { return PERIODS[k] || k }
function catColor(c) { return (CATS.find(x => x.name === c) || {}).color || '#64748B' }
function priceText(p) {
  if (!p || p.price_min == null) return '—'
  if (p.price_min === 0) return '免费'
  const max = p.price_max && p.price_max > p.price_min ? '~' + p.price_max : ''
  return '¥' + p.price_min + max
}
function dayPrice(d) {
  return (d.blocks || []).reduce((s, b) => s + (b.product.price_min || 0), 0)
}
function daySummary(d) {
  const names = (d.blocks || []).filter(b => b.period !== 'night').slice(0, 2).map(b => b.product.name)
  return names.length ? names.join(' → ') + ((d.blocks || []).filter(b => b.period !== 'night').length > 2 ? ' 等' : '') : '自由安排'
}
</script>

<style scoped>
.book-page { padding-top: 28px; max-width: 1060px; }
.loading-block { padding: 90px 0; text-align: center; color: var(--ink-400); }
.empty.big { padding: 80px 20px; text-align: center; }
.empty .icon { font-size: 54px; }
.empty p { font-size: 15px; color: var(--ink-500); }
.act { display: flex; gap: 10px; justify-content: center; margin-top: 18px; }

.book-hero {
  display: grid; grid-template-columns: 1fr 300px; gap: 24px;
  padding: 26px 28px; border-radius: var(--r-xl);
  background:
    radial-gradient(700px 260px at 96% -10%, rgba(139,92,246,.09), transparent 55%),
    radial-gradient(600px 240px at 2% 0%, rgba(245,158,11,.08), transparent 55%),
    linear-gradient(180deg, #fff, var(--ink-50));
  border: 1px solid var(--ink-100); box-shadow: var(--shadow-md);
}
.bh-main { display: flex; gap: 20px; min-width: 0; }
.bh-cover { width: 108px; height: 108px; border-radius: 18px; flex: none; display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow-md); }
.bh-cover span { font-size: 56px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.18)); }
.bh-info { min-width: 0; }
.bh-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.tag-blue { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; font-size: 11.5px; padding: 3px 10px; border-radius: 999px; font-weight: 600; }
.tag-purple { background: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE; font-size: 11.5px; padding: 3px 10px; border-radius: 999px; font-weight: 600; }
.tag-gray { background: var(--ink-100); color: var(--ink-600); font-size: 11.5px; padding: 3px 10px; border-radius: 999px; font-weight: 600; }
.bh-title { font-size: 26px; font-weight: 900; letter-spacing: -.02em; color: var(--ink-900); margin: 4px 0 8px; }
.bh-meta { display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; color: var(--ink-500); }
.bh-note { margin-top: 12px; padding: 10px 14px; background: rgba(255,255,255,.8); border: 1px dashed var(--ink-200); border-radius: 10px; font-size: 12.5px; color: var(--ink-600); line-height: 1.7; }

.bh-side { display: flex; flex-direction: column; justify-content: space-between; gap: 14px; }
.bh-price { background: #fff; border: 1px solid var(--ink-200); border-radius: var(--r-lg); padding: 16px 18px; text-align: center; }
.bp-label { font-size: 12px; color: var(--ink-500); }
.bp-label small { display: block; color: var(--ink-400); font-size: 10.5px; margin-top: 2px; }
.bh-price b { display: block; font-size: 30px; font-weight: 900; color: var(--danger); margin: 6px 0; }
.bp-sub { display: flex; gap: 10px; justify-content: center; font-size: 11.5px; color: var(--ink-400); flex-wrap: wrap; }
.bp-sub .up { color: var(--danger); font-weight: 700; }
.bp-sub .down { color: var(--ok); font-weight: 700; }
.bh-actions { display: flex; gap: 8px; }
.bh-actions .btn { flex: 1; }

.day-book { margin-top: 20px; display: flex; flex-direction: column; gap: 14px; }
.db-day { border: 1px solid var(--ink-200); border-radius: var(--r-lg); background: #fff; overflow: hidden; }
.db-head { display: flex; align-items: center; gap: 14px; padding: 14px 20px; background: linear-gradient(90deg, var(--ink-50), #fff); border-bottom: 1px solid var(--ink-100); }
.db-dayno { width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, var(--brand-600), var(--brand-400)); color: #fff; font-size: 18px; font-weight: 900; display: flex; align-items: center; justify-content: center; }
.db-title { font-weight: 800; font-size: 16px; color: var(--ink-900); }
.db-sub { font-size: 12.5px; color: var(--ink-500); margin-top: 2px; }
.db-stat { margin-left: auto; font-size: 12.5px; color: var(--ink-500); background: #fff; border: 1px solid var(--ink-200); padding: 5px 12px; border-radius: 999px; white-space: nowrap; }

.db-body { padding: 10px 20px 14px; }
.db-row { display: grid; grid-template-columns: 70px 18px 1fr; gap: 6px; }
.db-time { padding-top: 10px; text-align: right; display: flex; flex-direction: column; align-items: flex-end; }
.db-time .t { font-family: var(--mono); font-size: 12.5px; font-weight: 700; color: var(--ink-700); }
.db-time .p { font-size: 11px; color: var(--ink-400); }
.db-line { position: relative; display: flex; justify-content: center; }
.db-line::after { content: ''; position: absolute; top: 20px; bottom: -4px; width: 2px; background: var(--ink-200); }
.db-row:last-child .db-line::after { display: none; }
.dot { width: 12px; height: 12px; border-radius: 50%; margin-top: 16px; background: #fff; border: 3px solid var(--ink-300); box-shadow: 0 0 0 1px var(--ink-300); z-index: 1; }
.db-card { display: grid; grid-template-columns: 40px 1fr auto auto; gap: 12px; align-items: center; padding: 9px 6px; border-radius: 10px; text-decoration: none !important; transition: background .12s; }
.db-card:hover { background: var(--brand-50); }
.dc-emoji { width: 40px; height: 40px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.dc-name { font-weight: 700; font-size: 14px; color: var(--ink-900); display: flex; align-items: center; gap: 6px; }
.dc-tag { font-size: 10.5px; background: var(--brand-50); color: var(--brand-700); border: 1px solid var(--brand-200); padding: 0 7px; border-radius: 999px; }
.dc-meta { display: flex; gap: 8px; align-items: center; margin-top: 3px; font-size: 11px; color: var(--ink-500); flex-wrap: wrap; }
.dc-cat { font-weight: 800; }
.dc-price { font-size: 13.5px; font-weight: 800; color: var(--ink-900); white-space: nowrap; }
.dc-go { font-size: 12px; color: var(--brand-600); font-weight: 600; }

.book-foot { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 22px; padding: 18px 22px; background: var(--ink-50); border-radius: var(--r-lg); }
.book-foot p { font-size: 12.5px; color: var(--ink-500); margin: 0; }
.link-more { color: var(--brand-600); font-weight: 700; font-size: 13.5px; }

@media (max-width: 900px) {
  .book-hero { grid-template-columns: 1fr; }
  .bh-side { flex-direction: row; align-items: center; }
  .bh-price { flex: 1; }
}
</style>
