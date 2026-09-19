<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { planById, MALL_PLANS } from './mock.js'
import { planShopApi, catalogApi, favApi } from '../../api/index.js'
import { auth } from '../../stores/auth.js'

const route = useRoute()
const router = useRouter()

// 方案详情：GET /api/plan-products/{id}（返回 {plan, related}），未命中/失败回退演示方案
const plan = ref(planById(route.params.id))
const notFound = ref(false)
const rawDetail = ref(null)

// 后端 plan 记录 → 页面契约
function toPlanView(raw) {
  const itin = Array.isArray(raw.itinerary) ? raw.itinerary : []
  return {
    id: raw.id,
    name: raw.title || raw.name,
    category: raw.category || '',
    city: raw.city || '',
    days: raw.days || itin.length || 1,
    pace: raw.pace_zh ? raw.pace_zh.replace('节奏', '') : (raw.pace || ''),
    rating: raw.rating || 4.8,
    poi: raw.poi_count || (itin.reduce((n, d) => n + (d.blocks || []).length, 0)) || 0,
    sold: raw.sales || 0,
    perPrice: raw.per_price ?? raw.price_total ?? 0,
    oldPrice: raw.original_per_price && raw.original_per_price > (raw.per_price || 0) ? raw.original_per_price : null,
    emoji: (raw.cover && raw.cover.emoji) || '🧭',
    gradient: (raw.cover && raw.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)',
    badges: raw.badges || [],
    intro: raw.intro || raw.subtitle || '',
    include: raw.include || [],
    exclude: raw.exclude || [],
    pickup: raw.pickup || '',
    refund: raw.refund_policy || '',
    // 团期：后端无静态团期字段，生成未来 4 个团期占位（可订 90 天）
    dates: genDates(),
    dayLines: itin.map(d => ({
      day: d.day,
      title: (raw.day_titles && raw.day_titles[d.day - 1]) || `第 ${d.day} 天`,
      spots: (d.blocks || []).map(b => (b.product && b.product.name) || b.tag || '').filter(Boolean),
    })),
    grounding: [],
    productIds: (itin.flatMap(d => (d.blocks || []).map(b => b.product && b.product.id))).filter(Boolean),
  }
}
function genDates() {
  const out = []
  const base = new Date()
  for (let i = 1; out.length < 4 && i < 90; i++) {
    const d = new Date(base.getTime() + i * 86400000)
    if (d.getDay() === 5 || d.getDay() === 6) {
      const zh = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
      const left = 3 + Math.floor(Math.random() * 8)
      out.push({ d: `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} 周${zh}`, left, tight: left <= 4 })
    }
  }
  return out.length ? out : [{ d: '近期团期', left: 8, tight: false }]
}

/* sku / 日期 / 人数 */
const sku = ref('标准版 · 一价全包')
const SKU_OPTS = ref([
  { key: '标准版 · 一价全包', delta: 0, note: '含行程内全部门票住宿正餐', label: '标准整订' },
  { key: '轻装版 · 不含餐', delta: -260, note: '住宿门票全含,正餐自理', label: '轻装版' },
  { key: '尊享版 · 专车专导', delta: +680, note: '专车接送 + 私人导游全程', label: '尊享版' },
])
const skuMeta = computed(() => SKU_OPTS.value.find(s => s.key === sku.value) || SKU_OPTS.value[0])
const dateIdx = ref(0)
const people = ref(2)
const total = computed(() => (plan.value.perPrice + skuMeta.value.delta) * Math.max(people.value, plan.value.minPersons || 1))

const liked = ref(false)
const shareTip = ref('')
const step = ref(1)   // 三步流程高亮
const similar = ref([])
function mockSimilar() {
  similar.value = MALL_PLANS.filter(p => p.id !== route.params.id && (p.city === plan.value.city || p.category === plan.value.category)).slice(0, 3)
}

