<template>
  <div>
    <div class="page-head">
      <div>
        <h1>经营看板</h1>
        <div class="desc" style="color:var(--text-faint)">任务总量、状态分布与近 30 天趋势 · 租户 {{ stats?.tenant || '-' }}</div>
      </div>
      <button class="btn btn-ghost btn-sm" @click="load">↻ 刷新</button>
    </div>

    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
    <template v-else-if="stats">
      <div class="stat-grid">
        <div class="card stat-card"><div class="k">任务总数</div><div class="v">{{ stats.total }}</div><div class="sub">全部行程生成任务</div></div>
        <div class="card stat-card"><div class="k">完成率</div><div class="v" style="color:var(--ok)">{{ ((stats.completed_rate ?? 0) * 100).toFixed(1) }}%</div><div class="sub">COMPLETED / 总数</div></div>
        <div class="card stat-card"><div class="k">覆盖客户</div><div class="v">{{ (stats.customers || []).length }}</div><div class="sub">toB 客户归属 TOP</div></div>
        <div class="card stat-card"><div class="k">待处理挂起</div><div class="v" style="color:var(--warn)">{{ pending }}</div><div class="sub">预算 / 安全审批队列</div></div>
      </div>

      <div class="chart-row">
        <div class="card chart-card">
          <div class="c-title">状态分布</div>
          <div ref="pieEl" style="height:280px"></div>
        </div>
        <div class="card chart-card">
          <div class="c-title">近 30 天新建任务</div>
          <div ref="barEl" style="height:280px"></div>
        </div>
      </div>

      <div class="card" style="padding:20px 24px;margin-top:16px">
        <div class="c-title">客户任务量 TOP</div>
        <div class="cust-rows">
          <div v-for="c in stats.customers || []" :key="c[0]" class="cust-row">
            <span class="c-name">{{ c[0] || '（散客）' }}</span>
            <div class="c-bar"><div :style="{ width: barW(c[1]) }"></div></div>
            <span class="c-num">{{ c[1] }} 单</span>
          </div>
        </div>
      </div>

      <!-- 外部集成状态 -->
      <div class="card" style="padding:20px 24px;margin-top:16px" v-if="integrations">
        <div class="c-title">外部集成状态</div>
        <div class="int-grid">
          <div v-for="(v, k) in integrations" :key="k" class="int-item">
            <span class="tag" :class="v === true || v?.enabled || v?.status === 'ok' ? 'tag-green' : 'tag-gray'">{{ k }}</span>
            <span class="int-val">{{ typeof v === 'object' ? JSON.stringify(v) : v }}</span>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="empty card"><div class="icon">📉</div><p>暂无统计数据</p></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { govApi } from '../../api'
import { useChart } from '../../composables/useChart'

const stats = ref(null)
const pending = ref(0)
const integrations = ref(null)
const loading = ref(true)
const pieEl = ref(null)
const barEl = ref(null)

const STATUS_LABELS = {
  QUEUED: '排队中', RUNNING: '生成中', COMPLETED: '已完成',
  WAITING_SAFETY_REVIEW: '待安全审核', WAITING_BUDGET_APPROVAL: '待预算审批',
  FAILED: '失败', CORRUPTED: '损坏', REPLAN_REQUIRED: '需重规划',
}

const { render: renderPie } = useChart(pieEl, () => ({
  tooltip: { trigger: 'item', backgroundColor: '#131E33', borderColor: '#263450', textStyle: { color: '#E6EDF7', fontSize: 12 } },
  legend: { bottom: 0, textStyle: { color: '#93A4C0', fontSize: 12 }, itemWidth: 12, itemHeight: 8 },
  series: [{
    type: 'pie', radius: ['42%', '68%'], center: ['50%', '44%'],
    label: { show: false },
    itemStyle: { borderColor: '#131E33', borderWidth: 3, borderRadius: 6 },
    data: (stats.value?.status_distribution || []).map(([s, n]) => ({
      name: STATUS_LABELS[s] || s, value: n,
      itemStyle: { color: PIE_COLORS[Object.keys(STATUS_LABELS).indexOf(s) % PIE_COLORS.length] },
    })),
  }],
}))
const PIE_COLORS = ['#38BDF8', '#FBBF24', '#34D399', '#F87171', '#A78BFA', '#64748B', '#FB923C', '#F472B6']

const { render: renderBar } = useChart(barEl, () => {
  const daily = stats.value?.daily_created || []
  return {
    grid: { left: 8, right: 8, top: 24, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis', backgroundColor: '#131E33', borderColor: '#263450', textStyle: { color: '#E6EDF7', fontSize: 12 } },
    xAxis: {
      type: 'category', data: daily.map(d => d.date?.slice(5)),
      axisLabel: { color: '#5C6E8C', fontSize: 11 }, axisLine: { lineStyle: { color: '#263450' } }, axisTick: { show: false },
    },
    yAxis: { type: 'value', axisLabel: { color: '#5C6E8C', fontSize: 11 }, splitLine: { lineStyle: { color: '#1A2740' } } },
    series: [{
      type: 'bar', data: daily.map(d => d.count), barMaxWidth: 18,
      itemStyle: { color: '#0EA5E9', borderRadius: [4, 4, 0, 0] },
    }],
  }
})

const maxCust = computed(() => Math.max(1, ...(stats.value?.customers || []).map(c => c[1])))
function barW(n) { return Math.max(4, (n / maxCust.value) * 100) + '%' }

async function load() {
  loading.value = true
  try {
    const [s, p, i] = await Promise.allSettled([govApi.stats(), govApi.pendingApprovals(), govApi.integrations()])
    if (s.status === 'fulfilled') { stats.value = s.value; setTimeout(renderPie); setTimeout(renderBar) }
    if (p.status === 'fulfilled') pending.value = p.value.total || 0
    if (i.status === 'fulfilled') integrations.value = i.value
  } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.chart-row { display: grid; grid-template-columns: 1fr 1.4fr; gap: 16px; margin-top: 16px; }
@media (max-width: 1000px) { .chart-row { grid-template-columns: 1fr; } }
.chart-card { padding: 20px 24px; }
.c-title { font-weight: 700; font-size: 14.5px; margin-bottom: 10px; }
.cust-rows { display: flex; flex-direction: column; gap: 10px; }
.cust-row { display: grid; grid-template-columns: 140px 1fr 64px; gap: 14px; align-items: center; }
.c-name { font-size: 13.5px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.c-bar { height: 10px; background: var(--bg-raised); border-radius: 999px; overflow: hidden; }
.c-bar > div { height: 100%; background: linear-gradient(90deg, #0EA5E9, #38BDF8); border-radius: 999px; }
.c-num { font-size: 12.5px; color: var(--text-faint); text-align: right; font-family: var(--mono); }
.int-grid { display: flex; flex-wrap: wrap; gap: 10px 22px; }
.int-item { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
.int-val { color: var(--text-faint); }
</style>
