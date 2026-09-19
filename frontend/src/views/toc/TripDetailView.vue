<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { tripById, catMeta } from './mock.js'
import { tripsStore } from '../../stores/trips.js'
import { planShopApi } from '../../api/index.js'
import { auth } from '../../stores/auth.js'

const route = useRoute()
tripsStore.load()
// 本地行程书优先（AI 规划沉淀 / 手动组装），无则回退演示行程
const trip = computed(() => tripsStore.byId(route.params.id) || tripById(route.params.id))

/* toB 上架为方案：把本行程一键转成方案馆在售线路（staff 专属入口） */
const listOpen = ref(false)
const listForm = ref({ title: '', city: '', days: 3, per_price: 0 })
const listBusy = ref(false)
const listMsg = ref('')
function openListing() {
  const t = trip.value
  listForm.value = {
    title: t.title, city: t.city || '苏州', days: t.days || 3,
    per_price: Math.max(199, Math.ceil((t.budget || t.days * 580) / Math.max(1, t.people || 2) * 1.3 / 10) * 10),
  }
  listOpen.value = true
}
async function submitListing() {
  if (listBusy.value) return
  listBusy.value = true
  listMsg.value = ''
  try {
    const f = listForm.value
    const res = await planShopApi.create({
      title: `${f.city}${f.days}日 · 顾问定制线路`, city: f.city, category: '定制线路',
      days: Math.min(7, f.days), per_price: Number(f.per_price) || 0,
      original_per_price: Math.round((Number(f.per_price) || 0) * 1.15),
      min_persons: trip.value.people || 2, stock: 20,
      subtitle: `${f.days} 日把 ${f.city} 安排明白，行程经过实战检验`,
      badges: ['顾问定制', '实战线路'],
    })
    listMsg.value = `已上架：${res.name || res.title || ''}`
    setTimeout(() => { listOpen.value = false; listMsg.value = '' }, 1200)
  } catch (e) {
    listMsg.value = e.message || '上架失败'
  } finally { listBusy.value = false }
}

const priceOf = (p) => (p > 0 ? `¥${p}` : '免费')
</script>

