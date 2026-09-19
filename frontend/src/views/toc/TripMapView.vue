<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { tripById, catMeta, CATS, SLOTS } from './mock.js'
import { tripsStore } from '../../stores/trips.js'
import RealMapView from '../../components/RealMapView.vue'

const catList = Object.entries(CATS)

const route = useRoute()
tripsStore.load()
const trip = computed(() => tripsStore.byId(route.params.id) || tripById(route.params.id))

const view = ref('map')           // map | timeline
const activeDay = ref(-1)         // -1 = 全部

const chartEl = ref(null)
let chart = null

const stops = computed(() => {
  const out = []
  trip.value.dayPlans.forEach((d, di) => {
    d.items.forEach((it, ii) => {
      out.push({ ...it.stop, day: di + 1, idx: ii + 1, seq: `D${di + 1}·${ii + 1}` })
    })
  })
  return out
})
const shown = computed(() => activeDay.value < 0 ? stops.value : stops.value.filter(s => s.day === activeDay.value + 1))
const locatable = computed(() =>
  (activeDay.value < 0 ? stops.value : stops.value.filter(s => s.day === activeDay.value + 1))
    .filter(s => s.x != null).map(s => ({
      ...s, lat: s.y, lng: s.x,
    }))
)

function renderMap() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const groups = {}
  shown.value.forEach(s => { (groups[s.cat] = groups[s.cat] || []).push(s) })
  const series = Object.entries(groups).map(([cat, arr]) => ({
    name: cat, type: 'scatter',
    symbolSize: 16,
    itemStyle: { color: catMeta(cat).color, borderColor: '#fff', borderWidth: 2 },
    label: { show: arr.length > 0, position: 'top', fontSize: 11, color: '#5C5853', formatter: p => p.data.name },
    data: arr.map(s => ({ name: s.name, value: [s.x, s.y] })),
  }))
  chart.setOption({
    grid: { left: 24, right: 24, top: 40, bottom: 40 },
    xAxis: { show: false, min: v => v.min - 0.012, max: v => v.max + 0.012 },
    yAxis: { show: false, min: v => v.min - 0.008, max: v => v.max + 0.008 },
    tooltip: { formatter: p => `<b>${p.data.name}</b><br/>品类:${p.seriesName}` },
    legend: { top: 0, right: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { color: '#8E8A82', fontSize: 12 } },
    series,
  }, true)
}

function resize() { chart && chart.resize() }
onMounted(async () => { await nextTick(); renderMap(); window.addEventListener('resize', resize) })
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart && chart.dispose() })
watch([view, activeDay], async () => { if (view.value === 'map') { await nextTick(); renderMap() } })

/* —— 24h 时间线 —— */
const RULER = [0, 360, 720, 1080, 1440]
const fmt = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
const lanes = computed(() => trip.value.dayPlans.map(d => ({
  day: d.day, title: d.title,
  bars: d.items.map(it => {
    const s = SLOTS[it.stop.slot] || SLOTS.afternoon
    const isHotel = it.stop.cat === '住宿'
    return { stop: it.stop, left: isHotel ? 1320 : s.start, width: isHotel ? 120 : s.len, isHotel }
  }),
})))
</script>

<template>
  <div class="trip-map">
    <div class="container">

      <header class="map-head">
        <div>
          <RouterLink to="/plans" class="back">← 返回我的行程</RouterLink>
          <h1 class="map-title">{{ trip.title }} · 动线</h1>
          <p class="map-sub">
            {{ trip.city }} · {{ trip.days }} 天 · {{ trip.date }} 出发 ·
            共 {{ stops.length }} 个停留点,其中 {{ locatable.length }} 个可定位
          </p>
        </div>
        <div class="head-btns">
          <RouterLink :to="`/trip/${trip.id}/edit`" class="btn btn-ghost btn-sm">编辑行程</RouterLink>
          <RouterLink to="/malls" class="btn btn-ghost btn-sm">逛方案馆</RouterLink>
        </div>
      </header>

      <!-- 视图切换 -->
      <div class="view-tabs card">
        <button :class="{ on: view === 'map' }" @click="view = 'map'">🗺 路线图</button>
        <button :class="{ on: view === 'timeline' }" @click="view = 'timeline'">📅 24 小时时间线</button>
      </div>

      <!-- 路线图 -->
      <section v-if="view === 'map'" class="card map-card">
        <div class="day-chips">
          <button class="chip chip-sm" :class="{ active: activeDay < 0 }" @click="activeDay = -1">全部</button>
          <button v-for="(d, i) in trip.dayPlans" :key="i" class="chip chip-sm" :class="{ active: activeDay === i }" @click="activeDay = i">
            D{{ d.day }} · {{ d.title }}
          </button>
        </div>
        <RealMapView :spots="locatable" height="480px" />
        <div class="map-warn">
          <span class="warn-ico">!</span>
          无坐标停留点(部分餐饮/购物)不出现在地图中,以时间线为准。
        </div>
      </section>

      <!-- 24h 时间线 -->
      <section v-else class="tl-card card">
        <div class="ruler">
          <span v-for="r in RULER" :key="r" class="ruler-tick" :style="{ left: (r / 1440 * 100) + '%' }">{{ fmt(r) }}</span>
        </div>
        <div class="lanes">
          <div v-for="l in lanes" :key="l.day" class="lane">
            <div class="lane-head">
              <span class="lane-day">D{{ l.day }}</span>
              <span class="lane-title">{{ l.title }}</span>
            </div>
            <div class="lane-track">
              <div v-for="b in l.bars" :key="b.stop.id + b.left"
                   class="tl-bar"
                   :class="{ hotel: b.isHotel }"
                   :style="{ left: (b.left / 1440 * 100) + '%', width: Math.max(b.width / 1440 * 100, 4.5) + '%', background: catMeta(b.stop.cat).color }"
                   :title="`${b.stop.name} · ${b.stop.dwell}`">
                <span class="bar-emoji">{{ catMeta(b.stop.cat).emoji }}</span>
                <span class="bar-name">{{ b.stop.name }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="tl-legend">
          <span v-for="[k, m] in catList" :key="k" class="lg-item">
            <i :style="{ background: m.color }"></i>{{ k }}
          </span>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.trip-map { padding: var(--s-7) 0 var(--s-9); }
.container { display: flex; flex-direction: column; gap: var(--s-5); }
.map-head { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--s-4); flex-wrap: wrap; }
.back { font-size: var(--fs-xs); color: var(--text-3); transition: color var(--dur-1) var(--ease); }
.back:hover { color: var(--text); }
.map-title { font-size: var(--fs-2xl); font-weight: var(--fw-bold); margin-top: var(--s-2); letter-spacing: -0.015em; }
.map-sub { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-3); }
.head-btns { display: flex; gap: var(--s-2); }

