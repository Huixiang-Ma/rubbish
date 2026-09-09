<template>
  <div>
    <div class="page-head">
      <div>
        <h1>订单管理</h1>
        <div class="desc" style="color:var(--text-faint)">
          承接游客端标品商城下单，支持收款确认、凭证核销、退款等履约操作 —— 订单与 C 端「我的订单」<b style="color:var(--text-dim)">同源同步</b>。
        </div>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="loadAll">↻ 刷新</button>
      </div>
    </div>

    <!-- 经营统计 -->
    <div class="ov-stats">
      <div class="ov-stat"><span>今日新增</span><b>{{ stat.today_new }}</b><i>笔订单</i></div>
      <div class="ov-stat"><span>待支付</span><b>{{ stat.by_status.UNPAID }}</b><i>等待游客付款</i></div>
      <div class="ov-stat ok"><span>待使用</span><b>{{ stat.by_status.PAID }}</b><i>已收款 · 未核销</i></div>
      <div class="ov-stat"><span>已完成</span><b>{{ stat.by_status.USED }}</b><i>凭证已核销</i></div>
      <div class="ov-stat warn"><span>退款/取消</span><b>{{ (stat.by_status.CANCELLED || 0) + (stat.by_status.REFUNDED || 0) }}</b><i>需关注售后</i></div>
      <div class="ov-stat gold"><span>成交额 GMV</span><b>¥{{ stat.gmv }}</b><i>已支付口径</i></div>
    </div>

    <!-- 近7日成交 -->
    <div class="card ov-chart">
      <div class="ov-chart-title">近 7 日成交</div>
      <div class="ov-bars">
        <div v-for="d in stat.days" :key="d.date" class="ov-bar-col">
          <div class="ov-bar-label">{{ d.gmv > 0 ? '¥' + d.gmv : '' }}</div>
          <div class="ov-bar-track">
            <div class="ov-bar" :style="{ height: barH(d.gmv) }" :title="`${d.date} 成交 ¥${d.gmv} · ${d.count} 单`"></div>
          </div>
          <div class="ov-bar-date">{{ d.date }}</div>
        </div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="card ov-toolbar">
      <div class="ov-search">
        <span class="s-ico">⌕</span>
        <input v-model.trim="f.keyword" placeholder="搜订单号 / 标品 / 客户名…" @keyup.enter="applyFilter" />
      </div>
      <div class="ov-status-tabs">
        <button v-for="t in TABS" :key="t.key" :class="{ on: f.status === t.key }" @click="switchStatus(t.key)">
          {{ t.label }}<i>{{ t.key === 'all' ? orders.length : countOf(t.key) }}</i>
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>
    <div v-else-if="!rows.length" class="empty card">
      <div class="icon">🧾</div><p>暂无符合条件的订单 —— 游客端在标品商城完成支付后，订单会实时出现在这里。</p>
    </div>

    <!-- 订单表格 -->
    <div v-else class="card ov-table-wrap">
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
              <div class="ov-no mono">{{ o.order_no }}</div>
              <div class="ov-time">{{ fmtTime(o.created_at) }}</div>
            </td>
            <td>
              <div class="ov-prod" v-for="it in o.items.slice(0, 2)" :key="it.sku_id + it.name">
                <span class="ov-cover" :style="{ background: it.cover?.gradient }">{{ it.cover?.emoji }}</span>
                <div class="ov-prod-info">
                  <b>{{ it.name }}</b>
                  <span>{{ it.sku_label }} × {{ it.qty }}</span>
                </div>
              </div>
              <div v-if="o.items.length > 2" class="ov-more">… 等 {{ o.items.length }} 项</div>
            </td>
            <td>
              <b class="ov-name">{{ o.contact?.name }}</b>
              <div class="ov-time">{{ o.contact?.phone }}</div>
            </td>
            <td><b class="ov-amount">¥{{ o.total }}</b></td>
            <td class="ov-pay">{{ o.pay_method || '—' }}</td>
            <td><span class="ov-state" :class="o.status.toLowerCase()">{{ STATUS_LABEL[o.status] }}</span></td>
            <td>
              <div class="ov-ops">
                <button class="op" @click="openDetail(o.id)">详情</button>
                <button v-if="o.status === 'PAID'" class="op ok" @click="complete(o)">核销完成</button>
                <button v-if="['PAID', 'USED'].includes(o.status)" class="op danger" @click="refund(o)">退款</button>
                <button v-if="o.status === 'UNPAID'" class="op warn" @click="cancelOrder(o)">取消</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 订单详情 -->
    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="modal-sheet ov-modal">
        <div class="modal-head">
          <h3>订单详情 <span class="ov-no inline">{{ detail.order_no }}</span></h3>
          <button class="modal-x" @click="detail = null">✕</button>
        </div>
        <div class="modal-body">
          <div class="od-top">
            <div class="od-status">
              <span class="ov-state" :class="detail.status.toLowerCase()">{{ STATUS_LABEL[detail.status] }}</span>
            </div>
            <div class="od-meta">
              <span>下单 <b>{{ fmtTime(detail.created_at) }}</b></span>
              <span>使用日期 <b>{{ detail.use_date || '—' }}</b></span>
              <span v-if="detail.paid_at">支付 <b>{{ fmtTime(detail.paid_at) }}</b> {{ detail.pay_method }}</span>
              <span v-if="detail.used_at">核销 <b>{{ fmtTime(detail.used_at) }}</b></span>
            </div>
          </div>

          <div v-for="it in detail.items" :key="it.sku_id + it.name" class="od-item">
            <div class="ov-cover big" :style="{ background: it.cover?.gradient }">{{ it.cover?.emoji }}</div>
            <div class="od-item-info">
              <b>{{ it.name }}</b>
              <span>{{ it.category }} · {{ it.city }} · {{ it.sku_label }}（{{ it.spec }}）× {{ it.qty }}</span>
              <span class="dim">核销方式：{{ it.pickup || '出示电子凭证' }}</span>
            </div>
            <div class="od-item-price">¥{{ it.unit_price * it.qty }}</div>
          </div>

          <div class="od-grid">
            <div class="od-cell"><span>预订人</span><b>{{ detail.contact?.name }} {{ detail.contact?.phone }}</b></div>
            <div class="od-cell"><span>出行人</span><b>{{ (detail.travelers || []).map(t => t.name).join('、') || '—' }}</b></div>
            <div class="od-cell"><span>备注</span><b>{{ detail.remark || '—' }}</b></div>
            <div class="od-cell"><span>来源</span><b>{{ detail.source === 'mall' ? '游客端商城' : detail.source }}</b></div>
            <div class="od-cell"><span>小计</span><b>¥{{ detail.subtotal }}</b></div>
            <div class="od-cell"><span>优惠</span><b>− ¥{{ detail.discount }}</b></div>
            <div class="od-cell total"><span>实付金额</span><b>¥{{ detail.total }}</b></div>
            <div class="od-cell" v-if="detail.refund_amount"><span>退款金额</span><b class="warn-txt">¥{{ detail.refund_amount }}</b></div>
          </div>

          <div v-if="detail.vouchers?.length" class="od-vouchers">
            <div class="od-sec">🎫 待核销凭证</div>
            <div v-for="v in detail.vouchers" :key="v" class="od-voucher">
              <b class="mono">{{ v }}</b><span>已随订单发给游客端</span>
              <button class="copy-mini" @click="copy(v)">复制</button>
            </div>
          </div>

          <div class="od-actions">
            <button v-if="detail.status === 'PAID'" class="btn btn-primary btn-sm" @click="complete(detail)">核销完成</button>
            <button v-if="detail.status === 'PAID'" class="btn btn-ghost btn-sm danger-txt" @click="refund(detail)">全额退款</button>
            <button v-if="detail.status === 'UNPAID'" class="btn btn-ghost btn-sm" @click="cancelOrder(detail)">取消订单</button>
            <button class="btn btn-ghost btn-sm" @click="copy(detail.order_no)">复制单号</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ordersApi } from '../../api'