<template>
  <div class="trip-detail">
    <div class="container">

      <!-- 行程书头 -->
      <header class="book-hero card">
        <div class="hero-cover">
          <img src="/covers/c1043.jpg" :alt="trip.title" />
        </div>
        <div class="hero-main">
          <div class="hero-tags">
            <span class="tag tag-accent">{{ trip.days }} 天</span>
            <span class="tag tag-accent-2">{{ trip.theme }}</span>
            <span class="tag">{{ trip.pace }}节奏</span>
            <span class="tag">2 人出行</span>
          </div>
          <h1 class="hero-title">{{ trip.title }}</h1>
          <div class="hero-meta">
            <span>📅 {{ trip.date }} 出发</span>
            <span>📍 {{ trip.city }}</span>
            <span>🧩 {{ trip.stops }} 个停留点</span>
            <span>🗂 {{ trip.cats }} 个品类</span>
          </div>
          <p class="hero-note">行程书由「{{ trip.template }}」模板生成后手动调整,价格与营业信息来自企业核验素材。</p>
        </div>
        <aside class="hero-aside">
          <div class="price-box">
            <div class="pb-label">模板参考价</div>
            <div class="pb-val">¥{{ trip.budget.toLocaleString() }}</div>
            <div class="pb-delta">{{ trip.delta }}</div>
          </div>
          <div class="hero-btns">
            <button v-if="auth.isStaff" class="btn btn-ghost btn-sm" @click="openListing">💼 上架为方案</button>
            <RouterLink :to="`/trip/${trip.id}/map`" class="btn btn-primary btn-sm">查看动线图</RouterLink>
            <RouterLink :to="`/trip/${trip.id}/edit`" class="btn btn-ghost btn-sm">编辑行程</RouterLink>
            <RouterLink to="/malls/product/p101" class="btn btn-ghost btn-sm">一键下单</RouterLink>
          </div>
        </aside>
      </header>

      <!-- 逐日行程 -->
      <section v-for="d in trip.dayPlans" :key="d.day" class="day-book card">
        <div class="day-head">
          <span class="day-no">D{{ d.day }}</span>
          <div class="day-info">
            <h2 class="day-title">{{ d.title }}</h2>
            <p class="day-summary">{{ d.summary }}</p>
          </div>
          <div class="day-stat">
            <span>{{ d.items.length }} 个点位</span>
            <span>约 {{ Math.round(d.items.reduce((s, i) => s + parseFloat(i.stop.dwell), 0) * 10) / 10 }}h 游览</span>
          </div>
        </div>

        <div class="day-rows">
          <div v-for="(it, idx) in d.items" :key="idx" class="row-item">
            <div class="row-time">
              <span class="rt-txt">{{ it.time }}</span>
              <span class="rt-slot">{{ it.stop.slot === 'night' && it.stop.cat === '住宿' ? '宿' : catMeta(it.stop.cat).emoji }}</span>
            </div>
            <div class="tl-line">
              <span class="tl-dot" :style="{ background: catMeta(it.stop.cat).color }"></span>
              <span v-if="idx < d.items.length - 1" class="tl-bar"></span>
            </div>
            <div class="row-stop">
              <div class="stop-head">
                <b class="stop-name">{{ it.stop.name }}</b>
                <span class="stop-cat" :style="{ color: catMeta(it.stop.cat).color, background: catMeta(it.stop.cat).soft }">{{ it.stop.cat }}</span>
                <span class="stop-rating">★ {{ it.stop.rating }}</span>
              </div>
              <p class="stop-note">{{ it.stop.note }}</p>
              <div class="stop-meta">
                <span>⏱ {{ it.stop.dwell }}</span>
                <span>💰 {{ priceOf(it.stop.price) }}</span>
                <span>📍 {{ it.stop.city }}</span>
                <RouterLink to="/malls" class="stop-link">看同类素材 →</RouterLink>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer class="book-foot">
        <RouterLink to="/plans" class="btn btn-ghost">← 返回我的行程</RouterLink>
        <RouterLink :to="`/trip/${trip.id}/map`" class="btn btn-primary">查看每日动线与 24h 时间线</RouterLink>
      </footer>
    </div>
  </div>

    <!-- 上架为方案（staff） -->
    <div v-if="listOpen" class="modal-mask" @click.self="listOpen = false">
      <div class="card list-modal">
        <h3>上架为在售方案</h3>
        <div class="lf-field">
          <span>方案标题</span>
          <input v-model.trim="listForm.title" class="input" />
        </div>
        <div class="lf-field">
          <span>城市</span>
          <input v-model.trim="listForm.city" class="input" />
        </div>
        <div class="lf-row">
          <div class="lf-field" style="flex:1">
            <span>天数</span>
            <input v-model.number="listForm.days" type="number" min="1" max="7" class="input" />
          </div>
          <div class="lf-field" style="flex:1">
            <span>人均价（成本×1.3 建议）</span>
            <input v-model.number="listForm.per_price" type="number" class="input" />
          </div>
        </div>
        <p class="lf-tip">行程将按 {{ listForm.city }} 素材库自动编排上架，上架后立即进入方案馆与 RAG 推荐池。</p>
        <p v-if="listMsg" class="lf-msg">{{ listMsg }}</p>
        <div class="lf-btns">
          <button class="btn btn-ghost btn-sm" @click="listOpen = false">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="listBusy" @click="submitListing">{{ listBusy ? '上架中…' : '确认上架' }}</button>
        </div>
      </div>
    </div>
</template>

<style scoped>
.trip-detail { padding: var(--s-7) 0 var(--s-9); }
.container { display: flex; flex-direction: column; gap: var(--s-5); }

/* hero */
.book-hero { display: flex; gap: var(--s-6); padding: var(--s-6); }
.hero-cover { width: 120px; height: 120px; border-radius: var(--r-md); overflow: hidden; flex: none; }
.hero-cover img { width: 100%; height: 100%; object-fit: cover; }
.hero-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--s-3); }
.hero-tags { display: flex; gap: var(--s-2); flex-wrap: wrap; }
.hero-title { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; }
.hero-meta { display: flex; gap: var(--s-5); font-size: var(--fs-sm); color: var(--text-2); flex-wrap: wrap; }
.hero-note { font-size: var(--fs-sm); color: var(--text-3); line-height: var(--lh-base); }
.hero-aside { width: 240px; flex: none; display: flex; flex-direction: column; gap: var(--s-3); }
.price-box { background: var(--surface-2); border: 1px solid var(--border-soft); border-radius: var(--r-md); padding: var(--s-4); }
.pb-label { font-size: var(--fs-xs); color: var(--text-3); }
.pb-val { font-size: var(--fs-2xl); font-weight: var(--fw-bold); color: var(--accent-2); margin-top: var(--s-1); letter-spacing: -0.01em; }
.pb-delta { font-size: var(--fs-xs); color: var(--text-3); margin-top: var(--s-1); }
.hero-btns { display: flex; flex-direction: column; gap: var(--s-2); }
.hero-btns .btn { width: 100%; }

