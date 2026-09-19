<script setup>
import { ref, computed, onMounted } from 'vue'
import TobIcon from '../../components/TobIcon.vue'
import { ordersApi } from '../../api/index.js'

const STATUS_LABEL = { UNPAID: '待支付', PAID: '待使用', USED: '已完成', CANCELLED: '已取消', REFUNDED: '已退款' }
const f = ref({ keyword: '', status: 'all' })

/* —— 订单管理：GET /api/orders（staff 口径）+ 核销/退款/取消 —— */
const FALLBACK = [
  { id: 'WL20260909-0038', no: 'SO-240909-0038', time: '2026-09-09 14:32', items: [{ name: '拙政园', sku: '成人票', qty: 2 }], itemCount: 2, name: '林女士', phone: '138****6214', total: 396, pay: '微信支付', status: 'PAID' },
  { id: 'WL20260909-0037', no: 'SO-240909-0037', time: '2026-09-09 13:58', items: [{ name: '长安古都四日', sku: '整订 · 人均', qty: 2 }], itemCount: 1, name: '王先生', phone: '159****3087', total: 3160, pay: '支付宝', status: 'PAID' },
  { id: 'WL20260909-0036', no: 'SO-240909-0036', time: '2026-09-09 11:20', items: [{ name: '熊猫基地门票', sku: '成人票', qty: 3 }], itemCount: 2, name: '陈女士', phone: '186****5540', total: 733, pay: '微信支付', status: 'USED' },
]
const orders = ref(FALLBACK)

function maskPhone(p) {
  const s = String(p || '')
  return s.length === 11 ? `${s.slice(0, 3)}****${s.slice(7)}` : (s || '—')
}
function toRow(o) {
  const items = (o.items || []).map(it => ({ name: it.name || '', sku: it.sku_label || it.spec || '', qty: it.qty || it.travelers || 1 }))
  return {
    id: o.id, no: o.order_no || o.id,
    time: (o.created_at || '').replace('T', ' ').slice(0, 16),
    items, itemCount: items.length,
    name: (o.contact && o.contact.name) || '—',
    phone: maskPhone(o.contact && o.contact.phone),
    total: o.total ?? o.amount ?? 0,
    pay: o.pay_method || (o.status === 'UNPAID' ? '—' : ''),
    status: o.status,
  }
}

async function load() {
  try {
    const res = await ordersApi.list({ page: 1, page_size: 200 }, { staff: true })
    const rows = (res && res.items) || []
    if (rows.length) orders.value = rows.map(toRow)
  } catch { /* 未登录/网络异常：回退演示数据 */ }
  try {
    const st = await ordersApi.stats({ staff: true })
    if (st && st.daily && st.daily.length) {
      days.value = st.daily.slice(-7).map(d => ({ date: String(d.date).slice(5), gmv: d.gmv ?? d.total ?? 0, count: d.count ?? d.orders ?? 0 }))
    }
  } catch { /* 保留演示趋势 */ }
}
onMounted(load)

async function completeOrder(o) { try { await ordersApi.complete(o.id, { staff: true }); o.status = 'USED' } catch {} }
async function refundOrder(o) { if (!window.confirm(`确认退款订单 ${o.no}?`)) return; try { await ordersApi.refund(o.id, { staff: true }); o.status = 'REFUNDED' } catch {} }
async function cancelOrder(o) { try { await ordersApi.cancel(o.id, '工作台取消', { staff: true }); o.status = 'CANCELLED' } catch {} }

const TABS = [
  { key: 'all', label: '全部' },
  { key: 'UNPAID', label: '待支付' },
  { key: 'PAID', label: '待使用' },
  { key: 'USED', label: '已完成' },
  { key: 'CLOSED', label: '退款/取消' },
]

const rows = computed(() => orders.value.filter(o =>
  (f.value.status === 'all' ||
    (f.value.status === 'CLOSED' ? ['CANCELLED', 'REFUNDED'].includes(o.status) : o.status === f.value.status)) &&
  (!f.value.keyword || (o.no + o.name + (o.items[0] ? o.items[0].name : '')).includes(f.value.keyword))
))

function countOf(key) {
  if (key === 'CLOSED') return orders.value.filter(o => ['CANCELLED', 'REFUNDED'].includes(o.status)).length
  return orders.value.filter(o => o.status === key).length
}

const stat = computed(() => ({
  todayNew: orders.value.length,
  unpaid: countOf('UNPAID'),
  paid: countOf('PAID'),
  used: countOf('USED'),
  after: countOf('CLOSED'),
  gmv: orders.value.filter(o => !['UNPAID', 'CANCELLED'].includes(o.status)).reduce((n, o) => n + (o.total || 0), 0).toLocaleString(),
}))

