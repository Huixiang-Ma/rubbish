<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { ORDERS } from './mock.js'
import { ordersApi } from '../../api/index.js'

const TABS = [
  { key: 'all', label: '全部' },
  { key: 'UNPAID', label: '待支付' },
  { key: 'PAID', label: '待出行' },
  { key: 'USED', label: '已完成' },
  { key: 'CANCELLED', label: '已取消' },
]
const tab = ref('all')
const STATUS_ZH = { UNPAID: '待支付', PAID: '待出行', USED: '已完成', CANCELLED: '已取消', REFUNDED: '已退款' }

// 订单：GET /api/orders（登录用户真实账本；未登录回退演示数据）
const ORDERS_LIST = ref(ORDERS)
const loading = ref(true)

function toOrderView(o) {
  const it = (o.items && o.items[0]) || {}
  return {
    id: o.id,
    no: o.order_no || o.id,
    placed: (o.created_at || '').replace('T', ' ').slice(0, 16),
    status: o.status,
    statusZh: STATUS_ZH[o.status] || o.status,
    planId: it.product_id || '',
    name: it.name || '整订方案',
    category: it.category || '', city: it.city || '', days: it.days || it.plan_days || 1,
    people: it.qty || it.travelers || 1,
    date: o.use_date || it.use_date || '—',
    code: (o.vouchers && o.vouchers[0]) || '',
    perPrice: it.unit_price || 0,
    paid: o.status === 'UNPAID' ? 0 : (o.total ?? o.amount ?? 0),
    fee: it.refund || '出行前 48 小时外可免费取消',
    meet: it.pickup || '行程起点集合（下单后客服确认具体点位）',
    contact: o.contact ? `${o.contact.name || '—'} ${o.contact.phone || ''}` : '—',
    cover: it.cover || null,
    items: o.items || [],
  }
}

onMounted(async () => {
  try {
    const res = await ordersApi.list({ page: 1, page_size: 100 })
    const rows = (res && res.items) || []
    if (rows.length || res) ORDERS_LIST.value = rows.map(toOrderView)
  } catch { /* 未登录/网络异常：回退演示订单 */ }
  loading.value = false
})

const count = (k) => k === 'all' ? ORDERS_LIST.value.length : ORDERS_LIST.value.filter(o => o.status === k).length
const list = computed(() => tab.value === 'all' ? ORDERS_LIST.value : ORDERS_LIST.value.filter(o => o.status === tab.value))

const expanded = ref({})
const toggleEx = (id) => expanded.value[id] = !expanded.value[id]

/* 订单分享：复制订单页链接 */
function shareOrder(o) {
  const url = `${location.origin}${location.pathname}#/orders`
  navigator.clipboard?.writeText(`我的订单 ${o.no}：${url}`).then(() => {}, () => {})
}

/* 补付/支付：POST /api/orders/{id}/pay */
const paying = ref(null)
const payBusy = ref(false)
const payMethod = ref('wechat')
function payNow(o) { paying.value = o }
async function confirmPay() {
  if (!paying.value || payBusy.value) return
  payBusy.value = true
  try {
    await ordersApi.pay(paying.value.id, { method: payMethod.value === 'alipay' ? '支付宝' : '微信支付' })
    const o = ORDERS_LIST.value.find(x => x.id === paying.value.id)
    if (o) { o.status = 'PAID'; o.statusZh = '待出行'; o.paid = o.perPrice * o.people }
    paying.value = null
  } catch { paying.value = null } finally { payBusy.value = false }
}
/* 取消 / 退改 */
async function cancelOrder(o) {
  try { await ordersApi.cancel(o.id, '用户取消'); o.status = 'CANCELLED'; o.statusZh = '已取消' } catch {}
}
async function refundOrder(o) {
  try { await ordersApi.refund(o.id); o.status = 'REFUNDED'; o.statusZh = '已退款' } catch {}
}
</script>