/* day book */
.day-book { padding: var(--s-5) var(--s-6) var(--s-6); }
.day-head { display: flex; align-items: flex-start; gap: var(--s-4); padding-bottom: var(--s-4); border-bottom: 1px solid var(--border-soft); }
.day-no { width: 44px; height: 44px; border-radius: var(--r); background: var(--accent-soft); color: var(--accent); font-weight: var(--fw-bold); font-size: var(--fs-md); display: inline-flex; align-items: center; justify-content: center; flex: none; }
.day-info { flex: 1; }
.day-title { font-size: var(--fs-lg); font-weight: var(--fw-semi); }
.day-summary { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-3); line-height: var(--lh-base); }
.day-stat { display: flex; flex-direction: column; gap: var(--s-1); font-size: var(--fs-xs); color: var(--text-faint); text-align: right; }

.day-rows { display: flex; flex-direction: column; }
.row-item { display: flex; gap: var(--s-4); padding: var(--s-4) 0; }
.row-time { width: 104px; flex: none; display: flex; flex-direction: column; gap: var(--s-1); align-items: flex-end; padding-top: 2px; }
.rt-txt { font-size: var(--fs-xs); color: var(--text-2); font-variant-numeric: tabular-nums; }
.rt-slot { font-size: var(--fs-xs); color: var(--text-faint); }
.tl-line { width: 16px; flex: none; display: flex; flex-direction: column; align-items: center; }
.tl-dot { width: 10px; height: 10px; border-radius: 50%; flex: none; margin-top: 4px; box-shadow: 0 0 0 3px var(--surface); }
.tl-bar { width: 1.5px; flex: 1; background: var(--border); margin-top: 2px; }
.row-stop { flex: 1; min-width: 0; }
.stop-head { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.stop-name { font-size: var(--fs-base); font-weight: var(--fw-semi); }
.stop-cat { font-size: var(--fs-xs); padding: 1px var(--s-2); border-radius: var(--r-sm); font-weight: var(--fw-medium); }
.stop-rating { font-size: var(--fs-xs); color: var(--accent-2); font-weight: var(--fw-medium); }
.stop-note { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); line-height: var(--lh-base); }
.stop-meta { display: flex; gap: var(--s-4); margin-top: var(--s-2); font-size: var(--fs-xs); color: var(--text-3); flex-wrap: wrap; }
.stop-link { color: var(--accent-3); transition: color var(--dur-1) var(--ease); }
.stop-link:hover { color: var(--accent); }

.book-foot { display: flex; justify-content: space-between; padding-top: var(--s-2); }

@media (max-width: 900px) {
  .book-hero { flex-direction: column; }
  .hero-aside { width: 100%; }
  .hero-btns { flex-direction: row; }
  .hero-btns .btn { width: auto; flex: 1; }
}
@media (max-width: 640px) {
  .row-time { width: 84px; }
  .day-stat { display: none; }
}
.lf-field { display: flex; flex-direction: column; gap: 5px; margin-bottom: var(--s-3); }
.lf-field span { font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--text-2); }
.lf-field .input { height: 38px; border: 1px solid var(--border); border-radius: var(--r); padding: 0 var(--s-3); }
.lf-row { display: flex; gap: var(--s-3); }
.lf-tip { font-size: var(--fs-xs); color: var(--text-3); margin: 0 0 var(--s-3); }
.lf-msg { font-size: var(--fs-xs); color: #5C7A9D; margin: 0 0 var(--s-3); }
.lf-btns { display: flex; justify-content: flex-end; gap: var(--s-2); }
.list-modal { width: min(440px, 92vw); padding: var(--s-6); max-height: 82vh; overflow: auto; }
.modal-mask { position: fixed; inset: 0; background: rgba(46,44,40,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
</style>
