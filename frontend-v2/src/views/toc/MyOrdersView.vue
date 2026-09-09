<template>
  <div class="container mo">
    <div class="mo-head">
      <h1>🧾 我的订单</h1>
      <p>整订的线路方案都在这里：出行凭证、退改都在订单里</p>
    </div>

    <div class="tabs">
      <button v-for="t in TABS" :key="t.key" class="tab" :class="{ on: status === t.key }" @click="setTab(t.key)">
        {{ t.name }}<i v-if="countBy(t.key)"> {{ countBy(t.key) }}</i>
      </button>
    </div>

    <div v-if="loading" class="load-wrap"><div class="spinner"></div></div>

    <template v-else>
      <div v-if="!orders.length" class="empty card big">
        <div class="icon">🧳</div>
        <p>还没有订单。</p>
        <p class="sub">去方案馆挑一条排好的线路，整订出发吧</p>
        <router-link :to="{ name: 'malls' }" class="btn btn-primary">去逛方案</router-link>
      </div>

      <div v-else class="list">
        <div v-for="o in orders" :key="o.id" class="order card" :class="'st-' + o.status">
          <div class="o-top">
            <div class="o-no">订单号 {{ o.order_no }} · {{ fmtDT(o.created_at) }} 下单</div>
            <span class="o-status">{{ statusText(o.status) }}</span>
          </div>

          <div v-for="it in o.items" :key="it.sku_id" class="o-item">
            <span class="oi-cover" :style="{ background: it.cover?.gradient || 'linear-gradient(135deg,#94A3B8,#64748B)' }">{{ it.cover?.emoji || '🧭' }}</span>
            <div class="oi-info">
              <div class="oi-name">{{ it.name }}</div>
              <div class="oi-meta">
                <span>{{ it.category }} · {{ it.city }}</span>
                <span>{{ it.days }} 日方案 · {{ it.travelers || it.qty }} 人</span>
                <span v-if="o.use_date || o.start_date">📅 {{ fmtDate(o.use_date || o.start_date) }} 出发</span>
              </div>
              <div class="oi-tags">
                <span class="ot-voucher" v-if="o.status === 'PAID' || o.status === 'USED'">🎫 电子凭证：核销码 {{ o.voucher_no }}</span>
                <span class="ot-refund" v-else-if="o.status === 'UNPAID'">未支付 · {{ it.refund }}</span>
              </div>
            </div>
            <div class="oi-price">
              <div>¥{{ it.unit_price }}<span> × {{ it.travelers || it.qty }}人</span></div>
              <b>¥{{ o.amount }}</b>
            </div>
            <button class="btn btn-ghost btn-sm" @click="expanded = expanded === o.id ? '' : o.id">
              {{ expanded === o.id ? '收起 ▲' : '详情 ▾' }}
            </button>
          </div>

          <div v-if="expanded === o.id" class="o-detail">
            <div class="od-row"><span>费用说明</span><div><div class="od-spec" v-for="it in o.items" :key="it.sku_id">
              {{ it.name }} · 整订 {{ it.travelers || it.qty }} 人 × ¥{{ it.unit_price }} = ¥{{ o.amount }}
            </div><p class="od-tip">费用包含每日点位门票 / {{ o.items[0]?.days > 1 ? '住宿含早 / ' : '' }}出行保障；不含往返大交通</p></div></div>
            <div class="od-row"><span>集合方式</span><div>{{ o.items[0]?.pickup || '导游在首站集合点等待，凭电子凭证核销' }}</div></div>
            <div v-if="o.contact" class="od-row"><span>联系人</span><div>{{ o.contact.name }} {{ o.contact.phone }}</div></div>
            <div class="od-row"><span>出行保障</span><div>{{ o.items[0]?.refund || '出行前 1 天 18:00 前可全额退' }}</div></div>

            <div class="od-actions">
              <template v-if="o.status === 'UNPAID'">
                <button class="btn btn-ghost btn-sm" @click="cancelOrder(o)">取消订单</button>
                <button class="btn btn-primary btn-sm" @click="openPay(o)">去支付 ¥{{ o.amount }}</button>
              </template>
              <template v-if="o.status === 'PAID' || o.status === 'USED'">
                <button class="btn btn-ghost btn-sm" @click="share(o)">🔗 分享行程</button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 收银台（补付） -->
    <div v-if="payOrder" class="modal-mask" @click.self="payOrder = null">
      <div class="modal card">
        <div class="modal-title">补付尾款 · {{ payOrder.order_no }}</div>
        <div class="pay-amount">¥{{ payOrder.amount }}</div>
        <div class="pay-methods">
          <button v-for="m in METHODS" :key="m.key" class="pay-method" :class="{ on: method === m.key }" @click="method = m.key">
            <span>{{ m.ico }}</span><span>{{ m.name }}</span>
          </button>
        </div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="payOrder = null">取消</button>
          <button class="btn btn-primary" :disabled="paying" @click="doPay">
            <span v-if="paying" class="spinner"></span>确认支付
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ordersApi } from '../../api'
import { toast } from '../../composables/toast'

