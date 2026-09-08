<template>
  <div class="cov">
    <header class="cov-head">
      <div>
        <h1>📐 标品覆盖率 <small>标品库对行程规划业务的支撑能力</small></h1>
        <p class="hint">把"行程规划标品库"看作一个有 <b>覆盖面 / 命中度 / 拒答风险</b> 的"积木池"，本页用四个维度量化它的健康度：<b>行程覆盖</b>、<b>分类完整度</b>、<b>命中率趋势</b>、<b>TOP 缺口</b>。当某个分类覆盖率掉到 50% 以下或拒答率突破 20%，应触发标品入库任务。</p>
      </div>
      <div class="head-range">
        <button class="rg" :class="{ active: range === '7d' }" @click="range = '7d'">7 天</button>
        <button class="rg" :class="{ active: range === '30d' }" @click="range = '30d'">30 天</button>
        <button class="rg" :class="{ active: range === '90d' }" @click="range = '90d'">90 天</button>
      </div>
    </header>

    <!-- 1. KPI 看板 -->
    <section class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-label">行程标品覆盖率</div>
        <div class="kpi-big" :style="{ color: kpiColors.hit }">{{ (overview.hit_rate * 100).toFixed(0) }}<i>%</i></div>
        <div class="kpi-sub">{{ overview.rag_hit_plans }} / {{ overview.total_plans }} 行程被标品库覆盖</div>
        <div class="kpi-bar"><i :style="{ width: (overview.hit_rate * 100) + '%', background: kpiColors.hit }" /></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-label">拒答率 <em>（距离过大无法引用）</em></div>
        <div class="kpi-big" :style="{ color: kpiColors.refusal }">{{ (overview.refusal_rate * 100).toFixed(0) }}<i>%</i></div>
        <div class="kpi-sub">拒答越多 → 库里"行程相关"标品越少</div>
        <div class="kpi-bar"><i :style="{ width: (overview.refusal_rate * 100) + '%', background: kpiColors.refusal }" /></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-label">空命中率 <em>（检索无结果）</em></div>
        <div class="kpi-big" :style="{ color: kpiColors.empty }">{{ (overview.empty_rate * 100).toFixed(0) }}<i>%</i></div>
        <div class="kpi-sub">通常因为拼写错误或未入库的新概念</div>
        <div class="kpi-bar"><i :style="{ width: (overview.empty_rate * 100) + '%', background: kpiColors.empty }" /></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-label">平均检索距离</div>
        <div class="kpi-big" :style="{ color: kpiColors.dist }">{{ overview.avg_distance }}<i></i></div>
        <div class="kpi-sub">越低表示标品与问题语义越贴近（阈值 0.8）</div>
        <div class="kpi-bar"><i :style="{ width: (overview.avg_distance * 100) + '%', background: kpiColors.dist }" /></div>
      </article>
    </section>

    <div class="cov-body">
      <!-- 左：分类完整度 + TOP 缺口 -->
      <section class="card cat-card">
        <div class="pane-title">分类完整度</div>
        <p class="sub">每个分类的标品覆盖情况，识别"偏科"</p>
        <div class="cat-list">
          <div v-for="(rate, cat) in overview.coverage_by_category" :key="cat" class="cat-row">
            <span class="cat-icon">{{ catEmoji(cat) }}</span>
            <span class="cat-name">{{ cat }}</span>
            <div class="cat-track">
              <i :style="{ width: (rate * 100) + '%', background: rateColor(rate) }" />
            </div>
            <b :style="{ color: rateColor(rate) }">{{ (rate * 100).toFixed(0) }}%</b>
          </div>
        </div>

        <div class="pane-title" style="margin-top:24px">TOP 缺失标品（建议入库）</div>
        <p class="sub">客户反复询问但库内无结果的标品名称</p>
        <table class="missing-tbl">
          <thead><tr><th>排名</th><th>标品名称</th><th>被问次数</th><th>建议动作</th></tr></thead>
          <tbody>
            <tr v-for="(m, i) in overview.top_missing" :key="m.name">
              <td><span class="rank" :class="rankClass(i)">{{ i + 1 }}</span></td>
              <td><b>{{ m.name }}</b></td>
              <td>{{ m.count }} 次</td>
              <td><button class="btn-link">📥 入库</button></td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 右：趋势图 -->
      <section class="card trend-card">
        <div class="pane-title">
          命中率 / 拒答率趋势
          <span class="badge">{{ trend.length }} 天</span>
        </div>
        <div ref="chartEl" class="chart-box"></div>
        <div class="legend">
          <span><i style="background:#10B981"></i>命中率</span>
          <span><i style="background:#F59E0B"></i>拒答率</span>
          <span><i style="background:#94A3B8"></i>空命中率</span>
        </div>

        <div class="health-box">
          <div class="pane-title">📊 标品库健康度评分</div>
          <div class="health-row">
            <div class="health-num" :style="{ color: healthColor }">{{ healthScore }}<i>/100</i></div>
            <div class="health-meta">
              <b>{{ healthLabel }}</b>
              <p>基于命中率 50% + 分类均衡度 30% + 拒答率反向 20% 加权</p>
            </div>
          </div>
          <div class="health-bar"><i :style="{ width: healthScore + '%', background: healthColor }" /></div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { coverageApi } from '../../api'

