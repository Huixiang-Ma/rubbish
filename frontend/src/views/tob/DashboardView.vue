<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { govApi } from '../../api/index.js'

const range = ref('近 30 天')

// KPI / 客户榜 / 图表：GET /api/stats/overview（真实任务聚合，失败回退演示数据）
const kpis = ref([
  { label: '任务总数',    value: '1,284',   trend: '',  trendUp: true,  note: '全部行程生成任务' },
  { label: '完成率',      value: '94.6%',   trend: '',  trendUp: true,  note: 'COMPLETED / 总数' },
  { label: '覆盖客户',    value: '128',     trend: '',  trendUp: true,  note: 'toB 客户归属 TOP' },
  { label: '待处理挂起',  value: '23',      trend: '',  trendUp: false, note: '预算 / 安全审批队列' },
])

const customers = ref([
  { rank: 1, name: '苏州文旅集团',     count: 186, region: '江苏' },
  { rank: 2, name: '杭州运河景区',     count: 142, region: '浙江' },
  { rank: 3, name: '大理苍洱运营',     count: 118, region: '云南' },
  { rank: 4, name: '成都熊猫基地',     count: 96,  region: '四川' },
  { rank: 5, name: '厦门鼓浪屿景区',   count: 78,  region: '福建' },
  { rank: 6, name: '西安曲江文旅',     count: 64,  region: '陕西' },
])

const integrations = ref([
  { k: '携程开放平台',  v: '已接入', ok: true },
  { k: '飞猪直连',      v: '已接入', ok: true },
  { k: '12306',         v: '已接入', ok: true },
  { k: '美团门票',      v: '维护中', ok: false },
  { k: '高德地图',      v: '已接入', ok: true },
  { k: '腾讯位置服务',  v: '已接入', ok: true },
])

const DAILY_FALLBACK = Array.from({ length: 30 }, (_, i) => ({ date: i + 1, count: 12 + Math.round(Math.sin(i / 3) * 8 + i * 2.2) }))
const dailyCreated = ref(DAILY_FALLBACK)
const STATUS_FALLBACK = [
  { name: '排队中', value: 184 }, { name: '生成中', value: 86 }, { name: '已完成', value: 1214 },
  { name: '待安全审核', value: 14 }, { name: '待预算审批', value: 9 }, { name: '失败', value: 12 },
]
const statusDist = ref(STATUS_FALLBACK)

async function loadStats() {
  try {
    const st = await govApi.stats()
    const pending = await govApi.pendingApprovals().catch(() => ({ total: 0 }))
    kpis.value = [
      { label: '任务总数', value: (st.total ?? 0).toLocaleString(), trend: '', trendUp: true, note: '全部行程生成任务' },
      { label: '完成率', value: st.completed_rate != null ? `${(st.completed_rate * 100).toFixed(1)}%` : '—', trend: '', trendUp: true, note: 'COMPLETED / 总数' },
      { label: '覆盖客户', value: String((st.customers || []).length), trend: '', trendUp: true, note: 'toB 客户归属 TOP' },
      { label: '待处理挂起', value: String(pending.total ?? 0), trend: '', trendUp: false, note: '预算 / 安全审批队列' },
    ]
    if ((st.customers || []).length) {
      customers.value = st.customers.map(([name, count], i) => ({ rank: i + 1, name, count, region: '' }))
    }
    if ((st.daily_created || []).length) dailyCreated.value = st.daily_created
    const ZH = { QUEUED: '排队中', PENDING: '排队中', RUNNING: '生成中', COMPLETED: '已完成', WAITING_SAFETY_REVIEW: '待安全审核', WAITING_BUDGET_APPROVAL: '待预算审批', FAILED: '失败' }
    if ((st.status_distribution || []).length) {
      statusDist.value = st.status_distribution.map(([k, v]) => ({ name: ZH[k] || k, value: v }))
    }
  } catch { /* 回退演示数据（AUTH_ENABLED 时需工作台登录） */ }
  try {
    const ig = await govApi.integrations()
    const rows = ig && ig.adapters
    if (Array.isArray(rows) && rows.length) {
      integrations.value = rows.map(a => ({
        k: a.name || a.adapter || a.key || '适配器',
        v: a.status === 'ok' || a.available ? '已接入' : (a.status || '未接入'),
        ok: a.status === 'ok' || !!a.available,
      }))
    }
  } catch { /* 回退演示数据 */ }
}

