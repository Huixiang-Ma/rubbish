<template>
  <div class="browse">
    <section class="top">
      <div class="container top-inner">
        <div class="top-copy">
          <h1 class="page-title">
            <template v-if="mode==='theme'">「{{ activeKey }}」线路方案</template>
            <template v-else-if="mode==='city'">在 {{ queryCity }} 玩，这些方案已排好</template>
            <template v-else-if="mode==='keyword'">「{{ queryQ }}」的搜索结果</template>
            <template v-else>线路方案馆</template>
          </h1>
          <p class="page-sub">
            游客挑一条线路 = 打包整订整段假期：每日动线、门票食宿都在里面。<br v-if="false">
            标品素材由企业排好动线、整体报价，不用再一张张凑门票车票。
          </p>
        </div>
        <form class="kbar card" @submit.prevent="doSearch">
          <span>🔍</span>
          <input v-model.trim="kw" class="kinput" placeholder="城市 / 主题 / 线路关键词" />
          <button class="btn btn-primary btn-sm">搜索</button>
        </form>
      </div>
    </section>

    <section class="container body">
      <div class="filterbar card">
        <div class="fgroup">
          <span class="fg-label">城市</span>
          <div class="chips">
            <button class="chip" :class="{ on: !queryCity }" @click="setCity('')">全部</button>
            <button v-for="c in cats.cities" :key="c.name" class="chip" :class="{ on: queryCity===c.name }"
                    @click="setCity(c.name)">{{ c.name }}<i class="cnt">{{ c.count }}</i></button>
          </div>
        </div>
        <div class="fgroup">
          <span class="fg-label">玩法</span>
          <div class="chips">
            <button class="chip" :class="{ on: !queryCat }" @click="setCategory('')">全部</button>
            <button v-for="t in cats.themes" :key="t.name" class="chip" :class="{ on: queryCat===t.name }"
                    @click="setCategory(t.name)">{{ t.emoji }} {{ t.name }}<i class="cnt">{{ t.count }}</i></button>
          </div>
        </div>
        <div class="fgroup">
          <span class="fg-label">节奏</span>
          <div class="chips">
            <button class="chip" :class="{ on: !pace }" @click="setPace('')">全部</button>
            <button v-for="(p, i) in PACES" :key="p.key" class="chip" :class="{ on: pace===p.key }" @click="setPace(p.key)">{{ p.name }}</button>
          </div>
        </div>
        <div class="sort-line">
          <span class="count">共 {{ total }} 条方案</span>
          <select v-model="sort" class="select sort" @change="load(true)">
            <option value="">综合排序</option>
            <option value="sales">销量优先</option>
            <option value="rating">好评优先</option>
            <option value="price_asc">价格从低到高</option>
            <option value="price_desc">价格从高到低</option>
            <option value="days">天数由短到长</option>
          </select>
        </div>
      </div>

      <div v-if="loading && !plans.length" class="center">
        <div class="spinner"></div>
      </div>

      <template v-else>
        <div v-if="!plans.length" class="empty card">
          <div class="empty-emoji">🧳</div>
          <div class="empty-title">还没有匹配的方案</div>
          <p class="empty-desc">换一个城市或玩法试试；也可以直接用「行程规划」说一句话，让企业现场给你排</p>
          <router-link :to="{ name: 'my-plans', query: { new: 1 } }" class="btn btn-primary">✦ 去规划一条</router-link>
        </div>

        <div v-else class="grid">
          <router-link v-for="p in plans" :key="p.id"
                       :to="{ name: 'malls-product', params: { id: p.id } }"
                       class="shop-card card">
            <PhotoCover :cover="p.cover" :photos="p.photos || []">
              <span class="days-chip">{{ p.days }} 日 / {{ p.pace_zh }}</span>
              <div class="shop-badges">
                <span v-for="b in p.badges" :key="b" class="bd">{{ b }}</span>
              </div>
            </PhotoCover>
            <div class="shop-body">
              <div class="shop-top">
                <span class="shop-cat">{{ p.category }}</span>
                <span class="shop-city">📍{{ p.city }}</span>
              </div>
              <div class="shop-name">{{ p.name }}</div>
              <div class="shop-sub">{{ p.subtitle }}</div>
              <div class="shop-meta">
                <span class="rating">★ {{ Number(p.rating).toFixed(1) }}</span>
                <span>{{ p.poi_count }} 个点位</span>
                <span>已售 {{ p.sales }}</span>
              </div>
              <div class="shop-foot">
                <div class="shop-price">
                  <span class="y">¥</span><b>{{ p.per_price }}</b>
                  <span class="suffix">/人 · 整订</span>
                  <s v-if="p.original_per_price > p.per_price" class="p-orig">¥{{ p.original_per_price }}</s>
                </div>
                <span class="buy">查看行程 →</span>
              </div>
            </div>
          </router-link>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { planShopApi, svcApi } from '../../api'
