<template>
  <div class="container cat-page">
    <!-- 面包屑 -->
    <nav class="crumbs">
      <router-link :to="{ name: 'home' }">首页</router-link>
      <span>/</span>
      <router-link :to="{ name: 'malls' }">标品商城</router-link>
      <span>/</span>
      <span class="crumb-now">{{ pageTitle }}</span>
    </nav>

    <!-- 分类 Hero -->
    <section v-if="category" class="cat-hero" :style="{ '--cat-c': category.color }">
      <div class="hero-info">
        <div class="hero-icon">{{ category.emoji }}</div>
        <div>
          <h1>{{ category.name }}</h1>
          <p>{{ category.desc }}</p>
          <div class="meta-row">
            <span>共 <b>{{ total }}</b> 件标品</span>
            <span v-if="categoryKey">· 当前筛选 <b>{{ filteredCount }}</b> 件</span>
          </div>
        </div>
      </div>
    </section>
    <section v-else class="cat-hero cat-hero-search">
      <div class="hero-info">
        <div class="hero-icon">🔍</div>
        <div>
          <h1>搜索 "{{ kw }}"</h1>
          <p>匹配标品名 / 标签 / 城市 / 描述</p>
          <div class="meta-row">命中 <b>{{ total }}</b> 件</div>
        </div>
      </div>
    </section>

    <!-- 主区：工具栏 + 网格 -->
    <div class="cat-body">
      <!-- 工具栏 -->
      <div class="toolbar card">
        <div class="toolbar-row">
          <div class="seg">
            <button v-for="s in SORTS" :key="s.key"
                    :class="['seg-item', { active: sort === s.key }]"
                    @click="sort = s.key">{{ s.label }}</button>
          </div>
          <div class="price-input">
            <span>价格</span>
            <input type="number" v-model.number="priceMin" placeholder="不限" min="0" />
            <em>—</em>
            <input type="number" v-model.number="priceMax" placeholder="不限" min="0" />
            <button class="btn btn-sm" @click="applyAll">应用</button>
          </div>
        </div>
        <div class="toolbar-row">
          <span class="filter-label">城市</span>
          <button v-for="c in cities" :key="c"
                  :class="['chip-outline', { active: city === c }]"
                  @click="city = (city === c ? '' : c)">{{ c }}</button>
          <span class="divider"></span>
          <span class="filter-label">标签</span>
          <button v-for="b in badges" :key="b"
                  :class="['chip-outline', { active: badge === b }]"
                  @click="badge = (badge === b ? '' : b)">{{ b }}</button>
          <button v-if="city || badge || priceMin || priceMax || sort !== 'default' || kw"
                  class="btn btn-ghost btn-sm" @click="resetAll">重置筛选</button>
        </div>
      </div>

      <!-- 网格 / 骨架 / 空态 -->
      <div v-if="loading" class="grid">
        <div v-for="i in 8" :key="i" class="prod-card sk">
          <div class="sk-cover"></div>
          <div class="sk-body">
            <div class="sk-line w70"></div>
            <div class="sk-line w40"></div>
            <div class="sk-line w60"></div>
          </div>
        </div>
      </div>

      <div v-else-if="!items.length" class="empty">
        <div class="empty-illu">📦</div>
        <p class="empty-title">{{ emptyTitle }}</p>
        <p class="empty-desc">{{ emptyDesc }}</p>
        <div class="empty-actions">
          <button class="btn btn-primary" @click="resetAll">重置筛选条件</button>
          <router-link :to="{ name: 'malls' }" class="btn btn-soft">回到商城首页</router-link>
        </div>
      </div>

      <div v-else class="grid">
        <router-link v-for="p in items" :key="p.id"
                     :to="{ name: 'malls-product', params: { id: p.id } }"
                     class="prod-card card card-hover">
          <div class="prod-cover" :style="{ background: p.cover.gradient }">
            <span class="prod-emoji">{{ p.cover.emoji }}</span>
            <div class="prod-badges">
              <span v-for="b in p.badges" :key="b" class="bd">{{ b }}</span>
            </div>
          </div>
          <div class="prod-body">
            <div class="prod-cat">{{ p.category }} · {{ p.city }}</div>
            <div class="prod-name">{{ p.name }}</div>
            <div class="prod-tags">
              <span v-for="t in (p.tags || []).slice(0, 3)" :key="t" class="tg">{{ t }}</span>
            </div>
            <div class="prod-meta">
              <span class="rating">★ {{ p.rating?.toFixed(1) || '-' }}</span>
              <span class="sales">售 {{ formatSales(p.sales || 0) }}</span>
              <span v-if="p.level && p.level !== '-'" class="level">{{ p.level }}</span>
            </div>
            <div class="prod-price">
              <span v-if="p.price_min === 0" class="price-free">免费 / 含套餐</span>
              <template v-else>
                <span class="y">¥</span>
                <span class="price">{{ p.price_min }}</span>
                <span v-if="p.price_max > p.price_min" class="price-suffix"> 起</span>
              </template>
              <span v-if="p.free_shipping" class="free-ship">包邮</span>
            </div>
          </div>
        </router-link>
      </div>

      <!-- 分页 -->
      <nav v-if="totalPages > 1" class="pager">
        <button class="btn btn-sm" :disabled="page <= 1" @click="page--">‹ 上一页</button>
        <span class="pager-info">第 <b>{{ page }}</b> / {{ totalPages }} 页 · 共 {{ total }} 件</span>
        <button class="btn btn-sm" :disabled="page >= totalPages" @click="page++">下一页 ›</button>
      </nav>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsApi } from '../../api'