.view-tabs { display: inline-flex; gap: 2px; padding: 3px; width: fit-content; align-self: center; }
.view-tabs button { height: 32px; padding: 0 var(--s-5); border: none; border-radius: calc(var(--r) - 3px); background: transparent; font-size: var(--fs-sm); font-weight: var(--fw-medium); color: var(--text-3); transition: all var(--dur-1) var(--ease); }
.view-tabs button.on { background: var(--surface); color: var(--text); box-shadow: var(--shadow-xs); }

/* 路线图 */
.map-card { padding: var(--s-5); }
.day-chips { display: flex; gap: var(--s-2); flex-wrap: wrap; margin-bottom: var(--s-4); }
.chart { height: 460px; }
.map-warn { display: flex; align-items: center; gap: var(--s-2); margin-top: var(--s-3); font-size: var(--fs-xs); color: var(--text-faint); }
.warn-ico { width: 15px; height: 15px; border-radius: 50%; background: var(--warn-soft); color: var(--warn); font-size: 10px; font-weight: var(--fw-bold); display: inline-flex; align-items: center; justify-content: center; flex: none; }

/* 时间线 */
.tl-card { padding: var(--s-5) var(--s-6); }
.ruler { position: relative; height: 26px; margin-left: 128px; margin-bottom: var(--s-2); }
.ruler-tick { position: absolute; top: 0; transform: translateX(-50%); font-size: 11px; color: var(--text-faint); font-variant-numeric: tabular-nums; }
.ruler-tick::after { content: ""; position: absolute; left: 50%; top: 16px; width: 1px; height: 8px; background: var(--border); }
.lanes { display: flex; flex-direction: column; gap: var(--s-4); }
.lane { display: flex; gap: var(--s-4); }
.lane-head { width: 112px; flex: none; padding-top: 6px; }
.lane-day { font-weight: var(--fw-bold); color: var(--accent); font-size: var(--fs-sm); }
.lane-title { display: block; font-size: var(--fs-xs); color: var(--text-faint); margin-top: 2px; }
.lane-track { position: relative; flex: 1; height: 44px; background: var(--surface-2); border: 1px solid var(--border-soft); border-radius: var(--r); overflow: hidden; }
.tl-bar { position: absolute; top: 5px; bottom: 5px; border-radius: var(--r-sm); color: #fff; display: flex; align-items: center; gap: 5px; padding: 0 var(--s-2); overflow: hidden; white-space: nowrap; box-shadow: var(--shadow-xs); }
.tl-bar.hotel { opacity: .85; border-radius: var(--r-pill); }
.bar-emoji { font-size: 12px; flex: none; }
.bar-name { font-size: 11px; font-weight: var(--fw-medium); overflow: hidden; text-overflow: ellipsis; }
.tl-legend { display: flex; gap: var(--s-4); flex-wrap: wrap; margin-top: var(--s-5); padding-top: var(--s-4); border-top: 1px solid var(--border-soft); }
.lg-item { display: inline-flex; align-items: center; gap: var(--s-2); font-size: var(--fs-xs); color: var(--text-3); }
.lg-item i { width: 8px; height: 8px; border-radius: 2px; }

@media (max-width: 720px) {
  .lane-head { display: none; }
  .ruler { margin-left: 0; }
}
</style>