<template>
  <div class="orders">
    <div class="container">

      <header class="od-head">
        <div>
          <h1>我的订单</h1>
          <p class="od-sub">共 {{ ORDERS_LIST.length }} 笔订单 · 一处管理整订方案与电子凭证</p>
        </div>
        <RouterLink to="/malls" class="btn btn-ghost btn-sm">继续逛方案馆</RouterLink>
      </header>

      <nav class="od-tabs card">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">
          {{ t.label }} <i>{{ count(t.key) }}</i>
        </button>
      </nav>

      <div class="od-list">
        <section v-for="o in list" :key="o.id" class="card od-card">
          <div class="od-top">
            <span class="od-no">订单号 {{ o.id }}</span>
            <span class="od-time">{{ o.placed }}</span>
            <span class="od-status" :class="o.status.toLowerCase()">{{ o.statusZh }}</span>
          </div>

          <div class="od-body">
            <RouterLink :to="`/malls/product/${o.planId}`" class="od-cover" :style="{ background: (o.cover && o.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)' }">
              <span>{{ (o.cover && o.cover.emoji) || "🧭" }}</span>
            </RouterLink>
            <div class="od-info">
              <RouterLink :to="`/malls/product/${o.planId}`" class="od-name">{{ o.name }}</RouterLink>
              <span class="od-meta">{{ o.category }} · {{ o.city }} · {{ o.days }} 天 · {{ o.people }} 人</span>
              <span class="od-date">出行日期 {{ o.date }}</span>
            </div>
            <div class="od-voucher" v-if="o.code">
              <span class="vc-label">电子凭证 · 核销码</span>
              <code class="vc-code">{{ o.code }}</code>
            </div>
            <div class="od-amount">
              <span class="od-unit">¥{{ o.perPrice.toLocaleString() }} × {{ o.people }}</span>
              <b class="od-paid">¥{{ o.paid ? o.paid.toLocaleString() : '—' }}</b>
            </div>
          </div>

          <div class="od-foot">
            <button class="link-btn" @click="toggleEx(o.id)">{{ expanded[o.id] ? '收起详情' : '展开详情' }}</button>
            <div class="od-actions">
              <template v-if="o.status === 'UNPAID'">
                <button class="btn btn-ghost btn-sm" @click="cancelOrder(o)">取消订单</button>
                <button class="btn btn-primary btn-sm" @click="payNow(o)">去支付</button>
              </template>
              <template v-else-if="o.status === 'PAID'">
                <button class="btn btn-ghost btn-sm" @click="refundOrder(o)">申请退改</button>
                <button class="btn btn-ghost btn-sm" @click="shareOrder(o)">↗ 分享</button>
              </template>
              <template v-else-if="o.status === 'USED'">
                <button class="btn btn-ghost btn-sm">晒行程</button>
                <button class="btn btn-ghost btn-sm">再来一单</button>
              </template>
              <span v-else class="od-cancel-note">{{ o.fee }}</span>
            </div>
          </div>

          <div v-if="expanded[o.id]" class="od-detail">
            <div><span>费用说明</span><b>{{ o.fee }}</b></div>
            <div><span>集合方式</span><b>{{ o.meet }}</b></div>
            <div><span>联系人</span><b>{{ o.contact }}</b></div>
            <div><span>出行保障</span><b>未出行可退 · 平台担保 · 7×24 管家</b></div>
          </div>
        </section>

        <div v-if="!list.length" class="card od-empty">
          <p>该状态下暂无订单</p>
          <RouterLink to="/malls" class="btn btn-primary btn-sm">去方案馆看看</RouterLink>
        </div>
      </div>
    </div>

    <!-- 补付/支付 modal -->
    <div v-if="paying" class="modal-mask" @click.self="paying = null">
      <div class="modal card">
        <h3>支付订单 {{ paying.id }}</h3>
        <div class="pay-line"><span>{{ paying.name }} · {{ paying.people }} 人</span><b>¥{{ (paying.perPrice * paying.people).toLocaleString() }}</b></div>
        <div class="pay-methods">
          <button :class="{ on: payMethod === 'wechat' }" @click="payMethod = 'wechat'"><span class="pm-ico">💚</span>微信支付</button>
          <button :class="{ on: payMethod === 'alipay' }" @click="payMethod = 'alipay'"><span class="pm-ico">🔷</span>支付宝</button>
        </div>
        <div class="modal-btns">
          <button class="btn btn-ghost btn-sm" @click="paying = null">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="payBusy" @click="confirmPay">确认支付</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.orders { padding: var(--s-7) 0 var(--s-9); }
.od-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: var(--s-5); flex-wrap: wrap; gap: var(--s-3); }
.od-head h1 { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; }
.od-sub { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-3); }

