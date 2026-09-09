<template>
  <div class="container map-page">
    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>行程地图加载中…</div>

    <template v-else-if="!trip">
      <div class="empty card big"><div class="icon">🗺</div><p>没有找到这份行程书，可能已被删除</p>
        <div class="act"><router-link :to="{ name: 'my-plans' }" class="btn btn-primary">返回我的行程</router-link></div>
      </div>
    </template>

    <template v-else>
      <!-- 头 -->
      <div class="mp-head">
        <div class="mp-hl">
          <router-link :to="{ name: 'trip-detail', params: { id: trip.id } }" class="mp-back">← 行程书</router-link>
          <h1 class="mp-title">{{ trip.title }}</h1>
          <div class="mp-sub">
            {{ trip.city }} · {{ trip.days }} 天<template v-if="rangeText"> · 📅 {{ rangeText }}</template>
            <span class="mp-sub-stop">{{ totalBlocks }} 个停留（{{ withCoord }} 个可定位）</span>
          </div>
        </div>
        <div class="mp-acts">
          <router-link :to="{ name: 'trip-edit', params: { id: trip.id } }" class="btn btn-ghost btn-sm">✏️ 就地编辑</router-link>
          <router-link :to="{ name: 'malls' }" class="btn btn-ghost btn-sm">🛍 标品商城</router-link>
        </div>
      </div>

      <!-- 双视图切换 -->
      <div class="mp-tabs">
        <button class="tab" :class="{ on: view === 'map' }" @click="view = 'map'">🗺 路线图</button>
        <button class="tab" :class="{ on: view === 'timeline' }" @click="view = 'timeline'">📅 24 小时时间线</button>
      </div>

      <!-- ============ 视图一：逐日路线地图 ============ -->
      <div v-show="view === 'map'" class="mp-map">
        <div v-if="warnNoCoord" class="mp-warn">⚠️ 部分停留点是旧版本保存的，缺少坐标；已按标品库回查，仍无坐标的条目不会出现在地图上（时间线不受影响）。</div>
        <div class="mp-toolbar">
          <button class="chip" :class="{ on: dayFilter === 0 }" @click="dayFilter = 0">全部</button>
          <button v-for="d in trip.dayPlans" :key="d.day" class="chip" :class="{ on: dayFilter === d.day }"
                  :style="dayFilter === d.day ? { borderColor: dayColor(d.day), color: dayColor(d.day) } : {}"
                  @click="dayFilter = d.day">第 {{ d.day }} 天</button>
          <span class="mp-note">点序号 = 当日停留顺序 · 城际「交通」不入图 · 距离为示意比例</span>
        </div>
        <div ref="mapEl" class="mp-canvas"></div>
        <div v-if="withCoord < 2" class="mp-map-empty">可定位停留点不足 2 个，无法绘制逐日路线——可切到「24 小时时间线」查看，或回行程书重新编排补充有坐标的标品。</div>
        <div v-else class="mp-legend">
          <span v-for="d in trip.dayPlans" :key="'l' + d.day" class="lg-item">
            <i :style="{ background: dayColor(d.day) }"></i>第 {{ d.day }} 天
          </span>
        </div>
      </div>

      <!-- ============ 视图二：24 小时时间线 ============ -->
      <div v-show="view === 'timeline'" class="mp-tl">
        <div class="tl-ruler">
          <span v-for="m in RULER" :key="m" :style="{ left: (m / 1440) * 100 + '%' }">{{ rulerLabel(m) }}</span>
        </div>
        <section v-for="d in trip.dayPlans" :key="'tl' + d.day" class="tl-day">
          <header class="tl-head">
            <div class="tl-dayno">{{ d.day }}</div>
            <div class="tl-titles">
              <div class="tl-title">第 {{ d.day }} 天 <em v-if="dayDate(d.day)">{{ dayDate(d.day) }}</em></div>
              <div class="tl-sub">{{ daySummary(d) }}</div>
            </div>
            <div class="tl-legend">
              <span v-for="c in dayCats(d)" :key="c.name" class="lc-item">
                <i :style="{ background: c.color }"></i>{{ c.name }}
              </span>
            </div>
          </header>
          <div class="tl-lane">
            <div class="tl-grid"><i v-for="m in RULER" :key="'g' + m" :style="{ left: (m / 1440) * 100 + '%' }"></i></div>
            <div v-for="b in tlBars(d)" :key="b.key"
                 class="tl-bar" :style="{ left: b.left + '%', width: b.width + '%', background: b.bg, borderColor: b.color }"
                 :title="b.name + '（' + b.periodZh + ' ' + b.time + '）'">
              <span class="tb-time">{{ b.time }}</span>
              <span class="tb-emoji">{{ b.emoji }}</span>
              <span class="tb-name">{{ b.name }}<em v-if="b.tag"> · {{ b.tag }}</em></span>
            </div>
          </div>
        </section>
        <p class="mp-foot">条带宽度按停留时段折算到 24 小时，夜宿跨零点按至当日 24:00 展示；餐饮/夜宿标注为该停留建议时段。</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { useTripStore, tripDateRange } from '../../composables/tripStore'