import PhotoCover from '../../components/PhotoCover.vue'

const route = useRoute()
const router = useRouter()
const PACES = [
  { key: 'leisure', name: '悠闲' }, { key: 'standard', name: '标准' }, { key: 'compact', name: '紧凑' },
]

const cats = reactive({ themes: [], cities: [], total: 0 })
const plans = ref([])
const total = ref(0)
const loading = ref(true)
const kw = ref('')
const queryCat = ref('')
const queryCity = ref('')
const queryQ = ref('')
const pace = ref('')
const sort = ref('')
const mode = ref('all')
const activeKey = ref('')

function fromRoute() {
  activeKey.value = String(route.params.key || '')
  queryCity.value = String(route.query.city || '')
  queryQ.value = String(route.query.q || '')
  if (activeKey.value) mode.value = 'theme'
  else if (queryCity.value) mode.value = 'city'
  else if (queryQ.value) mode.value = 'keyword'
  else mode.value = 'all'
  // 搜索词带进顶部输入框
  kw.value = route.query.q ? String(route.query.q) : ''
}

function param() {
  return {
    category: queryCat.value || undefined,
    city: (route.query.city ? String(route.query.city) : queryCity.value) || undefined,
    keyword: (route.query.q ? String(route.query.q) : kw.value) || undefined,
    pace: pace.value || undefined,
    sort: sort.value || undefined,
    page_size: 60,
  }
}

async function loadPhotos() {
  for (const p of plans.value.slice(0, 12)) {
    try {
      const r = await svcApi.planPhotos(p.city, '')
      if (r.photos && r.photos.length) p.photos = r.photos
    } catch { /* 无图回落 emoji */ }
  }
}

async function load(reset = true) {
  loading.value = true
  try {
    const [r, c] = await Promise.allSettled([planShopApi.list(param()), planShopApi.categories()])
    if (r.status === 'fulfilled') {
      plans.value = r.value.items || []
      total.value = r.value.total || 0
    }
    if (c.status === 'fulfilled') {
      cats.themes = (c.value.themes || []).filter(t => t.count > 0)
      cats.cities = (c.value.cities || []).filter(t => t.count > 0)
      cats.total = c.value.total || 0
    }
  } finally { loading.value = false }
  loadPhotos()
}

function setCity(v) {
  queryCat.value = ''; pace.value = ''
  router.replace({ name: 'malls-search', query: v ? { city: v } : {} })
}
function setCategory(v) {
  queryCat.value = v; pace.value = ''
  router.replace(v ? { name: 'malls-category', params: { key: v } } : { name: 'malls' })
}
function setPace(v) { pace.value = v; load(true) }
function doSearch() {
  const q = kw.value.trim()
  router.replace({ name: 'malls-search', query: q ? { q } : {} })
}

watch(() => route.fullPath, () => { fromRoute(); load(true) })
onMounted(() => { fromRoute(); load(true) })
</script>