.od-tabs { display: flex; gap: 2px; padding: 4px; width: fit-content; max-width: 100%; overflow-x: auto; margin-bottom: var(--s-4); }
.od-tabs button { border: none; background: transparent; padding: 8px var(--s-4); border-radius: calc(var(--r) - 3px); font-size: var(--fs-sm); color: var(--text-3); white-space: nowrap; }
.od-tabs button.on { background: var(--surface-2); color: var(--text); font-weight: var(--fw-bold); }
.od-tabs i { font-style: normal; font-size: 10px; color: var(--text-faint); margin-left: 3px; }

.od-list { display: flex; flex-direction: column; gap: var(--s-4); }
.od-card { padding: var(--s-4) var(--s-5); }
.od-top { display: flex; align-items: center; gap: var(--s-4); padding-bottom: var(--s-3); border-bottom: 1px solid var(--border-soft); }
.od-no { font-size: var(--fs-xs); color: var(--text-2); font-weight: var(--fw-medium); }
.od-time { font-size: var(--fs-xs); color: var(--text-faint); }
.od-status { margin-left: auto; font-size: var(--fs-xs); font-weight: var(--fw-bold); }
.od-status.paid { color: #4C7A5A; }
.od-status.unpaid { color: #B0685C; }
.od-status.used { color: var(--text-faint); }
.od-status.cancelled { color: var(--text-faint); text-decoration: line-through; }

.od-body { display: flex; align-items: center; gap: var(--s-4); padding: var(--s-4) 0; flex-wrap: wrap; }
.od-cover { width: 84px; height: 64px; border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center; font-size: 24px; flex: none; text-decoration: none; }
.od-info { min-width: 200px; flex: 1; }
.od-name { font-size: var(--fs-sm); font-weight: var(--fw-bold); color: var(--text); text-decoration: none; }
.od-name:hover { color: var(--accent); }
.od-meta, .od-date { display: block; font-size: var(--fs-xs); color: var(--text-faint); margin-top: 3px; }
.od-voucher { text-align: center; flex: none; }
.vc-label { display: block; font-size: 10px; color: var(--text-faint); margin-bottom: 4px; }
.vc-code { font-size: var(--fs-sm); font-weight: var(--fw-bold); letter-spacing: .08em; color: var(--accent); background: #F4F6F1; border: 1px dashed var(--accent); padding: 4px 12px; border-radius: var(--r-sm); }
.od-amount { text-align: right; margin-left: auto; flex: none; }
.od-unit { display: block; font-size: var(--fs-xs); color: var(--text-faint); }
.od-paid { font-size: 18px; color: #B0685C; }

.od-foot { display: flex; align-items: center; gap: var(--s-3); padding-top: var(--s-3); border-top: 1px solid var(--border-soft); }
.link-btn { border: none; background: none; font-size: var(--fs-xs); color: var(--text-3); cursor: pointer; }
.link-btn:hover { color: var(--accent); }
.od-actions { margin-left: auto; display: flex; gap: var(--s-2); }
.od-cancel-note { font-size: var(--fs-xs); color: var(--text-faint); }

.od-detail { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--s-3); padding: var(--s-4); margin-top: var(--s-3); background: var(--surface-2); border-radius: var(--r); }
.od-detail > div { display: flex; flex-direction: column; gap: 3px; }
.od-detail span { font-size: var(--fs-xs); color: var(--text-faint); }
.od-detail b { font-size: var(--fs-xs); color: var(--text-2); font-weight: var(--fw-medium); }

.od-empty { text-align: center; padding: var(--s-8); color: var(--text-faint); font-size: var(--fs-sm); }
.od-empty .btn { margin-top: var(--s-3); }

.modal-mask { position: fixed; inset: 0; background: rgba(46,44,40,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { width: min(420px, 90vw); padding: var(--s-6); }
.modal h3 { font-size: var(--fs-md); margin-bottom: var(--s-4); }
.pay-line { display: flex; justify-content: space-between; font-size: var(--fs-sm); padding: var(--s-3) 0; }
.pay-line b { color: #B0685C; }
.pay-methods { display: flex; gap: var(--s-2); margin-bottom: var(--s-4); }
.pay-methods button { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid var(--border); background: var(--surface); border-radius: var(--r); padding: var(--s-3); font-size: var(--fs-sm); color: var(--text-2); cursor: pointer; }
.pay-methods button.on { border-color: var(--accent); background: #F4F6F1; color: var(--accent); font-weight: var(--fw-bold); }
.modal-btns { display: flex; justify-content: flex-end; gap: var(--s-2); }
</style>