// 近7日成交（orders/stats，接口不可用时保留演示数据）
const days = ref([
  { date: '09-03', gmv: 8600, count: 6 },
  { date: '09-04', gmv: 12400, count: 9 },
  { date: '09-05', gmv: 9800, count: 7 },
  { date: '09-06', gmv: 15600, count: 11 },
  { date: '09-07', gmv: 21300, count: 14 },
  { date: '09-08', gmv: 17800, count: 12 },
  { date: '09-09', gmv: 18420, count: 8 },
])
const maxGmv = computed(() => Math.max(...days.value.map(d => d.gmv), 1))
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">经营履约</div>
        <h1 class="page-title">订单管理</h1>
        <p class="page-desc">
          承接游客端标品商城下单,支持收款确认、凭证核销、退款等履约操作 —— 订单与 C 端「我的订单」<b>同源同步</b>。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="load"><TobIcon name="refresh" :size="14" />刷新</button>
      </div>
    </div>

    <!-- 经营统计 -->
    <div class="stat-grid cols-6">
      <div class="stat-card"><div class="k">今日新增</div><div class="v">{{ stat.todayNew }}</div><div class="sub">笔订单</div></div>
      <div class="stat-card"><div class="k">待支付</div><div class="v">{{ stat.unpaid }}</div><div class="sub">等待游客付款</div></div>
      <div class="stat-card"><div class="k" style="color:var(--ok)">待使用</div><div class="v" style="color:var(--ok)">{{ stat.paid }}</div><div class="sub">已收款 · 未核销</div></div>
      <div class="stat-card"><div class="k">已完成</div><div class="v">{{ stat.used }}</div><div class="sub">凭证已核销</div></div>
      <div class="stat-card"><div class="k" style="color:var(--warn)">退款/取消</div><div class="v" style="color:var(--warn)">{{ stat.after }}</div><div class="sub">需关注售后</div></div>
      <div class="stat-card"><div class="k">成交额 GMV</div><div class="v">¥{{ stat.gmv }}</div><div class="sub">已支付口径</div></div>
    </div>

    <!-- 近7日成交 -->
    <div class="card chart-card">
      <div class="pane-title">近 7 日成交</div>
      <div class="bars">
        <div v-for="d in days" :key="d.date" class="bar-col">
          <div class="bar-val">{{ d.gmv > 0 ? (d.gmv / 1000).toFixed(1) + 'k' : '' }}</div>
          <div class="bar-track">
            <div class="bar" :style="{ height: (d.gmv / maxGmv * 100) + '%' }" :title="`${d.date} 成交 ¥${d.gmv.toLocaleString()} · ${d.count} 单`" />
          </div>
          <div class="bar-date">{{ d.date }}</div>
        </div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="card toolbar">
      <div class="search-box">
        <span class="s-ico"><TobIcon name="search" :size="15" /></span>
        <input v-model.trim="f.keyword" placeholder="搜订单号 / 标品 / 客户名…" />
      </div>
      <div class="status-tabs" style="margin-left:auto">
        <button v-for="t in TABS" :key="t.key" :class="{ on: f.status === t.key }" @click="f.status = t.key">
          {{ t.label }} <i>{{ t.key === 'all' ? orders.length : countOf(t.key) }}</i>
        </button>
      </div>
    </div>

    <!-- 订单表 -->
    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>订单号 / 下单时间</th>
            <th>商品</th>
            <th>客户</th>
            <th>金额</th>
            <th>支付</th>
            <th>状态</th>
            <th style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in rows" :key="o.id">
            <td>
              <div class="mono-xs" style="color:var(--text-2)">{{ o.no }}</div>
              <div class="cell-sub">{{ o.time }}</div>
            </td>
            <td>
              <div v-for="it in o.items" :key="it.name" class="item-line">
                <b>{{ it.name }}</b>
                <span>{{ it.sku }} × {{ it.qty }}</span>
              </div>
            </td>
            <td>
              <div class="cell-main" style="font-weight:var(--fw-regular)">{{ o.name }}</div>
              <div class="cell-sub">{{ o.phone }}</div>
            </td>
            <td><b class="amount">¥{{ o.total.toLocaleString() }}</b></td>
            <td style="color:var(--text-3)">{{ o.pay }}</td>
            <td>
              <span class="pill" :class="{
                'pill-on': o.status === 'PAID',
                'pill-off': ['UNPAID', 'CANCELLED'].includes(o.status),
                'pill-warn': o.status === 'REFUNDED',
              }" :style="o.status === 'USED' ? 'background:var(--accent-3-soft);color:var(--accent-3)' : (o.status==='REFUNDED' ? 'background:var(--warn-soft);color:var(--warn)' : '')">
                {{ STATUS_LABEL[o.status] }}
              </span>
            </td>
            <td>
              <div class="ops">
                <button class="op" @click="f.keyword = o.no">详情</button>
                <button v-if="o.status === 'PAID'" class="op ok" @click="completeOrder(o)">核销完成</button>
                <button v-if="['PAID', 'USED'].includes(o.status)" class="op danger" @click="refundOrder(o)">退款</button>
                <button v-if="o.status === 'UNPAID'" class="op" @click="cancelOrder(o)">取消</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.chart-card { padding: var(--s-5); }
.bars {
  display: flex; align-items: flex-end; gap: var(--s-5);
  height: 180px; margin-top: var(--s-4);
  padding: 0 var(--s-2);
}
.bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: var(--s-2); height: 100%; }
.bar-val { font-size: var(--fs-xs); color: var(--text-3); font-variant-numeric: tabular-nums; }
.bar-track { flex: 1; width: 100%; max-width: 42px; display: flex; align-items: flex-end; background: var(--bg-soft); border-radius: var(--r-sm); overflow: hidden; }
.bar {
  width: 100%;
  background: linear-gradient(180deg, #7E97B0, #A9BCCB);
  border-radius: var(--r-sm) var(--r-sm) 0 0;
  transition: height var(--dur-3) var(--ease);
}
.bar-col:hover .bar { background: linear-gradient(180deg, #4F6F92, #8FA6BC); }
.bar-date { font-size: var(--fs-xs); color: var(--text-faint); font-variant-numeric: tabular-nums; }

.item-line { display: flex; flex-direction: column; line-height: 1.35; }
.item-line + .item-line { margin-top: var(--s-2); }
.item-line b { font-size: var(--fs-sm); font-weight: var(--fw-medium); }
.item-line span { font-size: var(--fs-xs); color: var(--text-faint); }

.amount { font-variant-numeric: tabular-nums; }
.pill-warn { background: var(--warn-soft); color: var(--warn); }
</style>