const route = useRoute()
const router = useRouter()
const TABS = [
  { key: '', name: '全部' }, { key: 'UNPAID', name: '待支付' },
  { key: 'PAID', name: '待出行' }, { key: 'USED', name: '已完成' }, { key: 'CANCELLED', name: '已取消' },
]
const METHODS = [
  { key: 'wechat', name: '微信支付', ico: '💚' },
  { key: 'alipay', name: '支付宝', ico: '🔷' },
  { key: 'card', name: '银行卡', ico: '💳' },
]
const STATUS_TEXT = { UNPAID: '待支付', PAID: '待出行', USED: '已完成', CANCELLED: '已取消' }
const all = ref([])
const orders = ref([])
const status = ref(String(route.query.status || ''))
const loading = ref(true)
const expanded = ref('')
const payOrder = ref(null)
const method = ref('wechat')
const paying = ref(false)

const countBy = (k) => k ? all.value.filter(o => o.status === k).length : all.value.length
function statusText(s) { return STATUS_TEXT[s] || s }
function setTab(k) {
  status.value = k
  expanded.value = ''
  router.replace({ name: 'my-orders', query: k ? { status: k } : {} })
  filter()
}
function filter() {
  orders.value = status.value ? all.value.filter(o => o.status === status.value) : all.value.slice()
}

