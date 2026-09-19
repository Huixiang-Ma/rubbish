<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { planById } from './mock.js'
import { planShopApi, ordersApi } from '../../api/index.js'
import { auth } from '../../stores/auth.js'

const route = useRoute()
const router = useRouter()

// 方案：优先路由 query 指定的方案 id（GET /api/plan-products/{id}），失败回退演示方案
const plan = ref(planById('p101'))
const skuId = ref('')

async function loadPlan() {
  const pid = route.query.plan
  if (!pid) return
  try {
    const res = await planShopApi.detail(pid)
    const raw = res.plan
    plan.value = {
      id: raw.id, name: raw.title || raw.name, category: raw.category || '', city: raw.city || '',
      days: raw.days || 1, pace: raw.pace_zh ? raw.pace_zh.replace('节奏', '') : (raw.pace || ''),
      perPrice: raw.per_price ?? raw.price_total ?? 0,
      emoji: (raw.cover && raw.cover.emoji) || '🧭',
      gradient: (raw.cover && raw.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)',
      badges: raw.badges || [], include: raw.include || [], minPersons: raw.min_persons || 2,
    }
    const skus = raw.skus || []
    if (skus.length) {
      const def = skus.find(sk => sk.default) || skus[0]
      skuId.value = route.query.sku && skus.some(sk => sk.sku_id === route.query.sku) ? route.query.sku : def.sku_id
    }
    people.value = Math.max(Number(route.query.people) || 2, raw.min_persons || 2)
    if (route.query.date) {
      // query 里是「MM-DD 周X」展示文案，转当年日期串供后端 use_date
      const m = String(route.query.date).match(/(\d{2})-(\d{2})/)
      if (m) date.value = `${new Date().getFullYear()}-${m[1]}-${m[2]}`
    }
  } catch { /* 回退演示方案 */ }
}

const date = ref(new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10))
const people = ref(2)
const name = ref('')
const phone = ref('')
const note = ref('')

const subtotal = computed(() => plan.value.perPrice * people.value)
const service = 0
const total = computed(() => subtotal.value + service)

/* 收银台：POST /api/orders 创建 → POST /api/orders/{id}/pay 支付回执 */
const paying = ref(false)
const payMethod = ref('wechat')
const PAID_METHODS = [
  { key: 'wechat', label: '微信支付', ico: '💚' },
  { key: 'alipay', label: '支付宝', ico: '🔷' },
  { key: 'bank', label: '银行卡', ico: '💳' },
]
const success = ref(false)
const orderId = ref('')
const errMsg = ref('')

async function loadDefaults() {
  if (!auth.isLogin) return
  try {
    const me = await fetch('/api/auth/me', { headers: { Authorization: `Bearer ${localStorage.getItem('wl_token')}` } })
    if (me.ok) {
      const j = await me.json()
      if (!name.value) name.value = j.username || ''
      if (!phone.value && /^1\d{10}$/.test(j.username || '')) phone.value = j.username
    }
  } catch { /* 忽略 */ }
}

onMounted(() => { loadPlan(); loadDefaults() })

const submitting = ref(false)
async function submit() {
  if (submitting.value) return
  errMsg.value = ''
  submitting.value = true
  try {
    if (!auth.isLogin) { router.push('/auth?redirect=' + encodeURIComponent(route.fullPath)); return }
    const res = await ordersApi.create({
      product_id: plan.value.id,
      persons: people.value,
      sku_id: skuId.value || undefined,
      use_date: date.value,
      contact: { name: name.value || '未填写', phone: phone.value },
    })
    orderId.value = res.order.id
    paying.value = true
  } catch (e) {
    errMsg.value = e.message || '下单失败,请稍后再试'
  } finally {
    submitting.value = false
  }
}

async function pay() {
  try {
    if (orderId.value) await ordersApi.pay(orderId.value, { method: payMethod.value })
    paying.value = false
    success.value = true
  } catch (e) {
    errMsg.value = e.message || '支付失败'
    paying.value = false
  }
}
</script>

