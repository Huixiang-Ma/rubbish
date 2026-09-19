<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { planShopApi } from '../api/index.js'

const route = useRoute()
const kw = ref('')
const sort = ref('推荐排序')
const theme = ref('全部主题')
const days = ref('不限天数')
const price = ref('不限价格')
const loading = ref(false)

const themes = ref(['全部主题'])
const dayOpts = ['不限天数','1-2 天','3-4 天','5-7 天','8 天以上']
const priceOpts = ['不限价格','¥1000 以下','¥1000-2000','¥2000-4000','¥4000 以上']
const sorts = ['推荐排序','价格 低到高','价格 高到低','最新上架']

// 真实分页
const currentPage = ref(1)
const pageSize = 9
const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))
const pagedPlans = computed(() => filtered.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize))
function goToPage(n) {
  if (n < 1 || n > totalPages.value) return
  currentPage.value = n
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// 城市实拍封面（素材库覆盖不到的城市沿用内置图，避免空封面）
const CITY_COVERS = {
  '苏州': '/covers/c1043.jpg', '杭州': '/covers/s_hangzhou1.jpg', '大理': '/covers/c1015.jpg',
  '成都': '/covers/c342.jpg', '厦门': '/covers/c154.jpg', '西安': '/covers/s_xian1.jpg',
  '北京': '/covers/s_chengdu1.jpg', '南京': '/covers/s_lake1.jpg',
}

// 后端 plan-product → 卡片契约（接口：GET /api/plan-products）
function toCard(raw = {}) {
  return {
    id: raw.id,
    city: raw.city || '',
    title: raw.name || raw.title || '',
    tag: raw.category || raw.theme || '自由行',
    days: raw.days || 1,
    price: Number(raw.per_price) || 0,
    oldPrice: raw.original_per_price && raw.original_per_price > (raw.per_price || 0) ? raw.original_per_price : null,
    stock: (raw.stock ?? 0) > 8 ? '充足' : (raw.stock ?? 0) > 0 ? '紧张' : '候补',
    people: `${raw.min_persons || 2}-${(raw.min_persons || 2) + 4}人`,
    photo: CITY_COVERS[raw.city] || '',
    cover: raw.cover || null,
  }
}

// 兜底演示数据（后端不可用时保持页面可渲染）
const FALLBACK = [
  { city: '苏州', title: '园林三日 · 拙政留园', tag: '园林水巷', days: 3, price: 1280, oldPrice: 1480, stock: '充足', people: '2-6人', photo: '/covers/c1043.jpg' },
  { city: '杭州', title: '西湖人文四日',         tag: '湖山人文', days: 4, price: 1680, oldPrice: null, stock: '紧张', people: '2-8人', photo: '/covers/s_xiamen1.jpg' },
  { city: '大理', title: '苍洱五日 · 白族家访',   tag: '湖山人文', days: 5, price: 2280, oldPrice: 2580, stock: '充足', people: '2-4人', photo: '/covers/c1015.jpg' },
  { city: '成都', title: '美食四日 · 熊猫基地',   tag: '美食烟火', days: 4, price: 1880, oldPrice: null, stock: '充足', people: '2-8人', photo: '/covers/c342.jpg' },
  { city: '厦门', title: '鼓浪屿三日 · 骑楼海岛', tag: '海岛度假', days: 3, price: 1480, oldPrice: 1680, stock: '充足', people: '2-6人', photo: '/covers/c154.jpg' },
  { city: '西安', title: '长安古都四日',         tag: '古都历史', days: 4, price: 1580, oldPrice: null, stock: '紧张', people: '2-8人', photo: '/covers/s_xian1.jpg' },
]

const plans = ref(FALLBACK)

onMounted(async () => {
  // 首页城市卡入口：/malls?city=苏州；搜索入口：/malls?kw=园林
  if (route.query.city) kw.value = String(route.query.city)
  if (route.query.kw) kw.value = String(route.query.kw)
  // 主题 chips：真实类目动态渲染（GET /api/plan-products/categories）
  try {
    const cats = await planShopApi.categories()
    const names = (cats && (cats.themes || [])) ? cats.themes.map(t => t.name || t) : []
    if (names.length) themes.value = ['全部主题', ...names]
  } catch { /* 保持默认 */ }
  loading.value = true
  try {
    const res = await planShopApi.list({ page: 1, page_size: 60 })
    const items = (res && res.items) || []
    if (items.length) plans.value = items.map(toCard)
  } catch { /* 后端不可用时保留兜底数据 */ }
  loading.value = false
})

const filtered = computed(() => {
  currentPage.value = 1
  const dayMatch = (d) =>
    days.value === '不限天数' ? true :
    days.value === '1-2 天' ? d <= 2 :
    days.value === '3-4 天' ? d >= 3 && d <= 4 :
    days.value === '5-7 天' ? d >= 5 && d <= 7 : d >= 8
  const priceMatch = (p) =>
    price.value === '不限价格' ? true :
    price.value === '¥1000 以下' ? p < 1000 :
    price.value === '¥1000-2000' ? p >= 1000 && p <= 2000 :
    price.value === '¥2000-4000' ? p > 2000 && p <= 4000 : p > 4000
  const kwHit = (x) => !kw.value || (x.title + x.city + x.tag).includes(kw.value.trim())
  const list = plans.value.filter(p =>
    (theme.value === '全部主题' || p.tag === theme.value) &&
    dayMatch(p.days) && priceMatch(p.price) && kwHit(p))
  const sorters = {
    '价格 低到高': (a, b) => a.price - b.price,
    '价格 高到低': (a, b) => b.price - a.price,
    '最新上架': (a, b) => String(b.id).localeCompare(String(a.id)),
  }
  return sorters[sort.value] ? [...list].sort(sorters[sort.value]) : list
})
</script>

<template>
  <div class="malls">
    <div class="container-wide">

      <!-- 页头 -->
      <header class="page-head">
        <div>
          <span class="eyebrow">方案馆</span>
          <h1 class="page-title">挑一份你的下一段旅程</h1>
          <p class="page-sub">{{ plans.length }} 份精选方案 · 一价全包 · 可随时改</p>
        </div>
        <div class="search-bar">
          <svg class="icon" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input v-model="kw" class="search-input" placeholder="搜索城市 / 主题 / 线路" />
        </div>
      </header>

      <!-- 筛选 -->
      <section class="filters card">
        <div class="filter-row">
          <span class="filter-label">主题</span>
          <div class="chip-group">
            <button v-for="t in themes" :key="t" class="chip chip-sm"
                    :class="{ active: theme === t }" @click="theme = t">{{ t }}</button>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">天数</span>
          <div class="chip-group">
            <button v-for="d in dayOpts" :key="d" class="chip chip-sm"
                    :class="{ active: days === d }" @click="days = d">{{ d }}</button>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">价格</span>
          <div class="chip-group">
            <button v-for="p in priceOpts" :key="p" class="chip chip-sm"
                    :class="{ active: price === p }" @click="price = p">{{ p }}</button>
          </div>
          <div class="row gap-2 ml-auto">
            <span class="t-3 t-sm">排序:</span>
            <select v-model="sort" class="select-mini">
              <option v-for="s in sorts" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>
        </div>
      </section>

      <!-- 卡片栅格 -->
      <section class="plan-grid">
        <article v-for="(p, i) in pagedPlans" :key="p.title" class="plan card card-hover anim-fade-up" :class="`delay-${(i%4)+1}`">
          <!-- 封面(统一实拍图,素材库无图时用主题色渐变兜底) -->
          <div class="cover">
            <img v-if="p.photo" class="cover-img" :src="p.photo" :alt="p.title" loading="lazy" />
            <div v-else class="cover-img cover-fallback" :style="{ background: (p.cover && p.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)' }">
              <span class="cover-emoji">{{ (p.cover && p.cover.emoji) || '🧭' }}</span>
            </div>
            <div class="cover-shade"></div>
            <div class="cover-badges">
              <span class="tag tag-accent-2">{{ p.tag }}</span>
              <span v-if="p.oldPrice" class="tag tag-danger">限时优惠</span>
            </div>
          </div>

          <!-- 内容 -->
          <div class="plan-body">
            <div class="row gap-2 t-3 t-xs">
              <span>{{ p.city }}</span>
              <span>·</span>
              <span>{{ p.days }} 天</span>
              <span>·</span>
              <span>{{ p.people }}</span>
            </div>
            <h3 class="plan-title">{{ p.title }}</h3>
            <p class="plan-desc">整单方案含门票、餐饮、住宿、大交通,企业核验素材,可改可退。</p>

            <div class="row gap-2 mt-3">
              <span class="tag" :class="p.stock === '紧张' ? 'tag-warn' : 'tag-ok'">团期{{ p.stock }}</span>
              <span class="tag tag-info">含大交通</span>
              <span class="tag tag-accent">一价全包</span>
            </div>

            <div class="plan-foot">
              <div class="price-block">
                <div class="price-row">
                  <span class="price-yen">¥</span>
                  <span class="price">{{ p.price.toLocaleString() }}</span>
                  <span class="price-unit">/ 人起</span>
                </div>
                <div v-if="p.oldPrice" class="price-old">原价 ¥{{ p.oldPrice.toLocaleString() }}</div>
              </div>
              <RouterLink :to="`/malls/product/${p.id}`" class="btn btn-primary btn-sm">查看详情</RouterLink>
            </div>
          </div>
        </article>
      </section>

      <!-- 分页 -->
      <nav class="pager mt-7">
        <button class="btn btn-ghost btn-sm" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">← 上一页</button>
        <div class="page-num">
          <button v-for="n in totalPages" :key="n" class="page-btn" :class="{ active: n === currentPage }" @click="goToPage(n)">{{ n }}</button>
        </div>
        <button class="btn btn-ghost btn-sm" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">下一页 →</button>
      </nav>
    </div>
  </div>
</template>

<style scoped>
.malls { padding: var(--s-7) 0 var(--s-9); }

/* —— 页头 —— */
.page-head {
  display: flex; justify-content: space-between; align-items: flex-end;
  gap: var(--s-5); margin-bottom: var(--s-6);
  flex-wrap: wrap;
}
.page-title { font-size: var(--fs-3xl); margin-top: var(--s-3); font-weight: var(--fw-bold); }
.page-sub { color: var(--text-3); margin-top: var(--s-2); font-size: var(--fs-sm); }

.search-bar {
  display: flex; align-items: center; gap: var(--s-3);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-pill); padding: var(--s-2) var(--s-5);
  min-width: 320px;
  transition: border-color var(--dur-2) var(--ease), box-shadow var(--dur-2) var(--ease);
}
.search-bar:focus-within { border-color: var(--text-3); box-shadow: var(--shadow-sm); }
.search-bar .icon { color: var(--text-3); }
.search-input {
  flex: 1; height: 40px; padding: 0; border: 0; background: transparent;
  font-size: var(--fs-base); color: var(--text);
}
.search-input:focus { outline: none; }
.search-input::placeholder { color: var(--text-faint); }