function exportCsv() {
  const rows = [['日期', '新增任务'], ...dailyCreated.value.map(d => [d.date, d.count])]
  const csv = '\ufeff' + rows.map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `dashboard-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

const mainChartEl = ref(null)
const pieChartEl  = ref(null)
let mainChart, pieChart

const palette = ['#6E86A0', '#8CA6BC', '#A6BCCB', '#93A9BC', '#B4C6D4', '#7C94A8']

onMounted(async () => {
  loadStats()
  await nextTick()
  mainChart = echarts.init(mainChartEl.value)
  pieChart  = echarts.init(pieChartEl.value)

  mainChart.setOption({
    grid: { left: 24, right: 24, top: 24, bottom: 36, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#FFFFFF',
      borderColor: '#E8E4DC',
      textStyle: { color: '#1F1D1A', fontSize: 12 },
      boxShadow: '0 4px 16px rgba(31,29,26,.08)',
    },
    legend: {
      bottom: 0, icon: 'roundRect',
      textStyle: { color: '#5C5853', fontSize: 12 },
      itemWidth: 10, itemHeight: 10,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dailyCreated.value.map(d => `${String(d.date).slice(5) || d.date}`),
      axisLabel: { color: '#8E8A82', fontSize: 11, interval: 2 },
      axisLine: { lineStyle: { color: '#E8E4DC' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#8E8A82', fontSize: 11 },
      splitLine: { lineStyle: { color: '#F0EDE6' } },
    },
    series: [
      {
        name: '新建任务', type: 'line', smooth: true,
        symbol: 'circle', symbolSize: 6,
        lineStyle: { width: 2, color: '#4F6F92' },
        itemStyle: { color: '#4F6F92', borderColor: '#FFFFFF', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(79,111,146,.18)' },
            { offset: 1, color: 'rgba(79,111,146,0)' },
          ])
        },
        data: dailyCreated.value.map(d => d.count),
      },
      {
        name: '完成数', type: 'line', smooth: true,
        symbol: 'circle', symbolSize: 5,
        lineStyle: { width: 2, color: '#90A5B8' },
        itemStyle: { color: '#90A5B8', borderColor: '#FFFFFF', borderWidth: 2 },
        data: dailyCreated.value.map(d => Math.round(d.count * 0.9)),
      },
    ],
  })

  const pieData = statusDist.value
  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: '#FFFFFF',
      borderColor: '#E8E4DC',
      textStyle: { color: '#1F1D1A', fontSize: 12 },
    },
    legend: {
      bottom: 0, icon: 'roundRect',
      textStyle: { color: '#5C5853', fontSize: 12 },
      itemWidth: 10, itemHeight: 10,
    },
    series: [{
      type: 'pie',
      radius: ['52%', '76%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: false,
      label: { show: false },
      labelLine: { show: false },
      itemStyle: {
        borderColor: '#FFFFFF', borderWidth: 3, borderRadius: 4,
      },
      data: pieData.map((d, i) => ({ ...d, itemStyle: { color: palette[i % palette.length] } })),
    }],
  })

  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  mainChart?.dispose(); pieChart?.dispose()
})
function resize() { mainChart?.resize(); pieChart?.resize() }
</script>

<template>
  <div class="dashboard">
    <div class="container-wide">
      <!-- 页头 -->
      <header class="page-head">
        <div class="head-copy">
          <span class="eyebrow">运营后台</span>
          <h1 class="page-title">经营看板</h1>
          <p class="page-sub">任务总量、状态分布与近 30 天趋势</p>
        </div>
        <div class="row gap-3 wrap">
          <div class="chip-group">
            <button v-for="r in ['今日','近 7 天','近 30 天','近 90 天']" :key="r"
                    class="chip chip-sm" :class="{ active: range === r }"
                    @click="range = r">{{ r }}</button>
          </div>
          <button class="btn btn-ghost btn-sm">
            <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></svg>
            导出
          </button>
          <button class="btn btn-primary btn-sm">
            <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-9-9"/><path d="M21 3v6h-6"/></svg>
            刷新
          </button>
        </div>
      </header>

      <!-- KPI -->
      <section class="kpi-grid">
        <div v-for="(k, i) in kpis" :key="k.label" class="kpi card anim-fade-up" :class="`delay-${i+1}`">
          <div class="kpi-label">{{ k.label }}</div>
          <div class="kpi-value">{{ k.value }}</div>
          <div class="kpi-foot">
            <span class="trend" :class="k.trendUp ? 'up' : 'down'">
              <svg v-if="k.trendUp" class="icon icon-sm" viewBox="0 0 24 24"><path d="M5 12l7-7 7 7"/><path d="M12 5v14"/></svg>
              <svg v-else class="icon icon-sm" viewBox="0 0 24 24"><path d="M19 12l-7 7-7-7"/><path d="M12 19V5"/></svg>
              {{ k.trend }}
            </span>
            <span class="t-3 t-xs">{{ k.note }}</span>
          </div>
        </div>
      </section>

      <!-- 图表区 -->
      <section class="charts">
        <div class="card chart-card chart-main">
          <div class="card-head">
            <div>
              <h3>新建与完成趋势</h3>
              <p class="t-3 t-sm">近 30 天 · 单位 / 单</p>
            </div>
            <div class="row gap-2">
              <span class="legend-dot" style="background:#4F6F92"></span>
              <span class="t-3 t-sm">新建任务</span>
              <span class="legend-dot" style="background:#90A5B8;margin-left:var(--s-3)"></span>
              <span class="t-3 t-sm">完成数</span>
            </div>
          </div>
          <div ref="mainChartEl" class="chart-canvas"></div>
        </div>

        <div class="card chart-card chart-side">
          <div class="card-head">
            <div>
              <h3>状态分布</h3>
              <p class="t-3 t-sm">任务生命周期占比</p>
            </div>
          </div>
          <div ref="pieChartEl" class="chart-canvas"></div>
        </div>
      </section>

      <!-- 客户任务量 -->
      <section class="card mt-6 section-card">
        <div class="card-head">
          <div>
            <h3>客户任务量 TOP</h3>
            <p class="t-3 t-sm">按累计行程生成任务数排序</p>
          </div>
          <button class="btn btn-text btn-sm">查看全部
            <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/></svg>
          </button>
        </div>

        <table class="table mt-4">
          <thead>
            <tr>
              <th style="width:60px">排名</th>
              <th>客户名称</th>
              <th>所属区域</th>
              <th class="ta-right">任务数</th>
              <th style="width:180px">占比</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in customers" :key="c.rank">
              <td class="t-3">{{ String(c.rank).padStart(2,'0') }}</td>
              <td class="fw-medium">{{ c.name }}</td>
              <td class="t-2">{{ c.region }}</td>
              <td class="ta-right fw-medium">{{ c.count }}</td>
              <td>
                <div class="progress"><span :style="{ width: ((c.count / 200) * 100) + '%' }"></span></div>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 集成状态 -->
      <section class="card mt-6 section-card">
        <div class="card-head">
          <div>
            <h3>外部集成状态</h3>
            <p class="t-3 t-sm">票务 / 大交通 / 地图等三方接入</p>
          </div>
        </div>
        <div class="int-grid mt-4">
          <div v-for="i in integrations" :key="i.k" class="int-item">
            <span class="int-dot" :class="i.ok ? 'ok' : 'warn'"></span>
            <span class="int-name fw-medium">{{ i.k }}</span>
            <span class="tag" :class="i.ok ? 'tag-ok' : 'tag-warn'">{{ i.v }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: var(--content-w-wide); }

/* —— 页头 —— */
.page-head {
  display: flex; justify-content: space-between; align-items: flex-end;
  gap: var(--s-5); margin-bottom: var(--s-7);
  flex-wrap: wrap;
}
.page-title { font-size: var(--fs-2xl); margin-top: var(--s-3); font-weight: var(--fw-semi); }
.page-sub { color: var(--text-3); margin-top: var(--s-2); font-size: var(--fs-sm); }

.chip-group { display: inline-flex; gap: var(--s-1); padding: 3px; background: var(--bg-soft); border-radius: var(--r-pill); }
.chip-group .chip { border: 0; background: transparent; }
.chip-group .chip.active { background: var(--surface); box-shadow: var(--shadow-xs); }

/* —— KPI —— */
.kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: var(--s-4); margin-bottom: var(--s-6);
}
.kpi { padding: var(--s-5) var(--s-5); }
.kpi-label { font-size: var(--fs-xs); color: var(--text-3); text-transform: uppercase; letter-spacing: 0.1em; font-weight: var(--fw-medium); }
.kpi-value {
  font-size: var(--fs-3xl); font-weight: var(--fw-bold);
  letter-spacing: -0.025em; margin: var(--s-3) 0 var(--s-4);
  color: var(--text);
}
.kpi-foot { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.trend {
  display: inline-flex; align-items: center; gap: 2px;
  font-size: var(--fs-xs); font-weight: var(--fw-medium);
  padding: 2px var(--s-2); border-radius: var(--r-pill);
}
.trend.up   { color: var(--ok);     background: var(--ok-soft); }
.trend.down { color: var(--danger); background: var(--danger-soft); }

/* —— Charts —— */
.charts {
  display: grid; grid-template-columns: 1.7fr 1fr;
  gap: var(--s-4);
}
.chart-card { padding: var(--s-5) var(--s-6) var(--s-4); }
.card-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: var(--s-4);
}
.card-head h3 { font-size: var(--fs-md); font-weight: var(--fw-semi); }
.card-head p { margin-top: var(--s-1); font-size: var(--fs-xs); }
.legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: var(--s-1); }
.chart-canvas { width: 100%; height: 320px; }

/* —— 客户表 —— */
.section-card { padding: var(--s-6); }
.ta-right { text-align: right; }

/* —— 集成状态 —— */
.int-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: var(--s-3);
}
.int-item {
  display: flex; align-items: center; gap: var(--s-3);
  padding: var(--s-3) var(--s-4);
  border: 1px solid var(--border-soft);
  border-radius: var(--r);
  background: var(--surface-2);
  transition: border-color var(--dur-1) var(--ease), background var(--dur-1) var(--ease);
}
.int-item:hover { border-color: var(--border); background: var(--surface); }
.int-dot {
  width: 8px; height: 8px; border-radius: 50%;
}
.int-dot.ok   { background: var(--ok); }
.int-dot.warn { background: var(--warn); }
.int-name { flex: 1; font-size: var(--fs-sm); }

/* —— 客户表 · 占比进度条(冷色系) —— */
.section-card :deep(.progress > span) {
  background: linear-gradient(90deg, #4F6F92, #8CA6BC);
}

@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.anim-fade-up { animation: rise .5s var(--ease) both; }

@media (max-width: 1100px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .charts   { grid-template-columns: 1fr; }
  .int-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .kpi-grid { grid-template-columns: 1fr; }
  .int-grid { grid-template-columns: 1fr; }
}
</style>