<template>
  <div class="checkout">
    <div class="container">

      <!-- 支付成功 -->
      <div v-if="success" class="card success-card">
        <div class="sc-emoji">🎉</div>
        <h2>支付成功!</h2>
        <p class="sc-no">订单号 <code>{{ orderId }}</code></p>
        <div class="sc-info">
          <div><span>方案</span><b>{{ plan.name }}</b></div>
          <div><span>出行日期</span><b>{{ date }} · {{ people }} 人</b></div>
          <div><span>实付</span><b class="price">¥{{ total.toLocaleString() }}</b></div>
        </div>
        <div class="sc-btns">
          <RouterLink to="/orders" class="btn btn-primary">查看我的订单</RouterLink>
          <RouterLink to="/malls" class="btn btn-ghost">继续逛方案馆</RouterLink>
        </div>
      </div>

      <template v-else>
        <header class="ck-head">
          <h1>确认订单</h1>
          <RouterLink to="/malls" class="back">← 返回方案馆</RouterLink>
        </header>

        <div class="ck-grid">
          <div class="ck-main">
            <!-- 方案确认 -->
            <section class="card sec">
              <h4>方案确认</h4>
              <div class="plan-row">
                <div class="pr-cover" :style="{ background: plan.gradient }"><span>{{ plan.emoji }}</span></div>
                <div class="pr-info">
                  <b>{{ plan.name }}</b>
                  <span>{{ plan.category }} · {{ plan.city }} · {{ plan.days }} 天 · {{ plan.pace }}节奏</span>
                  <span class="pr-badges">
                    <i v-for="b in plan.badges" :key="b">{{ b }}</i>
                  </span>
                </div>
                <span class="pr-price">¥{{ plan.perPrice.toLocaleString() }} × {{ people }}人</span>
              </div>
            </section>

            <!-- 出行信息 -->
            <section class="card sec">
              <h4>出行信息</h4>
              <div class="f-grid">
                <label class="field"><span>出发日期</span><input v-model="date" type="date" /></label>
                <label class="field"><span>出行人数</span><input v-model.number="people" type="number" min="1" max="12" /></label>
                <label class="field"><span>联系人姓名</span><input v-model="name" placeholder="取票联系人" /></label>
                <label class="field"><span>联系电话</span><input v-model="phone" placeholder="用于接收电子凭证" /></label>
                <label class="field full"><span>备注(选填)</span><textarea v-model="note" rows="2" placeholder="饮食禁忌、儿童座椅等特殊需求"></textarea></label>
              </div>
            </section>

            <!-- 费用包含 -->
            <section class="card sec">
              <h4>费用包含</h4>
              <ul class="inc-list">
                <li v-for="i in plan.include" :key="i">✓ {{ i }}</li>
              </ul>
            </section>
          </div>

          <!-- 结算栏 -->
          <aside class="card ck-aside">
            <h4>费用明细</h4>
            <div class="fee-row"><span>方案单价</span><span>¥{{ plan.perPrice.toLocaleString() }}</span></div>
            <div class="fee-row"><span>人数</span><span>× {{ people }}</span></div>
            <div class="fee-row"><span>平台服务费</span><span>免费</span></div>
            <div class="fee-total"><span>应付合计</span><b>¥{{ total.toLocaleString() }}</b></div>
            <button class="btn btn-primary pay-btn" :disabled="submitting" @click="submit">{{ submitting ? '正在下单…' : '提交并支付' }}</button>
            <p v-if="errMsg" class="seat-tip" style="background:#F6EBE9;color:#B0685C">⚠ {{ errMsg }}</p>
            <p class="seat-tip">🎫 10-02 场次仅余 4 席,提交后锁定 15 分钟</p>
          </aside>
        </div>
      </template>
    </div>

    <!-- 收银台 -->
    <div v-if="paying" class="modal-mask" @click.self="paying = false">
      <div class="modal card">
        <h3>收银台 · 支付 ¥{{ total.toLocaleString() }}</h3>
        <div class="pay-methods">
          <button v-for="m in PAID_METHODS" :key="m.key" :class="{ on: payMethod === m.key }" @click="payMethod = m.key">
            <span class="pm-ico">{{ m.ico }}</span>{{ m.label }}
          </button>
        </div>
        <div class="modal-btns">
          <button class="btn btn-ghost btn-sm" @click="paying = false">取消</button>
          <button class="btn btn-primary btn-sm" @click="pay">确认支付 ¥{{ total.toLocaleString() }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.checkout { padding: var(--s-7) 0 var(--s-9); }
.ck-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--s-5); }
.ck-head h1 { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; }
.back { font-size: var(--fs-xs); color: var(--text-3); }