import { toast } from '../../composables/toast'

const TABS = [
  { key: 'all', label: '全部' },
  { key: 'UNPAID', label: '待支付' },
  { key: 'PAID', label: '待使用' },
  { key: 'USED', label: '已完成' },
  { key: 'closed', label: '售后' },
]
const STATUS_LABEL = { UNPAID: '待支付', PAID: '待使用', USED: '已完成', CANCELLED: '已取消', REFUNDED: '已退款' }

const loading = ref(true)
const orders = ref([])
const rows = ref([])
const stat = ref({ by_status: {}, total_orders: 0, gmv: 0, today_new: 0, days: [] })
const detail = ref(null)
const f = reactive({ keyword: '', status: 'all' })
let maxGmv = 1

onMounted(loadAll)
async function loadAll() {
  loading.value = true
  try {
    const [o, s] = await Promise.all([ordersApi.list({}), ordersApi.stats()])
    orders.value = o.items || []
    stat.value = s
    maxGmv = Math.max(1, ...(s.days || []).map(d => d.gmv))
    applyFilter()
  } catch (e) {
    toast('订单加载失败：' + (e.message || e), 'err')
  } finally {
    loading.value = false
  }
}

function countOf(key) {
  if (key === 'all') return orders.value.length
  if (key === 'closed') return orders.value.filter(x => ['CANCELLED', 'REFUNDED'].includes(x.status)).length
  return orders.value.filter(x => x.status === key).length
}
function switchStatus(k) { f.status = k; applyFilter() }
function applyFilter() {
  let list = orders.value.slice()
  const k = f.keyword.trim().toLowerCase()
  if (k) list = list.filter(o =>
    o.order_no.toLowerCase().includes(k) ||
    (o.contact?.name || '').toLowerCase().includes(k) ||
    o.items.some(it => it.name.toLowerCase().includes(k)))
  if (f.status === 'closed') list = list.filter(x => ['CANCELLED', 'REFUNDED'].includes(x.status))
  else if (f.status !== 'all') list = list.filter(x => x.status === f.status)
  rows.value = list
}
function barH(v) { return Math.max(4, Math.round((v / maxGmv) * 56)) + 'px' }

function fmtTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
function copy(text) {
  navigator.clipboard?.writeText(String(text)).then(() => toast('已复制', 'ok')).catch(() => toast('复制失败', 'err'))
}

async function openDetail(id) {
  try {
    const r = await ordersApi.detail(id)
    detail.value = r.order
  } catch (e) {
    toast('详情加载失败：' + (e.message || e), 'err')
  }
}

async function complete(o) {
  if (!window.confirm(`确认核销完成订单 ${o.order_no}？`)) return
  try {
    const r = await ordersApi.complete(o.id)
    Object.assign(o, r.order)
    detail.value = o.id === detail.value?.id ? r.order : detail.value
    toast('已核销，订单标记为已完成', 'ok')
    loadAll()
  } catch (e) {
    toast('操作失败：' + (e.message || e), 'err')
  }
}
async function refund(o) {
  if (!window.confirm(`确认对 ${o.order_no} 全额退款 ¥${o.total}？`)) return
  try {
    const r = await ordersApi.refund(o.id)
    Object.assign(o, r.order)
    detail.value = o.id === detail.value?.id ? r.order : detail.value
    toast('已退款，原路退回游客账户', 'ok')
    loadAll()
  } catch (e) {
    toast('退款失败：' + (e.message || e), 'err')
  }
}
async function cancelOrder(o) {
  if (!window.confirm(`确认取消订单 ${o.order_no}？`)) return
  try {
    const r = await ordersApi.cancel(o.id)
    Object.assign(o, r.order)
    detail.value = o.id === detail.value?.id ? r.order : detail.value
    toast('订单已取消', 'ok')
    loadAll()
  } catch (e) {
    toast('取消失败：' + (e.message || e), 'err')
  }
}
</script>

<style scoped>
.page-actions { display: flex; gap: 10px; }
.ov-stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 14px; }
.ov-stat { background: var(--bg-panel); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.ov-stat span { font-size: 12px; color: var(--text-faint); }
.ov-stat b { font-size: 23px; color: var(--text); font-family: var(--mono); }
.ov-stat i { font-size: 11px; color: var(--text-faint); font-style: normal; }
.ov-stat.ok b { color: var(--ok); }
.ov-stat.warn b { color: var(--warn); }
.ov-stat.gold b { color: var(--brand); }

.ov-chart { padding: 14px 18px; margin-bottom: 14px; display: flex; flex-direction: column; gap: 14px; }
.ov-chart-title { font-size: 13px; font-weight: 800; color: var(--text-dim); }
.ov-bars { display: flex; gap: 14px; align-items: flex-end; height: 108px; padding: 0 6px; }
.ov-bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }
.ov-bar-label { font-size: 10px; color: var(--text-faint); font-family: var(--mono); height: 14px; }
.ov-bar-track { width: 100%; max-width: 46px; height: 60px; display: flex; align-items: flex-end; justify-content: center; }
.ov-bar {
  width: 16px; border-radius: 5px 5px 0 0; background: linear-gradient(180deg, var(--brand), var(--brand-dim));
  transition: height .3s; min-height: 4px;
}
.ov-bar-date { margin-top: 6px; font-size: 11px; color: var(--text-faint); font-family: var(--mono); }