import { toast } from '../../composables/toast'

const route = useRoute()
const router = useRouter()

const SORTS = [
  { key: 'default',    label: '综合' },
  { key: 'sales',      label: '销量' },
  { key: 'rating',     label: '评分' },
  { key: 'price_asc',  label: '价低' },
  { key: 'price_desc', label: '价高' },
  { key: 'newest',     label: '最新' },
]

const categoryKey = computed(() => {
  if (route.name === 'malls-category') return route.params.key || ''
  return ''
})
const kw = computed(() => {
  if (route.name === 'malls-search') return String(route.query.q || '').trim()
  return ''
})

const categories = ref([])
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)
const sort = ref('default')
const city = ref('')
const badge = ref('')
const priceMin = ref(null)
const priceMax = ref(null)

const category = computed(() => categories.value.find(c => c.name === categoryKey.value) || null)
const pageTitle = computed(() => {
  if (route.name === 'malls-search') return `搜索: ${kw.value}`
  return category.value?.name || '全部分类'
})
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const filteredCount = computed(() => total.value)

const cities = computed(() => {
  const set = new Set(items.value.map(p => p.city).filter(Boolean))
  return Array.from(set).slice(0, 8)
})
const badges = computed(() => {
  const set = new Set()
  items.value.forEach(p => (p.badges || []).forEach(b => set.add(b)))
  return Array.from(set).slice(0, 6)
})

const emptyTitle = computed(() => {
  if (route.name === 'malls-search') return `没有找到与 "${kw.value}" 相关的标品`
  return '当前分类下暂无已上架标品'
})
const emptyDesc = computed(() => '试试调整筛选条件，或浏览其他分类')

function formatSales(n) { return n >= 10000 ? (n / 10000).toFixed(1) + 'w' : String(n) }

async function loadCats() {
  try {
    const r = await productsApi.categories()
    if (r?.categories?.length) categories.value = r.categories.map(c => ({ ...c, name: c.name || c.key }))
  } catch {}
}

async function loadList() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize, sort: sort.value }
    if (categoryKey.value) params.category = categoryKey.value
    if (city.value) params.city = city.value
    if (badge.value) params.badge = badge.value
    if (priceMin.value != null && priceMin.value !== '') params.price_min = priceMin.value
    if (priceMax.value != null && priceMax.value !== '') params.price_max = priceMax.value
    if (kw.value) params.keyword = kw.value
    const r = await productsApi.list(params)
    items.value = r.items || []
    total.value = r.total || 0
  } catch (e) {
    items.value = []
    total.value = 0
    if (route.name !== 'malls-search') {
      toast('商品列表加载失败：' + (e.message || e), 'err')
    }
  } finally {
    loading.value = false
  }
}

function applyAll() { page.value = 1; loadList() }
function resetAll() {
  sort.value = 'default'; city.value = ''; badge.value = ''
  priceMin.value = null; priceMax.value = null
  if (route.name === 'malls-search') {
    router.push({ name: 'malls' })
    return
  }
  page.value = 1
  loadList()
}

watch(() => [categoryKey.value, kw.value], () => { page.value = 1; loadList() })
watch(sort, () => { page.value = 1; loadList() })
watch(page, loadList)

onMounted(async () => {
  await loadCats()
  await loadList()
})
</script>

<style scoped>
.cat-page { padding-top: 24px; padding-bottom: 80px; }
.crumbs { font-size: 13px; color: var(--ink-500); margin-bottom: 18px; display: flex; gap: 8px; align-items: center; }
.crumbs a { color: var(--ink-500); text-decoration: none !important; }
.crumbs a:hover { color: var(--brand-600); }
.crumb-now { color: var(--ink-900); font-weight: 700; }