async function load() {
  notFound.value = false
  try {
    const res = await planShopApi.detail(route.params.id)
    const raw = res.plan
    rawDetail.value = raw
    plan.value = toPlanView(raw)
    plan.value.minPersons = raw.min_persons || 2
    people.value = raw.min_persons || 2
    // 套餐种类：后端 plan_skus 派生（标准整订 / 纯玩不含宿 / 单房差 / 儿童价）
    const skus = raw.skus || []
    if (skus.length) {
      SKU_OPTS.value = skus.map(sk => ({
        key: sk.sku_id,
        delta: Number(sk.price || 0) - Number(raw.per_price || 0),
        note: sk.note || sk.spec || '',
        label: sk.label || sk.sku_id,
      }))
      sku.value = (skus.find(sk => sk.default) || skus[0]).sku_id
    }
    // 同类推荐：接口直接给 related
    if (Array.isArray(res.related) && res.related.length) {
      similar.value = res.related.map(r => ({
        id: r.id, name: r.name || r.title, city: r.city, days: r.days,
        rating: r.rating, perPrice: r.per_price,
        emoji: (r.cover && r.cover.emoji) || '🧭',
        gradient: (r.cover && r.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)',
      }))
    }
  } catch (e) {
    if (e.status === 404) notFound.value = true
    plan.value = planById(route.params.id) // 兜底演示方案
    mockSimilar()
  }
  // 收藏状态：真实拉取（未登录为空）
  try {
    const favs = await favApi.list()
    const ids = (favs && favs.product_ids) || (favs && favs.items && favs.items.map(x => x.product_id || x.id)) || []
    liked.value = ids.includes(route.params.id)
  } catch { /* 未登录忽略 */ }
  // RAG 语料背书：真实 grounding（ terms=城市+品类+标签 ）
  try {
    const terms = [plan.value.city, plan.value.category, ...(plan.value.dayLines.flatMap(d => d.spots).slice(0, 4))].filter(Boolean)
    const g = await catalogApi.ground(terms)
    plan.value.grounding = (g && g.items || []).map(x => x.source || x.title || x.knowledge_source || '').filter(Boolean).slice(0, 5)
  } catch { /* 无背书则留空 */ }
  // 同类推荐：同城 / 同品类
  try {
    const res = await planShopApi.list({ city: plan.value.city, page: 1, page_size: 8 })
    let rows = (res && res.items) || []
    if (rows.length < 3) {
      const res2 = await planShopApi.list({ category: plan.value.category, page: 1, page_size: 8 })
      rows = [...rows, ...((res2 && res2.items) || [])]
    }
    similar.value = rows.filter(p => p.id !== route.params.id).slice(0, 3).map(raw => ({
      id: raw.id, name: raw.title || raw.name, city: raw.city, days: raw.days,
      rating: raw.rating, perPrice: raw.per_price,
      emoji: (raw.cover && raw.cover.emoji) || '🧭',
      gradient: (raw.cover && raw.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)',
    }))
  } catch { /* 忽略 */ }
}
onMounted(load)
watch(() => route.params.id, load)

async function toggleFav() {
  if (!auth.isLogin) { router.push('/auth?redirect=' + encodeURIComponent(route.fullPath)); return }
  try {
    const res = await favApi.toggle(route.params.id)
    liked.value = !!res.liked
  } catch (e) { liked.value = !liked.value }
}

/* 分享：复制方案链接 */
function shareLink() {
  const url = `${location.origin}${location.pathname}#/malls/product/${plan.value.id}`
  navigator.clipboard?.writeText(url).then(() => {}, () => {})
  shareTip.value = '链接已复制'
  setTimeout(() => { shareTip.value = '' }, 2000)
}

function order() {
  router.push({ path: '/checkout', query: { plan: plan.value.id, date: plan.value.dates[dateIdx.value]?.d, people: people.value, sku: sku.value } })
}
</script>

