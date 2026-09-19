<script setup>
import { ref, computed } from 'vue'
import * as echarts from 'echarts'
import { onMounted, nextTick, watch } from 'vue'
import TobIcon from '../../components/TobIcon.vue'

const TABS = [
  { key: 'poi', label: '周边服务 POI 库' },
  { key: 'comfort', label: '景区舒适度' },
]
const tab = ref('poi')

/* 演示占位：开放平台对接未开放 */
function demoTip(label) {
  window.alert(label + '：开放平台对接为规划中能力,当前演示环境未开放')
}

/* ============ POI 库 ============ */
const POI_TYPES = ['餐饮', '住宿', '交通枢纽', '购物', '医疗', '停车场']
const f = ref({ kw: '', type: '', city: '苏州' })

const pois = ref([
  { id: 'POI-001', name: '松鹤楼(观前店)', type: '餐饮', city: '苏州', dist: 0.6, verified: true,  phone: '0512-6522****', addr: '姑苏区太监弄72号', hours: '11:00-21:00', linked: 3 },
  { id: 'POI-002', name: '得月楼(观前店)', type: '餐饮', city: '苏州', dist: 0.8, verified: true,  phone: '0512-6522****', addr: '姑苏区太监弄43号', hours: '11:00-21:00', linked: 2 },
  { id: 'POI-003', name: '平江府精品民宿', type: '住宿', city: '苏州', dist: 1.2, verified: true,  phone: '0512-6777****', addr: '姑苏区平江路保吉利桥', hours: '全天', linked: 5 },
  { id: 'POI-004', name: '苏州站(北广场)', type: '交通枢纽', city: '苏州', dist: 2.4, verified: true,  phone: '12306', addr: '姑苏区车站路', hours: '全天', linked: 8 },
  { id: 'POI-005', name: '观前街停车场', type: '停车场', city: '苏州', dist: 1.0, verified: true,  phone: '—', addr: '姑苏区观前街', hours: '全天 · ¥6/h', linked: 1 },
  { id: 'POI-006', name: '市立医院(本部)', type: '医疗', city: '苏州', dist: 1.6, verified: true,  phone: '0512-6236****', addr: '姑苏区道前街26号', hours: '24h 急诊', linked: 0 },
  { id: 'POI-007', name: '诚品书店(苏州)', type: '购物', city: '苏州', dist: 4.2, verified: false, phone: '0512-6696****', addr: '工业园区月廊街8号', hours: '10:00-22:00', linked: 2 },
  { id: 'POI-008', name: '苏大附一院药学部', type: '医疗', city: '苏州', dist: 3.1, verified: false, phone: '—', addr: '姑苏区十梓街', hours: '24h', linked: 0 },
])
const poiRows = computed(() => pois.value.filter(p =>
  (!f.value.kw || p.name.includes(f.value.kw) || p.addr.includes(f.value.kw)) &&
  (!f.value.type || p.type === f.value.type)
))
const poiStats = computed(() => ({
  total: pois.value.length,
  verified: pois.value.filter(p => p.verified).length,
  linked: pois.value.filter(p => p.linked > 0).length,
}))

/* ============ 舒适度 ============ */
const spots = ref([
  { name: '拙政园', level: '拥挤', crowd: 92, wait: '45分钟', advice: '建议 07:30 首场入园', trend: -6 },
  { name: '苏州博物馆', level: '较舒适', crowd: 58, wait: '15分钟', advice: '需预约,现场不售票', trend: +3 },
  { name: '平江路', level: '一般', crowd: 71, wait: '—', advice: '17:00 后人流回升', trend: +9 },
  { name: '虎丘', level: '舒适', crowd: 34, wait: '5分钟', advice: '下午光线适合拍塔', trend: -2 },
  { name: '山塘街', level: '拥挤', crowd: 86, wait: '摇橹船排 30 分钟', advice: '夜航票已售 80%', trend: +12 },
  { name: '网师园', level: '较舒适', crowd: 46, wait: '10分钟', advice: '夜花园限 300 席', trend: 0 },
])
const comfortColor = (l) => ({ '舒适': '#6B9A7E', '较舒适': '#6B7A5C', '一般': '#B08968', '拥挤': '#B0685C' }[l] || '#7B8DA0')