.cat-hero {
  padding: 28px 32px; border-radius: var(--r-xl);
  background: linear-gradient(135deg, var(--cat-c, var(--brand-500)) 0%, var(--brand-700) 100%);
  color: #fff; margin-bottom: 22px;
}
.hero-info { display: flex; gap: 18px; align-items: center; }
.hero-icon { font-size: 56px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.18)); flex: none; }
.hero-info h1 { font-size: 28px; font-weight: 900; margin: 0; letter-spacing: -.02em; }
.hero-info p { font-size: 14px; margin: 4px 0 0; opacity: .85; }
.meta-row { margin-top: 10px; font-size: 13.5px; opacity: .9; }
.meta-row b { font-weight: 800; }
.cat-hero-search { background: linear-gradient(135deg, #6366F1, #2563EB); }

.toolbar { padding: 14px 18px; margin-bottom: 18px; display: flex; flex-direction: column; gap: 10px; }
.toolbar-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.seg { display: inline-flex; gap: 4px; padding: 4px; background: var(--ink-50); border-radius: 9px; }
.seg-item { padding: 6px 14px; border: none; background: transparent; color: var(--ink-500); border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all .15s; }
.seg-item.active { background: #fff; color: var(--brand-700); box-shadow: var(--shadow-sm); }
.price-input { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; color: var(--ink-500); margin-left: auto; }
.price-input input { width: 80px; padding: 5px 8px; border-radius: 6px; border: 1px solid var(--ink-200); font-size: 13px; }
.filter-label { font-size: 13px; color: var(--ink-500); font-weight: 600; }
.chip-outline { background: transparent; border: 1px solid var(--ink-200); color: var(--ink-700); padding: 3px 12px; border-radius: 999px; font-size: 12.5px; cursor: pointer; transition: all .15s; }
.chip-outline:hover { border-color: var(--brand-500); color: var(--brand-700); }
.chip-outline.active { background: var(--brand-50); border-color: var(--brand-500); color: var(--brand-700); font-weight: 700; }
.divider { width: 1px; height: 18px; background: var(--ink-200); margin: 0 6px; }

.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.prod-card { padding: 0; overflow: hidden; text-decoration: none !important; transition: all .18s; display: flex; flex-direction: column; }
.prod-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.prod-cover { aspect-ratio: 4/3; display: flex; align-items: center; justify-content: center; position: relative; }
.prod-emoji { font-size: 80px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.18)); }
.prod-badges { position: absolute; left: 10px; top: 10px; display: flex; gap: 4px; flex-wrap: wrap; }
.bd { background: rgba(0,0,0,.45); color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 4px; backdrop-filter: blur(6px); }
.prod-body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 5px; flex: 1; }
.prod-cat { font-size: 11.5px; color: var(--ink-400); }
.prod-name { font-weight: 700; font-size: 14.5px; color: var(--ink-900); min-height: 2.8em; line-height: 1.4; }
.prod-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.tg { font-size: 11px; padding: 1px 8px; background: var(--ink-50); color: var(--ink-500); border-radius: 999px; }
.prod-meta { display: flex; gap: 8px; font-size: 11.5px; color: var(--ink-500); align-items: center; margin-top: auto; }
.prod-meta .rating { color: var(--accent-600); font-weight: 700; }
.prod-meta .level { padding: 1px 6px; background: var(--brand-50); color: var(--brand-700); border-radius: 4px; font-weight: 600; }
.prod-price { display: flex; align-items: baseline; gap: 3px; margin-top: 4px; }
.prod-price .y { font-size: 13px; color: var(--danger); font-weight: 700; }
.prod-price .price { font-size: 22px; color: var(--danger); font-weight: 900; }
.prod-price .price-suffix { font-size: 12px; color: var(--ink-500); }
.prod-price .price-free { font-size: 14px; color: var(--ok); font-weight: 800; }
.free-ship { margin-left: auto; background: var(--ok-bg); color: var(--ok); font-size: 11px; padding: 1px 6px; border-radius: 4px; font-weight: 700; }

/* 骨架 */
.sk { pointer-events: none; }
.sk-cover { aspect-ratio: 4/3; background: linear-gradient(90deg, var(--ink-100) 0%, var(--ink-50) 50%, var(--ink-100) 100%); background-size: 200% 100%; animation: shine 1.4s infinite linear; }
.sk-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
.sk-line { height: 12px; background: var(--ink-100); border-radius: 4px; animation: shine 1.4s infinite linear; background: linear-gradient(90deg, var(--ink-100) 0%, var(--ink-50) 50%, var(--ink-100) 100%); background-size: 200% 100%; }
.sk-line.w40 { width: 40%; }
.sk-line.w60 { width: 60%; }
.sk-line.w70 { width: 70%; height: 16px; }
@keyframes shine { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* 空态 */
.empty { padding: 80px 0; text-align: center; color: var(--ink-500); }
.empty-illu { font-size: 80px; opacity: .35; margin-bottom: 14px; }
.empty-title { font-size: 16px; font-weight: 700; color: var(--ink-700); margin: 0; }
.empty-desc { font-size: 13.5px; margin: 6px 0 22px; }
.empty-actions { display: inline-flex; gap: 10px; }

.pager { display: flex; justify-content: center; align-items: center; gap: 14px; padding: 28px 0; }
.pager-info { font-size: 13px; color: var(--ink-500); }
.pager-info b { color: var(--ink-900); font-weight: 800; }

@media (max-width: 980px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 540px) { .grid { grid-template-columns: 1fr; } .hero-info h1 { font-size: 22px; } .hero-icon { font-size: 42px; } }
</style>