const overview = ref({
  total_plans: 0, rag_hit_plans: 0, rag_miss_plans: 0,
  hit_rate: 0, refusal_rate: 0, empty_rate: 0, avg_distance: 0,
  coverage_by_category: {}, top_missing: [],
})
const trend = ref([])
const range = ref('30d')

const chartEl = ref(null)
let chart = null
let ro = null

const kpiColors = {
  hit: '#10B981', refusal: '#F59E0B', empty: '#94A3B8', dist: '#0EA5E9',
}

const CAT_EMOJI = { 景点: '🏛', 餐饮: '🍜', 住宿: '🏨', 交通: '🚄', 购物: '🛍', 文化: '📚' }
function catEmoji(cat) { return CAT_EMOJI[cat] || '📌' }
function rateColor(r) {
  if (r >= 0.8) return '#10B981'
  if (r >= 0.6) return '#38BDF8'
  if (r >= 0.4) return '#F59E0B'
  return '#EF4444'
}
function rankClass(i) {
  if (i === 0) return 'gold'
  if (i === 1) return 'silver'
  if (i === 2) return 'bronze'
  return ''
}

const healthScore = computed(() => {
  const cats = Object.values(overview.value.coverage_by_category)
  if (!cats.length) return 0
  const mean = cats.reduce((a, b) => a + b, 0) / cats.length
  const variance = cats.reduce((s, x) => s + Math.pow(x - mean, 2), 0) / cats.length
  const balance = Math.max(0, 1 - variance * 4)
  const score = overview.value.hit_rate * 50 + balance * 30 + (1 - overview.value.refusal_rate) * 20
  return Math.round(score)
})
const healthColor = computed(() => {
  const s = healthScore.value
  if (s >= 80) return '#10B981'
  if (s >= 60) return '#38BDF8'
  if (s >= 40) return '#F59E0B'
  return '#EF4444'
})
const healthLabel = computed(() => {
  const s = healthScore.value
  if (s >= 80) return '良好 · 标品库能充分支撑行程规划'
  if (s >= 60) return '一般 · 存在分类短板，建议入库补充'
  if (s >= 40) return '告警 · 部分行程被迫拒答，需排查'
  return '严重 · 标品库覆盖率不足，建议暂停接入'
})

async function renderChart() {
  if (!chartEl.value) return
  if (chart) { chart.dispose(); chart = null }
  if (ro) { ro.disconnect(); ro = null }
  await nextTick()
  if (!chartEl.value) return
  const dates = trend.value.map(t => t.date)
  const hit = trend.value.map(t => +(t.hit_rate * 100).toFixed(1))
  const refusal = trend.value.map(t => +(t.refusal_rate * 100).toFixed(1))
  const empty = trend.value.map(t => +(t.empty_rate * 100).toFixed(1))
  chart = echarts.init(chartEl.value)
  ro = new ResizeObserver(() => chart?.resize())
  ro.observe(chartEl.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { show: false },
    grid: { left: 36, right: 16, top: 16, bottom: 28 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#94A3B8', fontSize: 11 } },
    yAxis: { type: 'value', max: 100, axisLabel: { color: '#94A3B8', fontSize: 11, formatter: '{value}%' } },
    series: [
      { name: '命中率', type: 'line', smooth: true, data: hit, lineStyle: { color: '#10B981', width: 2 }, itemStyle: { color: '#10B981' }, areaStyle: { color: 'rgba(16,185,129,.15)' } },
      { name: '拒答率', type: 'line', smooth: true, data: refusal, lineStyle: { color: '#F59E0B', width: 2 }, itemStyle: { color: '#F59E0B' } },
      { name: '空命中率', type: 'line', smooth: true, data: empty, lineStyle: { color: '#94A3B8', width: 1.5, type: 'dashed' }, itemStyle: { color: '#94A3B8' } },
    ],
  })
}

