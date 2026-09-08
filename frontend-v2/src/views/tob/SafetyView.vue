<template>
  <div>
    <div class="page-head">
      <div>
        <h1>安全治理看板</h1>
        <div class="desc" style="color:var(--text-faint)">注入攻击拦截率、攻击类型分布与近 14 天拦截曲线</div>
      </div>
      <button class="btn btn-ghost btn-sm" @click="load">↻ 刷新</button>
    </div>

    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
    <template v-else-if="s">
      <div class="stat-grid">
        <div class="card stat-card"><div class="k">拦截率</div><div class="v" style="color:var(--danger)">{{ ((s.interception_rate ?? 0) * 100).toFixed(1) }}%</div><div class="sub">注入 / 总扫描</div></div>
        <div class="card stat-card"><div class="k">扫描任务数</div><div class="v">{{ s.jobs_scanned }}</div><div class="sub">安全扫描覆盖</div></div>
        <div class="card stat-card"><div class="k">扫描次数</div><div class="v">{{ s.scan_count }}</div><div class="sub">累计安全检查</div></div>
        <div class="card stat-card"><div class="k">拦截动作类型</div><div class="v">{{ Object.keys(s.counters || {}).length }}</div><div class="sub">{{ Object.entries(s.counters || {}).filter(([, v]) => v > 0).map(([k, v]) => `${k}:${v}`).join(' ') || '全部为 0' }}</div></div>
      </div>

      <div class="chart-row">
        <div class="card chart-card">
          <div class="c-title">攻击类型分布</div>
          <div ref="pieEl" style="height:260px"></div>
        </div>
        <div class="card chart-card">
          <div class="c-title">近 14 天拦截量</div>
          <div ref="barEl" style="height:260px"></div>
        </div>
      </div>

      <div class="card" style="padding:20px 24px;margin-top:16px">
        <div class="c-title">最近拦截事件</div>
        <div v-if="!(s.recent_safety_blocks || []).length" class="d-empty">暂无拦截记录</div>
        <table v-else class="table">
          <thead><tr><th>任务</th><th>风险等级</th><th>证据</th><th>时间</th></tr></thead>
          <tbody>
            <tr v-for="(b, i) in s.recent_safety_blocks" :key="i">
              <td style="font-family:var(--mono);font-size:12px;color:var(--text-faint)">{{ b.job_id }}</td>
              <td><span class="tag" :class="b.risk_level === 'high' ? 'tag-red' : 'tag-amber'">{{ b.risk_level || '-' }}</span></td>
              <td style="max-width:480px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text-dim)">{{ b.evidence }}</td>
              <td style="font-family:var(--mono);font-size:12px;color:var(--text-faint)">{{ (b.created_at || '').slice(0, 16) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="s.note" class="note">{{ s.note }}</p>
    </template>
    <div v-else class="empty card"><div class="icon">🛡</div><p>暂无安全数据</p></div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { govApi } from '../../api'
import { useChart } from '../../composables/useChart'

const s = ref(null)
const loading = ref(true)
const pieEl = ref(null)
const barEl = ref(null)

const { render: renderPie } = useChart(pieEl, () => ({
  tooltip: { trigger: 'item', backgroundColor: '#131E33', borderColor: '#263450', textStyle: { color: '#E6EDF7', fontSize: 12 } },
  series: [{
    type: 'pie', radius: ['40%', '66%'], center: ['50%', '46%'], label: { color: '#93A4C0', fontSize: 11 },
    itemStyle: { borderColor: '#131E33', borderWidth: 3, borderRadius: 6 },
    data: (s.value?.attack_distribution || []).map((x, i) => ({
      name: x[0], value: x[1], itemStyle: { color: ['#F87171', '#FBBF24', '#A78BFA', '#38BDF8', '#34D399', '#64748B'][i % 6] },
    })),
  }],
}))

const { render: renderBar } = useChart(barEl, () => {
  const d = s.value?.daily_blocks || []
  return {
    grid: { left: 8, right: 8, top: 20, bottom: 24, containLabel: true },
    tooltip: { trigger: 'axis', backgroundColor: '#131E33', borderColor: '#263450', textStyle: { color: '#E6EDF7', fontSize: 12 } },
    xAxis: { type: 'category', data: d.map(x => x.date?.slice(5)), axisLabel: { color: '#5C6E8C', fontSize: 11 }, axisLine: { lineStyle: { color: '#263450' } }, axisTick: { show: false } },
    yAxis: { type: 'value', axisLabel: { color: '#5C6E8C', fontSize: 11 }, splitLine: { lineStyle: { color: '#1A2740' } } },
    series: [{ type: 'bar', data: d.map(x => x.count), barMaxWidth: 16, itemStyle: { color: '#F87171', borderRadius: [4, 4, 0, 0] } }],
  }
})

async function load() {
  loading.value = true
  try {
    s.value = await govApi.safety()
    setTimeout(renderPie); setTimeout(renderBar)
  } finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.chart-row { display: grid; grid-template-columns: 1fr 1.4fr; gap: 16px; margin-top: 16px; }
@media (max-width: 1000px) { .chart-row { grid-template-columns: 1fr; } }
.chart-card { padding: 20px 24px; }
.c-title { font-weight: 700; font-size: 14.5px; margin-bottom: 8px; }
.d-empty { color: var(--text-faint); font-size: 13px; padding: 16px 0; }
.note { margin-top: 12px; font-size: 12px; color: var(--text-faint); }
</style>
