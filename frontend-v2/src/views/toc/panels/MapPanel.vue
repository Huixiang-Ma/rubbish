<template>
  <div>
    <div class="sec-title">每日动线</div>
    <p class="sec-desc">按经纬度绘制的抽象动线图（同色为同一天，序号为当日顺序）</p>

    <div v-if="!days.length" class="empty"><div class="icon">🗺</div><p>暂无动线数据（任务完成后生成）</p></div>
    <template v-else>
      <div class="card" style="padding:18px">
        <div ref="chartEl" style="width:100%;height:420px"></div>
      </div>

      <div class="day-lists">
        <div v-for="d in days" :key="d.day" class="card day-card">
          <div class="day-head">
            <span class="day-badge" :style="{ background: COLORS[(d.day - 1) % COLORS.length] }">Day {{ d.day }}</span>
            <span class="day-theme">{{ d.theme }}</span>
            <span class="tag tag-gray">{{ d.spots.length }} 个点位</span>
          </div>
          <ol class="spot-list">
            <li v-for="(s, i) in d.spots" :key="i">
              <b class="ord" :style="{ background: COLORS[(d.day - 1) % COLORS.length] }">{{ i + 1 }}</b>
              {{ s.name }}
              <span class="t">{{ s.time }}</span>
            </li>
          </ol>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { expApi } from '../../../api'
import { useChart } from '../../../composables/useChart'

const props = defineProps({ jobId: { type: String, required: true } })

const days = ref([])
const chartEl = ref(null)

const COLORS = ['#2563EB', '#F59E0B', '#10B981', '#8B5CF6', '#EF4444', '#06B6D4', '#EC4899', '#84CC16']

const { render } = useChart(chartEl, () => {
  const series = days.value.map((d, di) => {
    const c = COLORS[di % COLORS.length]
    const pts = d.spots.map((s, i) => ({
      value: [s.lng, s.lat, s.time || ''],
      name: s.name,
      label: { show: i === 0, formatter: `D${d.day}·${s.name}`, fontSize: 11, color: '#334155' },
    }))
    return {
      type: 'scatter', name: `Day ${d.day} · ${d.theme}`, data: pts,
      symbolSize: 16, itemStyle: { color: c, borderColor: '#fff', borderWidth: 2, shadowBlur: 6, shadowColor: 'rgba(15,23,42,.25)' },
    }
  })
  // 连线：同一天点位按顺序连线（seriesIndex 对应）
  const lines = days.value.map((d, di) => ({
    type: 'lines', coordinateSystem: 'cartesian2d', zlevel: 0, silent: true,
    lineStyle: { color: COLORS[di % COLORS.length], width: 2, opacity: .45, curveness: .15, type: 'dashed' },
    data: d.spots.slice(0, -1).map((s, i) => ({ coords: [[s.lng, s.lat], [d.spots[i + 1].lng, d.spots[i + 1].lat]] })),
  }))
  return {
    grid: { left: 20, right: 20, top: 40, bottom: 20, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p) => p.seriesName + '<br/>' + (p.name || '') + (p.value?.[2] ? ` · ${p.value[2]}` : ''),
    },
    legend: { top: 6, left: 'center', textStyle: { fontSize: 12, color: '#64748B' }, itemWidth: 12, itemHeight: 8 },
    xAxis: { show: false, min: (v) => v.min - 0.01, max: (v) => v.max + 0.01 },
    yAxis: { show: false, min: (v) => v.min - 0.01, max: (v) => v.max + 0.01 },
    series: [...series, ...lines],
  }
})

onMounted(async () => {
  try {
    const r = await expApi.map(props.jobId)
    days.value = (r.days || []).filter(d => d.spots?.length)
    if (days.value.length) render()
  } catch { /* 未完成时 404 */ }
})
</script>

<style scoped>
.day-lists { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; margin-top: 16px; }
.day-card { padding: 18px 20px; }
.day-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.day-badge { color: #fff; font-size: 12.5px; font-weight: 800; padding: 3px 11px; border-radius: 999px; }
.day-theme { font-weight: 700; font-size: 14.5px; color: var(--ink-900); flex: 1; }
.spot-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.spot-list li { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--ink-700); }
.ord { width: 21px; height: 21px; border-radius: 7px; color: #fff; font-size: 11.5px; display: inline-flex; align-items: center; justify-content: center; flex: none; }
.t { margin-left: auto; font-size: 12px; color: var(--ink-400); font-family: var(--mono); }
</style>