/* —— 筛选 —— */
.filters { padding: var(--s-5) var(--s-6); margin-bottom: var(--s-6); }
.filter-row {
  display: flex; align-items: center; gap: var(--s-4);
  padding: var(--s-3) 0;
  border-bottom: 1px solid var(--border-soft);
}
.filter-row:last-child { border-bottom: 0; }
.filter-label {
  width: 56px; flex-shrink: 0;
  font-size: var(--fs-xs); color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.1em; font-weight: var(--fw-medium);
}
.chip-group { display: flex; flex-wrap: wrap; gap: var(--s-2); flex: 1; }

.select-mini {
  height: 32px; padding: 0 var(--s-3);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--r);
  font-size: var(--fs-sm); color: var(--text);
  cursor: pointer;
}
.select-mini:hover { border-color: var(--border-strong); }
.select-mini:focus { outline: none; border-color: var(--text); }

/* —— 卡片栅格 —— */
.plan-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: var(--s-5);
}
.plan { padding: 0; overflow: hidden; display: flex; flex-direction: column; }
.cover {
  position: relative;
  aspect-ratio: 12/5;
  overflow: hidden;
}
.cover-img {
  width: 100%; height: 100%; object-fit: cover; display: block;
  transition: transform .7s var(--ease);
}
.cover-fallback { display: flex; align-items: center; justify-content: center; }
.cover-emoji { font-size: 44px; opacity: .9; }
.card-hover:hover .cover-img { transform: scale(1.05); }
.cover-shade {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(180deg, rgba(31,29,26,.05) 0%, rgba(31,29,26,0) 38%, rgba(31,29,26,.14) 100%);
}
.cover-badges {
  position: absolute; top: var(--s-3); left: var(--s-3);
  display: flex; gap: var(--s-2);
}