.ck-grid { display: grid; grid-template-columns: 1fr 320px; gap: var(--s-4); align-items: start; }
.ck-main { display: flex; flex-direction: column; gap: var(--s-4); }
.sec { padding: var(--s-5) var(--s-6); }
.sec h4 { font-size: var(--fs-md); margin-bottom: var(--s-4); }

.plan-row { display: flex; gap: var(--s-4); align-items: center; }
.pr-cover { width: 88px; height: 66px; border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center; font-size: 26px; flex: none; }
.pr-info b { display: block; font-size: var(--fs-sm); }
.pr-info > span { font-size: var(--fs-xs); color: var(--text-faint); display: block; margin-top: 3px; }
.pr-badges i { font-style: normal; font-size: 10px; color: var(--accent); border: 1px solid var(--accent); padding: 1px 6px; border-radius: var(--r-sm); margin-right: 4px; }
.pr-price { margin-left: auto; font-size: var(--fs-sm); color: #B0685C; font-weight: var(--fw-bold); flex: none; }

.f-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-4); }
.field { display: flex; flex-direction: column; gap: 6px; }
.field.full { grid-column: 1 / -1; }
.field span { font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--text-2); }
.inc-list { list-style: none; }
.inc-list li { font-size: var(--fs-sm); color: var(--text-2); padding: 4px 0; }

.ck-aside { padding: var(--s-5) var(--s-6); position: sticky; top: var(--s-5); }
.fee-row { display: flex; justify-content: space-between; font-size: var(--fs-sm); color: var(--text-3); padding: 6px 0; }
.fee-total { display: flex; justify-content: space-between; align-items: baseline; border-top: 1px dashed var(--border); margin-top: var(--s-3); padding-top: var(--s-3); font-size: var(--fs-sm); }
.fee-total b { font-size: 22px; color: #B0685C; }
.pay-btn { width: 100%; margin-top: var(--s-4); }
.seat-tip { margin-top: var(--s-3); font-size: var(--fs-xs); color: #9A7B54; background: #F5EFE7; padding: var(--s-2) var(--s-3); border-radius: var(--r-sm); text-align: center; }

/* 成功 */
.success-card { max-width: 460px; margin: var(--s-7) auto; padding: var(--s-8) var(--s-6); text-align: center; }
.sc-emoji { font-size: 48px; }
.sc-no { margin: var(--s-2) 0 var(--s-4); color: var(--text-3); font-size: var(--fs-sm); }
.sc-no code { background: var(--surface-2); padding: 2px 8px; border-radius: var(--r-sm); }
.sc-info { text-align: left; border-top: 1px solid var(--border-soft); border-bottom: 1px solid var(--border-soft); padding: var(--s-4) 0; margin-bottom: var(--s-4); }
.sc-info > div { display: flex; justify-content: space-between; padding: 4px 0; font-size: var(--fs-sm); }
.sc-info span { color: var(--text-3); }
.sc-info .price { color: #B0685C; font-size: 18px; }
.sc-btns { display: flex; gap: var(--s-3); justify-content: center; }

/* 收银台 */
.modal-mask { position: fixed; inset: 0; background: rgba(46,44,40,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { width: min(420px, 90vw); padding: var(--s-6); }
.modal h3 { font-size: var(--fs-md); margin-bottom: var(--s-4); }
.pay-methods { display: flex; gap: var(--s-2); margin-bottom: var(--s-4); }
.pay-methods button { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid var(--border); background: var(--surface); border-radius: var(--r); padding: var(--s-3); font-size: var(--fs-sm); color: var(--text-2); cursor: pointer; }
.pay-methods button.on { border-color: var(--accent); background: #F4F6F1; color: var(--accent); font-weight: var(--fw-bold); }
.pm-ico { font-size: 15px; }
.modal-btns { display: flex; justify-content: flex-end; gap: var(--s-2); }

@media (max-width: 900px) { .ck-grid { grid-template-columns: 1fr; } .f-grid { grid-template-columns: 1fr; } }
</style>