import { productsApi } from '../../api'

const route = useRoute()
const store = useTripStore()

const CATS = [
  { name: '景点', color: '#0EA5E9' }, { name: '餐饮', color: '#F59E0B' },
  { name: '住宿', color: '#8B5CF6' }, { name: '交通', color: '#10B981' },
  { name: '购物', color: '#EC4899' }, { name: '文化', color: '#6366F1' },
]
const CAT_COLOR = Object.fromEntries(CATS.map(c => [c.name, c.color]))
const DAY_COLORS = ['#0EA5E9', '#F59E0B', '#8B5CF6', '#10B981', '#EC4899', '#6366F1', '#F97316']
const SLOT = {
  morning:  { zh: '上午', start: '08:30', dur: 3 },
  midday:   { zh: '午餐', start: '11:30', dur: 2 },
  afternoon:{ zh: '下午', start: '14:00', dur: 3.5 },
  evening:  { zh: '晚间', start: '17:30', dur: 2.5 },
  night:    { zh: '夜宿', start: '21:00', dur: 12 },
}
const RULER = [0, 360, 720, 1080, 1440] // 00:00 / 06:00 / 12:00 / 18:00 / 24:00

const trip = ref(null)
const loading = ref(true)
const view = ref('map')
const dayFilter = ref(0)

const catalog = ref([])       // 标品全量，用于旧数据 coords 回查
const coordsMap = ref(new Map())
const missingCount = ref(0)

const rangeText = computed(() => (trip.value ? tripDateRange(trip.value) : ''))
const totalBlocks = computed(() => (trip.value?.dayPlans || []).reduce((s, d) => s + d.blocks.length, 0))

function dayColor(d) { return DAY_COLORS[(Number(d) - 1) % DAY_COLORS.length] }
function catColor(c) { return CAT_COLOR[c] || '#64748B' }
function fmtYMD(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
function dayDate(day) {
  const s = trip.value && trip.value.start_date
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(String(s))) return ''
  const dt = new Date(`${s}T00:00:00`)
  if (Number.isNaN(dt.getTime())) return ''
  dt.setDate(dt.getDate() + (Number(day) || 1) - 1)
  return fmtYMD(dt)
}

// —— 坐标解析：块坐标 = 快照 coords > 标品库回查 > 无 ——
const blocksFlat = computed(() => {
  const out = []
  for (const d of trip.value?.dayPlans || []) {
    ;(d.blocks || []).forEach((b, bi) => {
      const p = b.product || {}
      let coords = (Array.isArray(p.coords) && p.coords.length === 2) ? p.coords : null
      if (!coords) coords = coordsMap.value.get(p.id) || null
      out.push({ day: d.day, bi, key: b.key || `${d.day}_${bi}`, period: b.period, start: b.start, tag: b.tag || '', p })
      if (coords) out[out.length - 1].coords = coords
    })
  }
  return out
})

// 本地地图点（剔除城际交通 & 无坐标）
const localPts = computed(() =>
  blocksFlat.value.filter(x => x.p.category !== '交通' && x.coords))
const withCoord = computed(() => localPts.value.length)
const warnNoCoord = computed(() =>
  blocksFlat.value.some(x => x.p.category !== '交通' && !x.coords))