.ov-toolbar { display: flex; gap: 12px; align-items: center; padding: 10px 14px; margin-bottom: 14px; flex-wrap: wrap; }
.ov-search { position: relative; flex: 1; min-width: 220px; }
.ov-search .s-ico { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-faint); }
.ov-search input {
  width: 100%; background: var(--bg-panel); border: 1px solid var(--line); color: var(--text);
  border-radius: 8px; padding: 8px 12px 8px 34px; font-size: 13px; box-sizing: border-box;
}
.ov-status-tabs { display: flex; gap: 2px; background: var(--bg-panel); padding: 3px; border-radius: 9px; overflow-x: auto; }
.ov-status-tabs button {
  border: none; background: transparent; color: var(--text-faint); padding: 7px 12px;
  border-radius: 7px; cursor: pointer; font-size: 12.5px; font-family: inherit; white-space: nowrap;
}
.ov-status-tabs button i { font-style: normal; font-size: 11px; margin-left: 4px; opacity: .8; font-family: var(--mono); }
.ov-status-tabs button.on { background: var(--brand-dim); color: #04121F; font-weight: 700; }

.ov-table-wrap { padding: 4px 6px; }
.mono { font-family: var(--mono); }
.ov-no { color: var(--text); font-size: 12.5px; font-weight: 600; }
.ov-no.inline { display: inline; margin-left: 8px; color: var(--text-faint); font-size: 12px; }
.ov-time { color: var(--text-faint); font-size: 11px; margin-top: 2px; font-family: var(--mono); }
.ov-prod { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.ov-prod:last-child { margin-bottom: 0; }
.ov-cover {
  width: 28px; height: 28px; border-radius: 7px; flex: none;
  display: flex; align-items: center; justify-content: center; font-size: 15px;
}
.ov-cover.big { width: 40px; height: 40px; font-size: 20px; border-radius: 9px; }
.ov-prod-info { display: flex; flex-direction: column; min-width: 0; }
.ov-prod-info b { color: var(--text); font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }
.ov-prod-info span { color: var(--text-faint); font-size: 11px; }
.ov-more { color: var(--text-faint); font-size: 11px; }
.ov-name { color: var(--text); font-size: 13px; }
.ov-amount { color: var(--warn); font-family: var(--mono); }
.ov-pay { color: var(--text-dim); font-size: 12px; }

.ov-state { font-size: 12px; padding: 3px 11px; border-radius: 999px; font-weight: 600; white-space: nowrap; }
.ov-state.unpaid { background: rgba(251, 191, 36, .14); color: var(--warn); }
.ov-state.paid { background: rgba(52, 211, 153, .14); color: var(--ok); }
.ov-state.used { background: rgba(167, 139, 250, .16); color: var(--purple); }
.ov-state.cancelled, .ov-state.refunded { background: rgba(248, 113, 113, .13); color: var(--danger); }
.ov-ops { display: flex; gap: 9px; justify-content: flex-end; white-space: nowrap; }
.op { background: none; border: none; color: var(--brand); cursor: pointer; font-size: 12.5px; }
.op:hover { text-decoration: underline; }
.op.ok { color: var(--ok); }
.op.warn { color: var(--warn); }
.op.danger { color: var(--danger); }

.modal-mask {
  position: fixed; inset: 0; background: rgba(2, 6, 23, .62); backdrop-filter: blur(2px); z-index: 250;
  display: flex; align-items: center; justify-content: center; padding: 24px;
}
.modal-sheet { width: 640px; max-width: 100%; max-height: 88vh; background: var(--bg-panel); border: 1px solid var(--line); border-radius: 16px; display: flex; flex-direction: column; overflow: hidden; }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; border-bottom: 1px solid var(--line); }
.modal-head h3 { margin: 0; font-size: 15px; color: var(--text); }
.modal-x { background: var(--bg-raised); border: 1px solid var(--line); color: var(--text-dim); border-radius: 8px; width: 28px; height: 28px; cursor: pointer; }
.modal-body { padding: 16px 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; }
.od-top { display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.od-meta { display: flex; flex-direction: column; gap: 3px; font-size: 12px; color: var(--text-faint); align-items: flex-end; }
.od-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-top: 1px dashed var(--line); }
.od-item-info { flex: 1; display: flex; flex-direction: column; gap: 3px; }
.od-item-info b { color: var(--text); font-size: 14px; }
.od-item-info span { color: var(--text-dim); font-size: 12px; }
.dim { color: var(--text-faint); }
.od-item-price { color: var(--warn); font-family: var(--mono); }
.od-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 18px; }
.od-cell { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px dashed var(--line); font-size: 13px; }
.od-cell span { color: var(--text-faint); }
.od-cell b { color: var(--text); }
.od-cell.total b { color: var(--warn); }
.warn-txt { color: var(--danger) !important; }
.od-vouchers { display: flex; flex-direction: column; gap: 8px; }
.od-sec { font-size: 13px; font-weight: 800; color: var(--text); }
.od-voucher {
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  border: 1.5px dashed var(--brand-dim); border-radius: 10px; background: rgba(14, 165, 233, .07);
}
.od-voucher b { color: var(--brand); font-size: 16px; }
.od-voucher span { color: var(--text-faint); font-size: 11.5px; flex: 1; }
.copy-mini { background: var(--bg-raised); border: 1px solid var(--line); color: var(--brand); border-radius: 6px; padding: 3px 10px; font-size: 11.5px; cursor: pointer; }
.od-actions { display: flex; gap: 10px; justify-content: flex-end; border-top: 1px solid var(--line); padding-top: 12px; }
.danger-txt { color: var(--danger) !important; }
</style>