async function loadAll() {
  try {
    const [ov, tr] = await Promise.all([coverageApi.overview(), coverageApi.trend()])
    overview.value = ov
    trend.value = tr.trend || []
  } catch (e) {
    // shoot.mjs 注入 mock；前端无 mock 时会持续重试
  }
}

onMounted(() => { loadAll().then(renderChart) })
watch(range, () => loadAll().then(renderChart))
onBeforeUnmount(() => { if (chart) chart.dispose(); if (ro) ro.disconnect() })
</script>

<style scoped>
.cov { display: flex; flex-direction: column; gap: 18px; }
.cov-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 18px; flex-wrap: wrap; }
.cov-head h1 { font-size: 22px; font-weight: 800; margin: 0; }
.cov-head h1 small { font-size: 12.5px; font-weight: 600; color: var(--text-faint); margin-left: 8px; }
.cov-head .hint { color: var(--text-dim); font-size: 13px; margin: 6px 0 0; line-height: 1.7; max-width: 820px; }
.head-range { display: flex; gap: 4px; background: var(--bg-hover); padding: 4px; border-radius: 9px; }
.rg { padding: 6px 14px; border: none; background: transparent; color: var(--text-dim); border-radius: 6px; cursor: pointer; font-size: 12.5px; font-weight: 600; }
.rg.active { background: var(--card); color: var(--brand); box-shadow: 0 1px 2px rgba(0,0,0,.05); }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.kpi-card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; }
.kpi-label { font-size: 12px; color: var(--text-faint); }
.kpi-label em { font-style: normal; font-size: 11px; }
.kpi-big { font-size: 36px; font-weight: 800; margin: 8px 0 4px; line-height: 1; }
.kpi-big i { font-size: 18px; font-weight: 700; margin-left: 2px; font-style: normal; opacity: .7; }
.kpi-sub { font-size: 11.5px; color: var(--text-faint); margin-bottom: 10px; }
.kpi-bar { height: 4px; background: var(--bg-hover); border-radius: 2px; overflow: hidden; }
.kpi-bar i { display: block; height: 100%; transition: width .5s; }

.cov-body { display: grid; grid-template-columns: 1.1fr 1.4fr; gap: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
.pane-title { font-size: 14.5px; font-weight: 700; display: flex; justify-content: space-between; align-items: center; margin: 0 0 8px; }
.sub { font-size: 12px; color: var(--text-faint); margin: 0 0 14px; }
.badge { font-size: 11px; padding: 2px 8px; background: var(--bg-hover); color: var(--text-dim); border-radius: 999px; font-weight: 600; }

.cat-list { display: flex; flex-direction: column; gap: 10px; }
.cat-row { display: grid; grid-template-columns: 32px 60px 1fr 50px; align-items: center; gap: 10px; }
.cat-icon { font-size: 18px; text-align: center; }
.cat-name { font-size: 13px; color: var(--text-dim); }
.cat-track { height: 8px; background: var(--bg-hover); border-radius: 4px; overflow: hidden; }
.cat-track i { display: block; height: 100%; transition: width .5s; }

.missing-tbl { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.missing-tbl th { text-align: left; font-size: 11px; color: var(--text-faint); padding: 6px 8px; border-bottom: 1px solid var(--line); }
.missing-tbl td { padding: 9px 8px; border-bottom: 1px dashed var(--line); }
.rank { display: inline-block; width: 22px; height: 22px; text-align: center; line-height: 22px; border-radius: 6px; background: var(--bg-hover); font-size: 11px; font-weight: 700; }
.rank.gold { background: #FBBF24; color: #fff; }
.rank.silver { background: #94A3B8; color: #fff; }
.rank.bronze { background: #B45309; color: #fff; }
.btn-link { background: none; border: none; color: var(--brand); cursor: pointer; font-size: 12px; font-weight: 600; }

.chart-box { height: 280px; margin-top: 8px; }
.legend { display: flex; gap: 16px; margin-top: 8px; font-size: 12px; color: var(--text-dim); }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }

.health-box { margin-top: 18px; padding: 16px; background: var(--bg-hover); border-radius: 10px; }
.health-row { display: flex; align-items: center; gap: 18px; }
.health-num { font-size: 44px; font-weight: 800; line-height: 1; }
.health-num i { font-size: 18px; opacity: .55; font-style: normal; margin-left: 4px; }
.health-meta b { font-size: 14px; display: block; }
.health-meta p { font-size: 11.5px; color: var(--text-faint); margin: 4px 0 0; }
.health-bar { margin-top: 12px; height: 6px; background: var(--card); border-radius: 3px; overflow: hidden; }
.health-bar i { display: block; height: 100%; transition: width .5s; }
</style>