// —— ECharts 封装（带 notMerge 强刷） ——
const mapEl = ref(null)
const chart = ref(null)
let ro = null

function drawMap() {
  if (!mapEl.value) return
  if (!chart.value) {
    chart.value = echarts.init(mapEl.value)
    ro = new ResizeObserver(() => chart.value?.resize())
    ro.observe(mapEl.value)
  }
  chart.value.setOption(mapOption(), true)
}

function mapOption() {
  const days = trip.value.dayPlans || []
  const visible = localPts.value.filter(x => !dayFilter.value || x.day === dayFilter.value)
  const byDay = new Map()
  visible.forEach(x => {
    if (!byDay.has(x.day)) byDay.set(x.day, [])
    byDay.get(x.day).push(x)
  })

  const series = []
  const lg = visible.length
  if (lg >= 2) {
    // 墨卡托近似投影（km），保证 x/y 同尺度
    const lats = visible.map(x => x.coords[1])
    const lngs = visible.map(x => x.coords[0])
    const midLat = (Math.min(...lats) + Math.max(...lats)) / 2
    const midLng = (Math.min(...lngs) + Math.max(...lngs)) / 2
    const kmLng = Math.cos((midLat * Math.PI) / 180) * 110.6
    const pts = visible.map(x => ({ ...x, X: (x.coords[0] - midLng) * kmLng, Y: (x.coords[1] - midLat) * 110.6 }))

    const xs = pts.map(p => p.X); const ys = pts.map(p => p.Y)
    const W = mapEl.value.clientWidth || 800
    const H = mapEl.value.clientHeight || 460
    const availX = W - 60; const availY = H - 96
    const sx = Math.max(...xs) - Math.min(...xs)
    const sy = Math.max(...ys) - Math.min(...ys)
    const kmPerPx = Math.max((sx || 1) / availX, (sy || 1) / availY, 0.05)
    const midX = (Math.min(...xs) + Math.max(...xs)) / 2
    const midY = (Math.min(...ys) + Math.max(...ys)) / 2
    const axisX = { min: midX - (availX * kmPerPx) / 2, max: midX + (availX * kmPerPx) / 2 }
    const axisY = { min: midY - (availY * kmPerPx) / 2, max: midY + (availY * kmPerPx) / 2 }

    const grouped = new Map()
    pts.forEach(p => {
      if (!grouped.has(p.day)) grouped.set(p.day, [])
      grouped.get(p.day).push(p)
    })
    const sortedDays = [...grouped.keys()].sort((a, b) => a - b)
    sortedDays.forEach(day => {
      const list = grouped.get(day)
      const color = dayColor(day)
      const data = list.map((p, i) => ({
        value: [+p.X.toFixed(4), +p.Y.toFixed(4)],
        raw: { name: p.p.name, category: p.p.category, period: p.period, tag: p.tag, day, idx: i + 1, start: p.start },
      }))
      if (list.length >= 2) {
        series.push({
          name: `第${day}天`, type: 'line', data, z: 1,
          symbol: 'none', smooth: false,
          lineStyle: { color, width: 2.2, type: 'solid', opacity: 0.9 },
        })
      }
      series.push({
        name: `第${day}天点`, type: 'scatter', data, z: 2,
        symbol: 'circle', symbolSize: 22,
        itemStyle: { color: '#fff', borderColor: color, borderWidth: 2.5 },
        label: { show: true, formatter: p => p.data.raw.idx, color, fontSize: 11, fontWeight: 800 },
        tooltip: {
          formatter: p => {
            const r = p.data.raw
            const zh = SLOT[r.period] ? SLOT[r.period].zh : r.period
            return `<b>第 ${r.day} 天 · ${zh}</b><br/>${r.name}<span style="color:#94A3B8">${r.tag ? ' · ' + r.tag : ''}</span><br/><span style="color:#94A3B8">${r.category} · 当日第 ${r.idx} 站</span>`
          },
        },
      })
    })

    return {
      animation: false,
      grid: { left: 18, right: 18, top: 10, bottom: 12, containLabel: false },
      xAxis: { type: 'value', min: axisX.min, max: axisX.max, show: false, scale: true },
      yAxis: { type: 'value', min: axisY.min, max: axisY.max, show: false, scale: true },
      tooltip: { trigger: 'item', backgroundColor: 'rgba(255,255,255,.97)', borderColor: '#E2E8F0', textStyle: { color: '#0F172A', fontSize: 12.5 }, extraCssText: 'box-shadow:0 8px 24px rgba(15,23,42,.12);border-radius:10px;padding:8px 12px' },
      series,
    }
  }
  return {
    animation: false,
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: 'value', show: false }, yAxis: { type: 'value', show: false },
    series: [],
  }
}