function fmtDate(v) {
  if (!v) return '—'
  const d = new Date(v)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function fmtDT(v) {
  if (!v) return ''
  return fmtDate(v).slice(5)
}

async function load() {
  loading.value = true
  try {
    const r = await ordersApi.list({})
    all.value = r.items || []
    filter()
  } finally { loading.value = false }
}
function openPay(o) { payOrder.value = o; method.value = 'wechat' }
async function doPay() {
  if (!payOrder.value) return
  paying.value = true
  try {
    const r = await ordersApi.pay(payOrder.value.order_id || payOrder.value.id, method.value)
    toast('支付成功，凭证已更新', 'ok')
    payOrder.value = null
    await load()
  } catch (e) { toast('支付失败：' + (e.message || e), 'err') } finally { paying.value = false }
}
async function cancelOrder(o) {
  try {
    await ordersApi.cancel(o.order_id || o.id, '游客主动取消')
    toast('订单已取消', 'ok')
    await load()
  } catch (e) { toast('取消失败：' + (e.message || e), 'err') }
}
function share(o) {
  const it = o.items[0]
  if (!it) return
  const url = location.origin + location.pathname + '#/malls/product/' + it.product_id
  if (navigator.clipboard) navigator.clipboard.writeText(url).catch(() => {})
  toast('方案链接已复制，可分享', 'ok')
}

onMounted(load)
</script>

<style scoped>
.mo { max-width: 880px; padding: 26px 0 50px; }
.mo-head h1 { font-size: 24px; font-weight: 900; color: var(--ink-900); margin: 0; }
.mo-head p { font-size: 13px; color: var(--ink-500); margin: 4px 0 20px; }
.tabs { display: flex; gap: 4px; border-bottom: 2px solid var(--ink-100); margin-bottom: 18px; }
.tab { border: none; background: none; padding: 10px 16px; font-size: 14px; color: var(--ink-500); cursor: pointer; font-weight: 600; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab i { font-style: normal; font-size: 11.5px; color: var(--ink-400); }
.tab.on { color: var(--brand-700); border-color: var(--brand-600); font-weight: 800; }
.load-wrap { text-align: center; padding: 70px 0; }
.list { display: flex; flex-direction: column; gap: 12px; }
.order { padding: 14px 20px; border-left: 3px solid var(--ink-200); }
.st-UNPAID { border-left-color: var(--accent-500); }
.st-PAID { border-left-color: var(--brand-500); }
.st-USED { border-left-color: var(--ok-700, #16a34a); }
.st-CANCELLED { border-left-color: var(--ink-300); opacity: .72; }
.o-top { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--ink-400); padding-bottom: 8px; border-bottom: 1px dashed var(--ink-100); }
.o-status { font-weight: 800; font-size: 12.5px; }
.st-UNPAID .o-status { color: var(--accent-600); }
.st-PAID .o-status { color: var(--brand-600); }
.st-USED .o-status { color: var(--ok-700, #16a34a); }
.o-item { display: flex; align-items: center; gap: 12px; padding: 12px 0; }
.oi-cover { width: 58px; height: 46px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 26px; flex: none; }
.oi-info { flex: 1; min-width: 0; }
.oi-name { font-weight: 800; font-size: 15px; color: var(--ink-900); }
.oi-meta { display: flex; gap: 12px; font-size: 12px; color: var(--ink-500); margin-top: 4px; flex-wrap: wrap; }
.oi-tags { margin-top: 6px; }
.ot-voucher { font-size: 11.5px; color: var(--ok-700, #15803d); background: var(--ok-50, #ecfdf5); padding: 2px 8px; border-radius: 4px; }
.ot-refund { font-size: 11px; color: var(--ink-400); }
.oi-price { text-align: right; font-size: 12px; color: var(--ink-400); white-space: nowrap; }
.oi-price b { display: block; font-size: 18px; color: var(--danger); margin-top: 3px; }
.o-detail { border-top: 1px dashed var(--ink-200); padding: 12px 2px; background: var(--ink-50); border-radius: 0 0 10px 10px; }
.od-row { display: grid; grid-template-columns: 96px 1fr; gap: 10px; font-size: 12.5px; padding: 6px 12px; }
.od-row > span { color: var(--ink-400); }
.od-row > div { color: var(--ink-700); }
.od-spec { font-weight: 600; }
.od-tip { color: var(--ink-400); font-size: 11.5px; margin: 4px 0 0; }
.od-actions { display: flex; justify-content: flex-end; gap: 8px; padding: 8px 12px 2px; }

.modal-mask { position: fixed; inset: 0; background: rgba(10,15,25,.5); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal { width: 360px; padding: 24px; }
.modal-title { font-weight: 800; font-size: 16px; color: var(--ink-900); }
.pay-amount { text-align: center; font-size: 34px; font-weight: 900; color: var(--ink-900); margin: 12px 0 2px; }
.pay-methods { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 16px 0 4px; }
.pay-method { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 4px; border: 1.5px solid var(--ink-200); border-radius: 10px; cursor: pointer; font-size: 11.5px; color: var(--ink-600); background: #fff; }
.pay-method.on { border-color: var(--brand-500); color: var(--brand-700); background: var(--brand-50); }
.modal-actions { display: flex; gap: 10px; margin-top: 16px; }
.modal-actions .btn { flex: 1; }
</style>