<template>
  <div class="pd-view">
    <div class="container">

      <nav class="crumbs">
        <RouterLink to="/">首页</RouterLink> ›
        <RouterLink to="/malls">方案馆</RouterLink> ›
        <span>{{ plan.name }}</span>
      </nav>

      <div class="pd-hero card">
        <div class="ph-cover" :style="{ background: plan.gradient }">
          <span class="ph-emoji">{{ plan.emoji }}</span>
        </div>
        <div class="ph-main">
          <div class="ph-badges">
            <span v-for="b in plan.badges" :key="b" class="badge">{{ b }}</span>
          </div>
          <h1 class="ph-title">{{ plan.name }}</h1>
          <div class="ph-tags">
            <span class="chip chip-sm">{{ plan.category }}</span>
            <span class="chip chip-sm">{{ plan.city }}</span>
            <span class="chip chip-sm">{{ plan.days }} 天</span>
            <span class="chip chip-sm">{{ plan.pace }}节奏</span>
          </div>
          <div class="ph-stats">
            <span class="rating">★ {{ plan.rating }}</span>
            <span>{{ plan.poi }} 个停留点</span>
            <span>已售 {{ plan.sold.toLocaleString() }}</span>
          </div>
          <p class="ph-intro">{{ plan.intro }}</p>
          <div class="ph-chips">
            <span>✓ 门票食宿一价全包</span>
            <span>✓ 多日期可选</span>
            <span>✓ 未出行随时退</span>
          </div>
          <!-- 三步流程 -->
          <div class="ph-flow">
            <div v-for="n in 3" :key="n" class="pf-step" :class="{ on: step === n }" @click="step = n">
              <span class="pf-no">{{ n }}</span>
              <span>{{ ['看动线', '选日期人数', '整订出发'][n - 1] }}</span>
            </div>
          </div>
        </div>

        <aside class="ph-buy">
          <div class="pb-price">
            <b>¥{{ (plan.perPrice + skuMeta.delta).toLocaleString() }}</b>
            <s v-if="plan.oldPrice">¥{{ plan.oldPrice.toLocaleString() }}</s>
            <span>/人起</span>
          </div>
          <div class="pb-field">
            <label>套餐</label>
            <select v-model="sku">
              <option v-for="s in SKU_OPTS" :key="s.key" :value="s.key">{{ s.label || s.key }}{{ s.delta ? `(${s.delta > 0 ? '+' : ''}¥${s.delta})` : '' }}</option>
            </select>
            <p class="pb-note">{{ skuMeta.note }}</p>
          </div>
          <div class="pb-field">
            <label>出发日期</label>
            <select v-model.number="dateIdx">
              <option v-for="(d, i) in plan.dates" :key="d.d" :value="i">
                {{ d.d }} · 余 {{ d.left }} 位{{ d.tight ? ' · 余位紧张' : '' }}
              </option>
            </select>
          </div>
          <div class="pb-field">
            <label>人数</label>
            <div class="stepper">
              <button @click="people = Math.max(1, people - 1)">−</button>
              <span>{{ people }} 人</span>
              <button @click="people = Math.min(12, people + 1)">＋</button>
            </div>
          </div>
          <div class="pb-total">
            <span>整单合计</span>
            <b>¥{{ total.toLocaleString() }}</b>
          </div>
          <button class="btn btn-primary buy-btn" @click="order">立即整订</button>
          <div class="pb-row">
            <button class="pb-sub" :class="{ on: liked }" @click="toggleFav">{{ liked ? '♥ 已收藏' : '♡ 收藏' }}</button>
            <button class="pb-sub" @click="shareLink">↗ {{ shareTip || '分享' }}</button>
          </div>
          <p class="pb-guarantee">🔒 未出行可退 · 企业核验 · 平台担保交易</p>
        </aside>
      </div>

      <!-- 包含/不含 -->
      <section class="card inc-card">
        <div class="inc-col">
          <h4>✓ 一价全包</h4>
          <ul><li v-for="i in plan.include" :key="i">{{ i }}</li></ul>
        </div>
        <div class="inc-col ex">
          <h4>✕ 未包含</h4>
          <ul><li v-for="e in plan.exclude" :key="e">{{ e }}</li></ul>
        </div>
      </section>

      <!-- 每日动线 -->
      <section class="card days-card">
        <h3 class="sec-h">每日动线</h3>
        <div v-for="d in plan.dayLines" :key="d.day" class="dl-row">
          <span class="dl-day">D{{ d.day }}</span>
          <b class="dl-title">{{ d.title }}</b>
          <div class="dl-spots">
            <template v-for="(s, i) in d.spots" :key="s">
              <span class="dl-spot">{{ s }}</span>
              <span v-if="i < d.spots.length - 1" class="dl-arrow">→</span>
            </template>
          </div>
        </div>
        <div class="dg-src">
          <span class="dg-tag">RAG 语料背书</span>
          <span v-for="g in plan.grounding" :key="g" class="dg-item">{{ g }}</span>
        </div>
      </section>

      <!-- 同类推荐 -->
      <section class="similar">
        <h3 class="sec-h">同类 · 同城推荐</h3>
        <div class="sim-grid">
          <RouterLink v-for="p in similar" :key="p.id" :to="`/malls/product/${p.id}`" class="card sim-card">
            <div class="sc-cover" :style="{ background: p.gradient }"><span>{{ p.emoji }}</span></div>
            <div class="sc-body">
              <b>{{ p.name }}</b>
              <span class="sc-meta">{{ p.city }} · {{ p.days }}天 · ★{{ p.rating }}</span>
              <span class="sc-price">¥{{ p.perPrice.toLocaleString() }}/人起</span>
            </div>
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.pd-view { padding: var(--s-5) 0 var(--s-9); }
.crumbs { font-size: var(--fs-xs); color: var(--text-faint); margin-bottom: var(--s-4); display: flex; gap: 6px; }
.crumbs a { color: var(--text-3); }