// —— 时间线：24h 条带 ——
function parseHM(s) {
  const m = String(s || '').match(/^(\d{1,2}):(\d{2})$/)
  return m ? Number(m[1]) * 60 + Number(m[2]) : null
}
function tlBars(d) {
  return (d.blocks || []).map((b, bi) => {
    const p = b.product || {}
    const meta = SLOT[b.period] || { zh: b.period || '', start: '10:00', dur: 2 }
    const startMin = parseHM(b.start) ?? parseHM(meta.start) ?? 600
    const endMin = Math.min(startMin + (meta.dur || 2) * 60, 1440)
    const color = catColor(p.category)
    return {
      key: b.key || `${d.day}_${bi}`,
      name: p.name || '未命名',
      tag: b.tag || '',
      time: b.start || meta.start,
      periodZh: meta.zh,
      emoji: (p.cover && p.cover.emoji) || (p.category ? { 景点: '🏛', 餐饮: '🍜', 住宿: '🏨', 交通: '🚄', 购物: '🛍', 文化: '📚' }[p.category] : '📌'),
      color,
      bg: color + '1A',
      left: ((startMin || 0) / 1440) * 100,
      width: Math.max(((endMin - (startMin || 0)) / 1440) * 100, 3.2),
    }
  })
}
function rulerLabel(m) {
  const h = m / 60
  return (h === 24 ? '24:00' : String(h).padStart(2, '0') + ':00')
}
function dayCats(d) {
  const set = new Set((d.blocks || []).map(b => b.product && b.product.category).filter(Boolean))
  return CATS.filter(c => set.has(c.name))
}
function daySummary(d) {
  const day = (d.blocks || []).filter(b => b.period !== 'night')
  const names = day.slice(0, 2).map(b => b.product && b.product.name)
  return names.length ? names.join(' → ') + (day.length > 2 ? ' 等' : '') : '自由安排'
}

// —— 加载 ——
async function load() {
  loading.value = true
  trip.value = store.get(String(route.params.id || ''))
  if (!trip.value) { loading.value = false; return }
  try {
    const r = await productsApi.list({ page_size: 200 })
    catalog.value = r.items || []
  } catch { catalog.value = [] }
  const m = new Map()
  catalog.value.forEach(p => {
    if (Array.isArray(p.coords) && p.coords.length === 2) m.set(p.id, p.coords)
  })
  coordsMap.value = m
  missingCount.value = 0
  loading.value = false
  await nextTick()
  drawMap()
}

watch(view, async v => { if (v === 'map') { await nextTick(); drawMap() } })
watch(dayFilter, () => drawMap())
watch(() => route.params.id, () => { load() })

onMounted(load)
onBeforeUnmount(() => {
  ro?.disconnect()
  chart.value?.dispose()
  chart.value = null
})
</script>

<style scoped>
.map-page { padding-top: 26px; max-width: 1060px; }
.loading-block { padding: 90px 0; text-align: center; color: var(--ink-400); }
.empty.big { padding: 80px 20px; text-align: center; }
.act { display: flex; justify-content: center; margin-top: 16px; }
.btn-ghost { background: transparent; border: 1px solid var(--ink-300); color: var(--ink-600); }
.btn-ghost:hover { border-color: var(--brand-500); color: var(--brand-600); }

.mp-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 14px; flex-wrap: wrap; margin-bottom: 6px; }
.mp-back { font-size: 13px; color: var(--ink-500); font-weight: 600; text-decoration: none; }
.mp-back:hover { color: var(--brand-600); }
.mp-title { font-size: 24px; font-weight: 900; margin: 4px 0 2px; color: var(--ink-900); letter-spacing: -.02em; }
.mp-sub { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; font-size: 13px; color: var(--ink-500); }
.mp-sub-stop { font-size: 12px; color: var(--ink-400); background: var(--ink-100); padding: 1px 9px; border-radius: 999px; }
.mp-acts { display: flex; gap: 8px; }