<style scoped>
.browse { padding-bottom: 40px; }
.top { padding: 44px 0 28px; background: radial-gradient(800px 300px at 80% 0%, rgba(224,138,60,.10), transparent 60%); }
.top-inner { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; flex-wrap: wrap; }
.page-title { font-size: 28px; font-weight: 900; color: var(--ink-900); letter-spacing: -.02em; margin: 0; }
.page-sub { color: var(--ink-500); font-size: 14px; margin-top: 8px; max-width: 560px; line-height: 1.7; }
.kbar {
  display: flex; align-items: center; gap: 8px; padding: 8px 8px 8px 16px; min-width: 340px;
  box-shadow: 0 6px 20px rgba(15,23,42,.06);
}
.kinput { flex: 1; border: none; outline: none; background: none; font-size: 14px; }
.body { margin-top: 20px; }
.filterbar { padding: 14px 18px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 18px; }
.fgroup { display: flex; align-items: center; gap: 12px; }
.fg-label { font-size: 12.5px; color: var(--ink-500); font-weight: 700; flex: none; width: 44px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-flex; align-items: center; gap: 4px; padding: 5px 12px; font-size: 13px; color: var(--ink-600);
  background: var(--ink-50); border: 1px solid var(--ink-200); border-radius: 999px; cursor: pointer; transition: all .14s;
}
.chip:hover { border-color: var(--brand-500); color: var(--brand-700); }
.chip.on { background: var(--brand-600); border-color: var(--brand-600); color: #fff; font-weight: 700; }
.chip .cnt { font-size: 10.5px; opacity: .65; font-style: normal; }
.chip.on .cnt { opacity: .8; }
.sort-line { display: flex; justify-content: space-between; align-items: center; gap: 12px; border-top: 1px dashed var(--ink-200); padding-top: 10px; }
.count { font-size: 12.5px; color: var(--ink-400); }
.sort { min-width: 150px; }
.center { display: flex; justify-content: center; padding: 80px 0; }
.empty { text-align: center; padding: 60px 20px; }
.empty-emoji { font-size: 52px; }
.empty-title { font-weight: 800; font-size: 18px; color: var(--ink-900); margin-top: 10px; }
.empty-desc { color: var(--ink-500); font-size: 14px; margin: 8px 0 18px; }

.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.shop-card { padding: 0; overflow: hidden; transition: all .18s; text-decoration: none !important; }
.shop-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.shop-cover { aspect-ratio: 4/3; position: relative; display: flex; align-items: center; justify-content: center; }
.shop-emoji { font-size: 72px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.16)); }
.days-chip { position: absolute; left: 10px; top: 10px; background: rgba(0,0,0,.48); color: #fff; font-size: 11px; padding: 3px 9px; border-radius: 999px; backdrop-filter: blur(6px); }
.shop-badges { position: absolute; right: 10px; top: 10px; display: flex; gap: 4px; }
.shop-badges .bd { background: rgba(255,255,255,.92); color: var(--brand-800); font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 4px; }
.shop-body { padding: 14px 16px 15px; }
.shop-top { display: flex; justify-content: space-between; align-items: center; }
.shop-cat { font-size: 11.5px; color: var(--brand-700); font-weight: 700; background: var(--brand-50); padding: 2px 8px; border-radius: 4px; }
.shop-city { font-size: 11.5px; color: var(--ink-400); }
.shop-name { font-weight: 800; font-size: 15px; color: var(--ink-900); margin-top: 7px; line-height: 1.35; }
.shop-sub { font-size: 12.5px; color: var(--ink-500); margin-top: 3px; line-height: 1.5; min-height: 2.4em; }
.shop-meta { display: flex; gap: 12px; font-size: 12px; color: var(--ink-400); margin-top: 8px; }
.rating { color: var(--accent-600); font-weight: 700; }
.shop-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 9px; }
.shop-price { display: flex; align-items: baseline; gap: 2px; }
.shop-price .y { font-size: 13px; font-weight: 700; color: var(--danger); }
.shop-price b { font-size: 22px; font-weight: 900; color: var(--danger); }
.shop-price .suffix { font-size: 11.5px; color: var(--ink-400); }
.p-orig { font-size: 12px; color: var(--ink-400); margin-left: 5px; }
.buy { font-size: 12.5px; color: var(--brand-600); font-weight: 700; white-space: nowrap; }

@media (max-width: 1080px) { .grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 860px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 520px) { .grid { grid-template-columns: 1fr; } .kbar { min-width: 0; width: 100%; } .top-inner { flex-direction: column; align-items: stretch; } }
</style>