.pd-hero { display: grid; grid-template-columns: 280px 1fr 300px; gap: var(--s-6); padding: var(--s-6); }
.ph-cover { border-radius: var(--r); display: flex; align-items: center; justify-content: center; min-height: 240px; }
.ph-emoji { font-size: 64px; filter: drop-shadow(0 6px 16px rgba(0,0,0,.18)); }
.ph-badges { display: flex; gap: var(--s-2); margin-bottom: var(--s-3); }
.badge { font-size: 10px; font-weight: var(--fw-bold); color: var(--accent); border: 1px solid var(--accent); padding: 2px 8px; border-radius: var(--r-sm); }
.ph-title { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; }
.ph-tags { display: flex; gap: var(--s-2); margin-top: var(--s-3); flex-wrap: wrap; }
.ph-stats { display: flex; gap: var(--s-4); margin-top: var(--s-3); font-size: var(--fs-sm); color: var(--text-3); align-items: center; }
.rating { color: #B08968; font-weight: var(--fw-bold); }
.ph-intro { margin-top: var(--s-3); font-size: var(--fs-sm); color: var(--text-2); line-height: 1.7; }
.ph-chips { display: flex; gap: var(--s-4); margin-top: var(--s-3); font-size: var(--fs-xs); color: #4C7A5A; }
.ph-flow { display: flex; gap: var(--s-2); margin-top: var(--s-5); }
.pf-step { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs); color: var(--text-3); background: var(--surface-2); padding: 6px var(--s-3); border-radius: var(--r-pill); cursor: pointer; transition: all var(--dur-1) var(--ease); }
.pf-step.on { background: var(--accent); color: #fff; }
.pf-no { width: 16px; height: 16px; border-radius: 50%; background: rgba(255,255,255,.25); display: inline-flex; align-items: center; justify-content: center; font-size: 10px; }
.pf-step:not(.on) .pf-no { background: var(--border); }

.ph-buy { border-left: 1px solid var(--border-soft); padding-left: var(--s-6); display: flex; flex-direction: column; gap: var(--s-3); }
.pb-price b { font-size: 26px; color: #B0685C; }
.pb-price s { color: var(--text-faint); margin-left: var(--s-2); font-size: var(--fs-sm); }
.pb-price span { font-size: var(--fs-xs); color: var(--text-faint); }
.pb-field label { font-size: var(--fs-xs); color: var(--text-3); display: block; margin-bottom: 4px; font-weight: var(--fw-bold); }
.pb-field select { width: 100%; }
.pb-note { font-size: 11px; color: var(--text-faint); margin-top: 3px; }
.stepper { display: flex; align-items: center; border: 1px solid var(--border); border-radius: var(--r); overflow: hidden; width: fit-content; }
.stepper button { width: 32px; height: 32px; border: none; background: var(--surface-2); cursor: pointer; font-size: 15px; color: var(--text-2); }
.stepper span { padding: 0 var(--s-4); font-size: var(--fs-sm); }
.pb-total { display: flex; justify-content: space-between; align-items: baseline; border-top: 1px dashed var(--border); padding-top: var(--s-3); }
.pb-total b { font-size: 20px; color: #B0685C; }
.buy-btn { width: 100%; }
.pb-row { display: flex; gap: var(--s-2); }
.pb-sub { flex: 1; border: 1px solid var(--border); background: transparent; border-radius: var(--r-sm); padding: 6px; font-size: var(--fs-xs); color: var(--text-3); cursor: pointer; }
.pb-sub.on { color: #B0685C; border-color: #B0685C; }
.pb-guarantee { font-size: 11px; color: var(--text-faint); text-align: center; }

.inc-card { margin-top: var(--s-4); display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-6); padding: var(--s-5) var(--s-6); }
.inc-col h4 { font-size: var(--fs-sm); margin-bottom: var(--s-3); color: #4C7A5A; }
.inc-col.ex h4 { color: var(--text-faint); }
.inc-col li { font-size: var(--fs-sm); color: var(--text-2); padding: 3px 0 3px var(--s-4); position: relative; list-style: none; }
.inc-col li::before { content: "·"; position: absolute; left: 4px; color: var(--text-faint); font-weight: bold; }

.days-card { margin-top: var(--s-4); padding: var(--s-5) var(--s-6); }
.sec-h { font-size: var(--fs-md); margin-bottom: var(--s-4); }
.dl-row { display: flex; align-items: flex-start; gap: var(--s-3); padding: var(--s-3) 0; border-bottom: 1px solid var(--border-soft); flex-wrap: wrap; }
.dl-row:last-of-type { border-bottom: none; }
.dl-day { font-weight: var(--fw-bold); color: var(--accent); flex: none; width: 34px; }
.dl-title { font-size: var(--fs-sm); flex: none; }
.dl-spots { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; flex: 1; }
.dl-spot { font-size: var(--fs-xs); background: var(--surface-2); padding: 3px 10px; border-radius: var(--r-pill); color: var(--text-2); }
.dl-arrow { color: var(--text-faint); font-size: 10px; }
.dg-src { margin-top: var(--s-4); padding-top: var(--s-4); border-top: 1px dashed var(--border); display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; }
.dg-tag { font-size: 10px; font-weight: var(--fw-bold); color: var(--accent-3, #7B8DA0); border: 1px solid var(--accent-3, #7B8DA0); border-radius: var(--r-sm); padding: 1px 6px; }
.dg-item { font-size: var(--fs-xs); color: var(--text-faint); background: var(--surface-2); padding: 2px 8px; border-radius: var(--r-sm); }

.similar { margin-top: var(--s-6); }
.sim-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--s-4); }
.sim-card { overflow: hidden; text-decoration: none; transition: all var(--dur-1) var(--ease); }
.sim-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.sc-cover { height: 110px; display: flex; align-items: center; justify-content: center; font-size: 34px; }
.sc-body { padding: var(--s-4); }
.sc-body b { font-size: var(--fs-sm); display: block; color: var(--text); }
.sc-meta { font-size: var(--fs-xs); color: var(--text-faint); display: block; margin: 4px 0; }
.sc-price { font-size: var(--fs-sm); color: #B0685C; font-weight: var(--fw-bold); }

@media (max-width: 960px) { .pd-hero { grid-template-columns: 1fr; } .ph-buy { border-left: none; padding-left: 0; border-top: 1px solid var(--border-soft); padding-top: var(--s-4); } .inc-card { grid-template-columns: 1fr; } }
</style>