.mp-tabs { display: flex; gap: 6px; margin: 18px 0 12px; border-bottom: 1px solid var(--ink-200); }
.tab { border: none; background: none; font-size: 15px; font-weight: 800; color: var(--ink-500); padding: 9px 16px 11px; cursor: pointer; border-bottom: 2.5px solid transparent; }
.tab.on { color: var(--brand-600); border-bottom-color: var(--brand-500); }

/* 地图视图 */
.mp-map { background: #fff; border: 1px solid var(--ink-200); border-radius: var(--r-lg); padding: 14px 16px 16px; }
.mp-warn { background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; font-size: 12.5px; border-radius: 10px; padding: 8px 12px; margin-bottom: 12px; }
.mp-toolbar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.chip { border: 1px solid var(--ink-200); background: #fff; border-radius: 999px; padding: 4px 13px; font-size: 12.5px; font-weight: 700; color: var(--ink-600); cursor: pointer; }
.chip.on { background: var(--brand-50); border-color: var(--brand-400); color: var(--brand-700); }
.mp-note { margin-left: auto; font-size: 11.5px; color: var(--ink-400); }
.mp-canvas { width: 100%; height: 460px; border-radius: 12px; background:
  radial-gradient(560px 200px at 90% 0%, rgba(14,165,233,.05), transparent 60%),
  linear-gradient(180deg, var(--ink-50), #fff); border: 1px dashed var(--ink-200); }
.mp-map-empty { text-align: center; color: var(--ink-500); font-size: 13px; padding: 26px 12px 8px; }
.mp-legend { display: flex; gap: 14px; justify-content: center; margin-top: 12px; flex-wrap: wrap; }
.lg-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--ink-500); font-weight: 600; }
.lg-item i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }

/* 时间线视图 */
.mp-tl { background: #fff; border: 1px solid var(--ink-200); border-radius: var(--r-lg); padding: 18px 18px 6px; }
.tl-ruler { position: relative; height: 20px; margin: 0 118px 10px 0; }
.tl-ruler span { position: absolute; transform: translateX(-50%); font-family: var(--mono); font-size: 10.5px; color: var(--ink-400); }
.tl-day { margin-bottom: 20px; }
.tl-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.tl-dayno { width: 34px; height: 34px; border-radius: 10px; background: linear-gradient(135deg, var(--brand-600), var(--brand-400)); color: #fff; font-weight: 900; display: flex; align-items: center; justify-content: center; font-size: 15px; }
.tl-title { font-weight: 800; font-size: 15px; color: var(--ink-900); }
.tl-title em { font-style: normal; font-size: 12px; color: var(--ink-400); font-weight: 600; margin-left: 8px; font-family: var(--mono); }
.tl-sub { font-size: 12px; color: var(--ink-500); margin-top: 1px; }
.tl-legend { margin-left: auto; display: flex; gap: 10px; }
.lc-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--ink-500); }
.lc-item i { width: 8px; height: 8px; border-radius: 3px; }

.tl-lane { position: relative; margin-left: 46px; }
.tl-grid { position: absolute; inset: 0; }
.tl-grid i { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--ink-100); }
.tl-bar { position: absolute; top: 0; height: 44px; border-radius: 9px; border: 1px solid; display: flex; align-items: center; gap: 6px; padding: 0 8px; overflow: hidden; min-width: 0; box-sizing: border-box; }
.tb-time { font-family: var(--mono); font-size: 10.5px; color: var(--ink-500); font-weight: 700; flex: none; }
.tb-emoji { flex: none; font-size: 13px; }
.tb-name { font-size: 12.5px; font-weight: 800; color: var(--ink-800); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tb-name em { font-style: normal; color: var(--ink-400); font-weight: 600; }
.mp-foot { font-size: 12px; color: var(--ink-400); margin: 4px 0 14px 46px; }

@media (max-width: 860px) {
  .tl-legend { display: none; }
  .mp-note { display: none; }
}
</style>
