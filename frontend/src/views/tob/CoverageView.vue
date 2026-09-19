<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
import TobIcon from '../../components/TobIcon.vue'
import { coverageApi, assistApi } from '../../api/index.js'

/* 语料缺口工单：拒答/空命中 query 聚类（数据智能闭环 环2） */
const gaps = ref([])
async function loadGaps() {
  try {
    const res = await assistApi.ragGaps()
    gaps.value = (res && res.items) || []
  } catch { /* staff 才可读 */ }
}

/* —— 覆盖率：GET /api/stats/product-coverage(/trend)（结构对齐后端口径；失败回退演示数据） —— */
const overview = ref({
  total_plans: 486,
  rag_hit_plans: 402,
  rag_miss_plans: 84,
  hit_rate: 0.827,
  refusal_rate: 0.062,
  empty_rate: 0.031,
  avg_distance: 0.54,
  coverage_by_category: {
    '景点': 0.91, '餐饮': 0.86, '住宿': 0.88,
    '交通': 0.72, '购物': 0.44, '文化': 0.58,
  },
  top_missing: [
    { name: '三亚蜈支洲岛潜水套票', count: 27 },
    { name: '成都川剧变脸茶馆演出', count: 19 },
    { name: '敦煌莫高窟特窟预约', count: 14 },
    { name: '呼伦贝尔草原骑马体验', count: 11 },
    { name: '泉州簪花围民俗写真', count: 8 },
  ],
})

const range = ref('30d')
const RANGE_DAYS = { '7d': 7, '30d': 30, '90d': 90 }