const chartEl = ref(null)
let chart = null
function renderChart() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const arr = [...spots.value].sort((a, b) => a.crowd - b.crowd)
  chart.setOption({
    grid: { left: 80, right: 40, top: 20, bottom: 30 },
    xAxis: { type: 'value', max: 100, splitLine: { lineStyle: { color: '#EDEAE3' } }, axisLabel: { color: '#8E8A82', fontSize: 11 } },
    yAxis: { type: 'category', data: arr.map(s => s.name), axisLabel: { color: '#5C5853', fontSize: 12 }, axisLine: { show: false }, axisTick: { show: false } },
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}:实时客流指数 ${p[0].value}` },
    series: [{
      type: 'bar', barWidth: 14,
      data: arr.map(s => ({ value: s.crowd, itemStyle: { color: comfortColor(s.level), borderRadius: [0, 7, 7, 0] } })),
      label: { show: true, position: 'right', fontSize: 11, color: '#8E8A82', formatter: '{c}' },
    }],
  }, true)
}
onMounted(async () => { await nextTick(); if (tab.value === 'comfort') renderChart() })
watch(tab, async (k) => { if (k === 'comfort') { await nextTick(); renderChart() } })

/* 实时时间 */
const now = '09-10 14:00 更新'
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">运营管理</div>
        <h1 class="page-title">周边服务与舒适度</h1>
        <p class="page-desc">
          维护游客端「服务大厅」的 <b>POI 库</b>(餐饮/住宿/交通/医疗等,需通过核验),
          并监测核心景区 <b>实时舒适度</b> —— 拥挤度将同步至 AI 规划智能体用于避峰排程。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm"><TobIcon name="refresh" :size="14" />同步开放平台</button>
        <button class="btn btn-primary btn-sm"><TobIcon name="plus" :size="14" />登记 POI</button>
      </div>
    </div>

    <div class="status-tabs" style="width:fit-content; margin-bottom:var(--s-4)">
      <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
    </div>

    <!-- ========== POI 库 ========== -->
    <template v-if="tab === 'poi'">
      <div class="stat-grid cols-4">
        <div class="stat-card"><div class="k">POI 总数</div><div class="v">{{ poiStats.total }}</div><div class="sub">苏州城区</div></div>
        <div class="stat-card"><div class="k">已核验</div><div class="v" style="color:var(--accent)">{{ poiStats.verified }}</div><div class="sub">营业执照 + 实地</div></div>
        <div class="stat-card"><div class="k">被方案引用</div><div class="v">{{ poiStats.linked }}</div><div class="sub">出现在服务大厅</div></div>
        <div class="stat-card"><div class="k" style="color:var(--warn)">待核验</div><div class="v" style="color:var(--warn)">{{ poiStats.total - poiStats.verified }}</div><div class="sub">不会推荐给游客</div></div>
      </div>

      <div class="card toolbar">
        <div class="search-box">
          <span class="s-ico"><TobIcon name="search" :size="15" /></span>
          <input v-model.trim="f.kw" placeholder="搜 POI 名称 / 地址…" />
        </div>
        <select v-model="f.type" class="select-slim">
          <option value="">全部类型</option>
          <option v-for="t in POI_TYPES" :key="t">{{ t }}</option>
        </select>
        <select v-model="f.city" class="select-slim">
          <option v-for="c in ['苏州', '杭州', '大理']" :key="c">{{ c }}</option>
        </select>
      </div>

      <div class="card table-card">
        <table class="table">
          <thead>
            <tr><th>POI</th><th>类型</th><th>距古城</th><th>营业 / 电话</th><th>引用</th><th>核验</th><th style="text-align:right">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="p in poiRows" :key="p.id">
              <td>
                <div class="cell-main">{{ p.name }}</div>
                <div class="cell-sub">{{ p.id }} · {{ p.addr }}</div>
              </td>
              <td><span class="type-pill" :data-t="p.type">{{ p.type }}</span></td>
              <td class="num">{{ p.dist }} km</td>
              <td>
                <div class="cell-main" style="font-weight:var(--fw-regular)">{{ p.hours }}</div>
                <div class="cell-sub">{{ p.phone }}</div>
              </td>
              <td class="num">{{ p.linked }} 个方案</td>
              <td>
                <span class="pill" :class="p.verified ? 'pill-on pill-dot' : 'pill-off pill-dot'">{{ p.verified ? '已核验' : '待核验' }}</span>
              </td>
              <td>
                <div class="ops">
                  <button class="op">编辑</button>
                  <button class="op">{{ p.verified ? '取消核验' : '通过核验' }}</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ========== 舒适度 ========== -->
    <template v-else>
      <div class="comfort-grid">
        <!-- 实时卡片 -->
        <div class="cg-list">
          <div v-for="s in spots" :key="s.name" class="card comfort-card">
            <div class="cc-head">
              <b>{{ s.name }}</b>
              <span class="pill-dot pill" :style="{ background: comfortColor(s.level) + '1E', color: comfortColor(s.level) }">{{ s.level }}</span>
            </div>
            <div class="cc-bar"><i :style="{ width: s.crowd + '%', background: comfortColor(s.level) }"></i></div>
            <div class="cc-meta">
              <span>客流指数 {{ s.crowd }}</span>
              <span :class="s.trend > 0 ? 'up' : s.trend < 0 ? 'down' : ''">{{ s.trend > 0 ? '↑ +' : s.trend < 0 ? '↓ ' : '± ' }}{{ s.trend }} /小时</span>
              <span>排队 {{ s.wait }}</span>
            </div>
            <p class="cc-advice">💡 {{ s.advice }}</p>
          </div>
          <p class="update-time">数据来源:景区闸机 + 运营商信令 · {{ now }} · 每 15 分钟刷新</p>
        </div>

        <!-- 图表 -->
        <div class="card chart-card">
          <h4 class="ch-title">实时客流指数排序(低 → 高)</h4>
          <div ref="chartEl" class="chart"></div>
          <div class="ch-legend">
            <span><i style="background:#6B9A7E"></i>舒适(&lt;40)</span>
            <span><i style="background:#6B7A5C"></i>较舒适(40-60)</span>
            <span><i style="background:#B08968"></i>一般(60-80)</span>
            <span><i style="background:#B0685C"></i>拥挤(&gt;80)</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.type-pill { font-size: var(--fs-xs); padding: 2px 10px; border-radius: var(--r-pill); background: var(--surface-2); color: var(--text-2); }
.type-pill[data-t="医疗"] { background: #F6EBE9; color: #B0685C; }
.type-pill[data-t="交通枢纽"] { background: #EDF1F7; color: #5C7A9D; }
.type-pill[data-t="住宿"] { background: #F0EDF4; color: #8B7A9E; }
.num { font-variant-numeric: tabular-nums; font-weight: var(--fw-medium); }

/* 舒适度 */
.comfort-grid { display: grid; grid-template-columns: 340px 1fr; gap: var(--s-4); align-items: start; }
.cg-list { display: flex; flex-direction: column; gap: var(--s-3); }
.comfort-card { padding: var(--s-4) var(--s-5); }
.cc-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--s-2); }
.cc-head b { font-size: var(--fs-sm); }
.cc-bar { height: 6px; background: var(--surface-2); border-radius: var(--r-pill); overflow: hidden; }
.cc-bar i { display: block; height: 100%; border-radius: var(--r-pill); transition: width .4s var(--ease); }
.cc-meta { display: flex; gap: var(--s-3); font-size: var(--fs-xs); color: var(--text-3); margin-top: var(--s-2); }
.cc-meta .up { color: #B0685C; }
.cc-meta .down { color: #4C7A5A; }
.cc-advice { font-size: var(--fs-xs); color: var(--text-3); margin-top: var(--s-2); padding-top: var(--s-2); border-top: 1px dashed var(--border-soft); }
.update-time { font-size: 11px; color: var(--text-faint); text-align: center; }

.chart-card { padding: var(--s-5); }
.ch-title { font-size: var(--fs-sm); margin-bottom: var(--s-4); }
.chart { height: 320px; }
.ch-legend { display: flex; gap: var(--s-4); flex-wrap: wrap; margin-top: var(--s-3); padding-top: var(--s-3); border-top: 1px solid var(--border-soft); }
.ch-legend span { display: inline-flex; align-items: center; gap: 6px; font-size: var(--fs-xs); color: var(--text-3); }
.ch-legend i { width: 8px; height: 8px; border-radius: 2px; }

@media (max-width: 1100px) { .comfort-grid { grid-template-columns: 1fr; } }
</style>