.plan-body {
  padding: var(--s-4) var(--s-5) var(--s-5);
  display: flex; flex-direction: column; gap: var(--s-2);
  flex: 1;
}
.plan-title {
  font-size: var(--fs-md); font-weight: var(--fw-semi); margin-top: var(--s-2);
  letter-spacing: -0.005em;
}
.plan-desc {
  font-size: var(--fs-sm); color: var(--text-2);
  line-height: var(--lh-base);
  margin-top: var(--s-2);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}

.plan-foot {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: auto; padding-top: var(--s-4);
  border-top: 1px solid var(--border-soft);
}
.price-block { display: flex; flex-direction: column; gap: 2px; }
.price-row { display: flex; align-items: baseline; gap: 2px; }
.price-yen { font-size: var(--fs-sm); color: var(--accent-2); font-weight: var(--fw-medium); }
.price { font-size: var(--fs-xl); font-weight: var(--fw-bold); color: var(--accent-2); letter-spacing: -0.01em; }
.price-unit { font-size: var(--fs-xs); color: var(--text-3); margin-left: 2px; }
.price-old { font-size: var(--fs-xs); color: var(--text-faint); text-decoration: line-through; }

/* —— 分页 —— */
.pager { display: flex; align-items: center; justify-content: center; gap: var(--s-3); }
.page-num { display: flex; gap: var(--s-1); align-items: center; }
.page-btn {
  min-width: 32px; height: 32px; padding: 0 var(--s-2);
  background: transparent; border: 1px solid transparent;
  border-radius: var(--r-sm); font-size: var(--fs-sm);
  color: var(--text-2); cursor: pointer;
  transition: all var(--dur-1) var(--ease);
}
.page-btn:hover { color: var(--text); background: var(--surface); border-color: var(--border); }
.page-btn.active {
  background: var(--text); color: var(--text-on-dark); border-color: var(--text);
}

.ml-auto { margin-left: auto; }

@media (max-width: 1000px) {
  .plan-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .plan-grid { grid-template-columns: 1fr; }
  .page-head { flex-direction: column; align-items: flex-start; }
  .search-bar { width: 100%; }
  .filter-row { flex-wrap: wrap; }
  .filter-label { width: 100%; }
}
</style>