function genTrend(days) {
  const out = []
  let hit = 0.79, refusal = 0.075, empty = 0.04
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(2026, 8, 9 - i)
    hit = Math.min(0.95, Math.max(0.7, hit + (Math.random() - 0.45) * 0.025))
    refusal = Math.min(0.15, Math.max(0.03, refusal + (Math.random() - 0.5) * 0.008))
    empty = Math.min(0.09, Math.max(0.01, empty + (Math.random() - 0.5) * 0.006))
    out.push({
      date: `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
      hit_rate: +hit.toFixed(3),
      refusal_rate: +refusal.toFixed(3),
      empty_rate: +empty.toFixed(3),
    })
  }
  return out
}
const trend = ref(genTrend(RANGE_DAYS['30d']))

watch(range, async (r) => {
  try {
    const res = await coverageApi.trend({ days: RANGE_DAYS[r] })
    if (res && Array.isArray(res.trend) && res.trend.some(t => t.hit_rate > 0)) trend.value = res.trend
    else trend.value = genTrend(RANGE_DAYS[r])
  } catch { trend.value = genTrend(RANGE_DAYS[r]) }
})

onMounted(async () => {
  loadGaps()
  try {
    const res = await coverageApi.overview()
    if (res && res.total_plans !== undefined) overview.value = { ...overview.value, ...res }
  } catch { /* 回退演示数据 */ }
  try {
    const res = await coverageApi.trend({ days: RANGE_DAYS['30d'] })
    if (res && Array.isArray(res.trend) && res.trend.some(t => t.hit_rate > 0)) trend.value = res.trend
  } catch { /* 保留演示曲线 */ }
})

/* —— 冷色系(命中/拒答/空命中 + 分级) —— */
const C_HIT = '#5C7A9D', C_REF = '#98A8B5', C_EMP = '#B4C6D4'
const kpiColors = { hit: C_HIT, refusal: C_REF, empty: C_EMP, dist: '#8FA6BC' }

function rateColor(r) {
  if (r >= 0.8) return C_HIT
  if (r >= 0.6) return '#8FA6BC'
  if (r >= 0.4) return C_EMP
  return 'var(--danger)'
}

/* —— 健康度评分(命中率 50% + 分类均衡 30% + 拒答反向 20%) —— */
const healthScore = computed(() => {
  const cats = Object.values(overview.value.coverage_by_category)
  if (!cats.length) return 0
  const mean = cats.reduce((a, b) => a + b, 0) / cats.length
  const variance = cats.reduce((s, x) => s + (x - mean) ** 2, 0) / cats.length
  const balance = Math.max(0, 1 - variance * 4)
  return Math.round(overview.value.hit_rate * 50 + balance * 30 + (1 - overview.value.refusal_rate) * 20)
})
const healthColor = computed(() => {
  const s = healthScore.value
  if (s >= 80) return 'var(--ok)'
  if (s >= 60) return '#8FA6BC'
  if (s >= 40) return 'var(--warn)'
  return 'var(--danger)'
})
const healthLabel = computed(() => {
  const s = healthScore.value
  if (s >= 80) return '良好 · 标品库能充分支撑行程规划'
  if (s >= 60) return '一般 · 存在分类短板,建议入库补充'
  if (s >= 40) return '告警 · 部分行程被迫拒答,需排查'
  return '严重 · 标品库覆盖率不足,建议暂停接入'
})

/* —— 趋势折线图 —— */
const chartEl = ref(null)
let chart = null, ro = null

function renderChart() {
  if (!chartEl.value) return
  if (chart) chart.dispose()
  const dates = trend.value.map(t => t.date)
  const hit = trend.value.map(t => +(t.hit_rate * 100).toFixed(1))
  const refusal = trend.value.map(t => +(t.refusal_rate * 100).toFixed(1))
  const empty = trend.value.map(t => +(t.empty_rate * 100).toFixed(1))
  chart = echarts.init(chartEl.value)
  ro = new ResizeObserver(() => chart?.resize())
  ro.observe(chartEl.value)
  chart.setOption({
    grid: { left: 8, right: 12, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#FFFFFF', borderColor: '#E8E4DC',
      textStyle: { color: '#1F1D1A', fontSize: 12 },
      valueFormatter: v => v + '%',
    },
    xAxis: {
      type: 'category', data: dates, boundaryGap: false,
      axisLabel: { color: '#B5B0A6', fontSize: 11 },
      axisLine: { lineStyle: { color: '#E8E4DC' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value', max: 100,
      axisLabel: { color: '#B5B0A6', fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#F0EDE6' } },
    },
    series: [
      { name: '命中率', type: 'line', smooth: true, data: hit, showSymbol: false,
        lineStyle: { color: C_HIT, width: 2.5 }, itemStyle: { color: C_HIT },
        areaStyle: { color: 'rgba(92,122,157,.10)' } },
      { name: '拒答率', type: 'line', smooth: true, data: refusal, showSymbol: false,
        lineStyle: { color: C_REF, width: 2 }, itemStyle: { color: C_REF } },
      { name: '空命中率', type: 'line', smooth: true, data: empty, showSymbol: false,
        lineStyle: { color: C_EMP, width: 1.5, type: 'dashed' }, itemStyle: { color: C_EMP } },
    ],
  })
}

// 数据到达 / 切换区间后重绘
watch([trend, overview], () => { renderChart() })
onMounted(renderChart)
onBeforeUnmount(() => { chart?.dispose(); ro?.disconnect() })
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <!-- 语料缺口工单（环2） -->
    <div v-if="gaps.length" class="card gaps-card">
      <h4 style="margin:0 0 var(--s-3)">📋 语料缺口工单 · {{ gaps.length }} 条（拒答/空命中聚类）</h4>
      <div v-for="g in gaps.slice(0, 8)" :key="g.query" class="gap-row">
        <span class="gap-q">{{ g.query }}</span>
        <span class="tag tag-warn">命中失败 {{ g.count }} 次</span>
        <span class="mono-xs" style="color:var(--text-faint)">{{ g.last_at }}</span>
      </div>
      <p class="gap-tip">建议：为以上高频问题补充对应知识库文档（MD/TXT/CSV/HTML），补充后自动进入召回。</p>
    </div>

    <div class="page-head">
      <div>
        <div class="eyebrow">知识 · 覆盖率</div>
        <h1 class="page-title">标品覆盖率</h1>
        <p class="page-desc">标品库对行程规划业务的支撑能力,从 <b>行程覆盖 / 命中度 / 拒答风险</b> 三个视角量化健康度;分类覆盖率低于 50% 或拒答率突破 20% 时,应触发标品入库任务。</p>
      </div>
      <div class="page-actions">
        <div class="status-tabs">
          <button v-for="r in ['7d', '30d', '90d']" :key="r" :class="{ on: range === r }" @click="range = r; $nextTick(renderChart)">
            {{ { '7d': '7 天', '30d': '30 天', '90d': '90 天' }[r] }}
          </button>
        </div>
      </div>
    </div>

    <!-- KPI -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="k">行程标品覆盖率</div>
        <div class="v" :style="{ color: kpiColors.hit }">{{ (overview.hit_rate * 100).toFixed(1) }}<i class="unit">%</i></div>
        <div class="sub">{{ overview.rag_hit_plans }} / {{ overview.total_plans }} 行程被标品库覆盖</div>
        <div class="kbar"><i :style="{ width: overview.hit_rate * 100 + '%', background: kpiColors.hit }" /></div>
      </div>
      <div class="stat-card">
        <div class="k">拒答率 <em>(距离过大无法引用)</em></div>
        <div class="v" :style="{ color: kpiColors.refusal }">{{ (overview.refusal_rate * 100).toFixed(1) }}<i class="unit">%</i></div>
        <div class="sub">拒答越多 → 库内"行程相关"标品越少</div>
        <div class="kbar"><i :style="{ width: overview.refusal_rate * 100 * 6 + '%', background: kpiColors.refusal }" /></div>
      </div>
      <div class="stat-card">
        <div class="k">空命中率 <em>(检索无结果)</em></div>
        <div class="v" :style="{ color: kpiColors.empty }">{{ (overview.empty_rate * 100).toFixed(1) }}<i class="unit">%</i></div>
        <div class="sub">通常因为拼写错误或未入库的新概念</div>
        <div class="kbar"><i :style="{ width: overview.empty_rate * 100 * 8 + '%', background: kpiColors.empty }" /></div>
      </div>
      <div class="stat-card">
        <div class="k">平均检索距离</div>
        <div class="v" :style="{ color: kpiColors.dist }">{{ overview.avg_distance.toFixed(2) }}</div>
        <div class="sub">越低表示标品与问题语义越贴近(阈值 0.8)</div>
        <div class="kbar"><i :style="{ width: overview.avg_distance * 100 + '%', background: kpiColors.dist }" /></div>
      </div>
    </div>

    <div class="cov-body">
      <!-- 左:分类完整度 + TOP 缺口 -->
      <div class="card pane">
        <div class="pane-title">分类完整度</div>
        <div class="pane-sub">每个分类的标品覆盖情况,识别"偏科"</div>
        <div class="cat-list">
          <div v-for="(rate, cat) in overview.coverage_by_category" :key="cat" class="cat-row">
            <span class="cat-name">{{ cat }}</span>
            <div class="cat-track"><i :style="{ width: rate * 100 + '%', background: rateColor(rate) }" /></div>
            <b class="cat-val" :style="{ color: rateColor(rate) }">{{ (rate * 100).toFixed(0) }}%</b>
          </div>
        </div>

        <div class="pane-title gap-top">TOP 缺失标品 <span class="suggest">建议入库</span></div>
        <div class="pane-sub">客户反复询问但库内无结果的标品名称</div>
        <table class="table miss-tbl">
          <thead><tr><th>排名</th><th>标品名称</th><th>被问次数</th><th style="text-align:right">建议动作</th></tr></thead>
          <tbody>
            <tr v-for="(m, i) in overview.top_missing" :key="m.name">
              <td><span class="rank" :class="i === 0 ? 'top1' : ''">{{ i + 1 }}</span></td>
              <td class="cell-main">{{ m.name }}</td>
              <td class="mono-xs">{{ m.count }} 次</td>
              <td style="text-align:right"><button class="op-in"><TobIcon name="download" :size="12" />入库</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 右:趋势 + 健康度 -->
      <div class="card pane">
        <div class="pane-row">
          <div class="pane-title">命中率 / 拒答率趋势</div>
          <span class="range-badge">{{ RANGE_DAYS[range] }} 天</span>
        </div>
        <div ref="chartEl" class="chart-box"></div>
        <div class="legend">
          <span><i :style="{ background: C_HIT }"></i>命中率</span>
          <span><i :style="{ background: C_REF }"></i>拒答率</span>
          <span><i :style="{ background: C_EMP }"></i>空命中率</span>
        </div>

        <div class="health-box">
          <div class="health-row">
            <div class="health-num" :style="{ color: healthColor }">{{ healthScore }}<i>/100</i></div>
            <div class="health-meta">
              <b>{{ healthLabel }}</b>
              <p>基于命中率 50% + 分类均衡度 30% + 拒答率反向 20% 加权</p>
            </div>
          </div>
          <div class="health-bar"><i :style="{ width: healthScore + '%', background: healthColor }" /></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.unit { font-size: var(--fs-sm); font-weight: var(--fw-medium); font-style: normal; margin-left: 2px; opacity: .75; }
.stat-card em { font-style: normal; font-weight: 400; opacity: .7; }
.kbar { height: 4px; margin-top: var(--s-3); background: var(--bg-soft); border-radius: 2px; overflow: hidden; }
.kbar i { display: block; height: 100%; border-radius: 2px; transition: width .5s var(--ease); }

.cov-body { display: grid; grid-template-columns: 1fr 1.35fr; gap: var(--s-4); align-items: start; }
.pane { padding: var(--s-5); }
.pane-row { display: flex; justify-content: space-between; align-items: center; }
.range-badge { font-size: var(--fs-xs); padding: 2px var(--s-3); border-radius: var(--r-pill); background: var(--bg-soft); color: var(--text-3); font-weight: var(--fw-medium); }
.gap-top { margin-top: var(--s-6); }

/* 分类完整度 */
.cat-list { display: flex; flex-direction: column; gap: var(--s-3); margin-top: var(--s-3); }
.cat-row { display: grid; grid-template-columns: 44px 1fr 44px; align-items: center; gap: var(--s-3); }
.cat-name { font-size: var(--fs-sm); color: var(--text-2); }
.cat-track { height: 8px; background: var(--bg-soft); border-radius: 4px; overflow: hidden; }
.cat-track i { display: block; height: 100%; border-radius: 4px; transition: width .5s var(--ease); }
.cat-val { font-size: var(--fs-sm); font-variant-numeric: tabular-nums; text-align: right; }

/* 缺失表 */
.miss-tbl { margin-top: var(--s-3); }
.rank {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: var(--r-sm);
  background: var(--bg-soft); color: var(--text-3);
  font-size: var(--fs-xs); font-weight: var(--fw-semi);
  font-variant-numeric: tabular-nums;
}
.rank.top1 { background: var(--accent-soft); color: var(--accent); }
.op-in {
  display: inline-flex; align-items: center; gap: 4px;
  border: none; background: none; padding: 0;
  font-size: var(--fs-xs); font-weight: var(--fw-medium); color: var(--accent);
  cursor: pointer; transition: opacity var(--dur-1) var(--ease);
}
.op-in:hover { opacity: .7; }

/* 趋势 */
.chart-box { height: 280px; margin-top: var(--s-2); }
.legend { display: flex; gap: var(--s-4); margin-top: var(--s-1); font-size: var(--fs-xs); color: var(--text-3); }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }

/* 健康度 */
.health-box { margin-top: var(--s-5); padding: var(--s-5); background: var(--bg-soft); border-radius: var(--r-md); }
.health-row { display: flex; align-items: center; gap: var(--s-5); }
.health-num { font-size: 42px; font-weight: var(--fw-semi); line-height: 1; letter-spacing: -0.02em; font-variant-numeric: tabular-nums; }
.health-num i { font-size: var(--fs-sm); opacity: .55; font-style: normal; margin-left: 3px; font-weight: var(--fw-medium); }
.health-meta b { font-size: var(--fs-sm); display: block; font-weight: var(--fw-semi); }
.health-meta p { font-size: var(--fs-xs); color: var(--text-faint); margin: 3px 0 0; }
.health-bar { margin-top: var(--s-4); height: 6px; background: var(--surface); border-radius: 3px; overflow: hidden; }
.health-bar i { display: block; height: 100%; border-radius: 3px; transition: width .5s var(--ease); }

@media (max-width: 1000px) {
  .cov-body { grid-template-columns: 1fr; }
}
.gaps-card { margin-bottom: var(--s-4); padding: var(--s-5); }
.gap-row { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0; border-bottom: 1px dashed var(--border-soft); }
.gap-q { flex: 1; font-size: var(--fs-sm); }
.gap-tip { margin: var(--s-3) 0 0; font-size: var(--fs-xs); color: var(--text-3); }
</style>