<template>
  <div class="container co">
    <div class="co-head">
      <h1>确认订单</h1>
      <p>整订一条排好的线路 = 一次付款，全程无忧</p>
    </div>

    <!-- ============ 结算成功 ============ -->
    <div v-if="done" class="ok-panel card">
      <div class="ok-ico">🎉</div>
      <div class="ok-title">支付成功，方案已锁定</div>
      <p class="ok-sub">电子凭证已生成，出行前 1 天可全额退改</p>
      <div class="ok-order">
        <div class="oo-no">订单号 <b>{{ order.order_no }}</b></div>
        <div class="oo-line">{{ order.items[0]?.name }} · {{ order.items[0]?.days }} 日整订</div>
        <div class="oo-line">{{ fmtDate(order.use_date || order.start_date) }} 出发 · {{ order.items[0]?.travelers || order.items[0]?.qty }} 人</div>
        <div class="oo-total">实付 <b>¥{{ order.amount }}</b></div>
      </div>
      <div class="ok-actions">
        <router-link :to="{ name: 'my-orders' }" class="btn btn-primary">查看我的订单</router-link>
        <router-link :to="{ name: 'malls' }" class="btn btn-soft">继续逛方案</router-link>
      </div>
    </div>

    <template v-else>
      <template v-if="loading">
        <div class="load-wrap"><div class="spinner"></div><p>正在读取方案…</p></div>
      </template>

      <template v-else-if="!plan">
        <div class="empty card big">
          <div class="icon">🧭</div>
          <p>方案不存在或已下架，请回方案馆重新挑选。</p>
          <router-link :to="{ name: 'malls' }" class="btn btn-primary">返回方案馆</router-link>
        </div>
      </template>

      <template v-else>
        <div class="co-grid">
          <!-- 左：行程确认 -->
          <div class="co-main">
            <div class="card co-item">
              <div class="co-item-cover" :style="{ background: plan.cover.gradient }">{{ plan.cover.emoji }}</div>
              <div class="co-item-info">
                <div class="coi-cat">{{ plan.category }} · {{ plan.city }} · {{ plan.days }} 日线路方案</div>
                <div class="coi-name">{{ plan.title }}</div>
                <div class="coi-sub">{{ plan.subtitle }}</div>
                <div class="coi-tags">
                  <span>{{ plan.poi_count }} 个停留点位</span>
                  <span>🎫 门票食宿含于报价</span>
                  <span>↩️ {{ plan.refund_policy }}</span>
                </div>
              </div>
              <div class="coi-price">¥{{ plan.per_price }}<span>/人</span></div>
            </div>

            <div class="card co-section">
              <div class="co-section-title">🕐 出行信息</div>
              <div class="co-form-grid">
                <div class="co-field">
                  <label>出发日期 <b>*</b></label>
                  <select v-model="form.date" class="select">
                    <option v-for="d in dateOptions" :key="d.value" :value="d.value">{{ d.text }}</option>
                  </select>
                </div>
                <div class="co-field">
                  <label>出行人数（按人计价）<b>*</b></label>
                  <div class="stepper">
                    <button class="step-btn" :disabled="form.persons <= plan.min_persons" @click="form.persons--">−</button>
                    <div class="num">{{ form.persons }}</div>
                    <button class="step-btn" :disabled="form.persons >= 12" @click="form.persons++">＋</button>
                    <span class="unit">人 · {{ plan.days }} 日</span>
                  </div>
                </div>
                <div class="co-field">
                  <label>联系人姓名 <b>*</b></label>
                  <input v-model.trim="form.name" class="input" placeholder="出行人姓名" />
                </div>
                <div class="co-field">
                  <label>联系电话 <b>*</b></label>
                  <input v-model.trim="form.phone" class="input" placeholder="用于接收电子凭证" />
                </div>
              </div>
              <p class="co-note">下单成功后电子凭证会发送至该手机号；出行前企业导游会在首站集合点等待核销。</p>
            </div>

            <div class="card co-section">
              <div class="co-section-title">💰 费用包含</div>
              <ul class="co-include">
                <li v-for="(it, i) in plan.include" :key="i"><span>✓</span>{{ it }}</li>
              </ul>
              <div class="co-excl">
                <b>未包含：</b>{{ plan.exclude.join('、') }}
              </div>
            </div>
          </div>

          <!-- 右：结算栏 -->
          <aside class="co-side card">
            <div class="co-price-title">费用明细</div>
            <div class="co-line">
              <span>{{ plan.title }}（整订）</span>
              <span>¥{{ plan.per_price }} × {{ form.persons }} 人</span>
            </div>
            <div class="co-line dim">
              <span>含：门票 / 早晚餐推荐 / {{ plan.days > 1 ? '住宿' : '保障' }}</span>
              <span>—</span>
            </div>
            <div class="co-total">
              <span>应付合计</span>
              <span class="amt"><b>¥{{ total }}</b></span>
            </div>
            <button class="btn btn-primary btn-lg block" :disabled="submitting || !valid" @click="submit">
              <span v-if="submitting" class="spinner"></span>
              提交并去支付 ¥{{ total }}
            </button>
            <p class="co-safe">🔥 余 {{ plan.stock }} 席 · 成团后不可改期<br />企业直营 · 未出行可退 · 有问题找客服</p>
          </aside>
        </div>
      </template>
    </template>

    <!-- ============ 收银台弹层 ============ -->
    <div v-if="payOpen" class="modal-mask" @click.self="payOpen = false">
      <div class="modal card">
        <div class="modal-title">收银台</div>
        <div class="pay-amount">¥{{ total }}<span> 整订支付</span></div>
        <div class="pay-methods">
          <button v-for="m in PAY_METHODS" :key="m.key" class="pay-method" :class="{ on: method === m.key }"
                  @click="method = m.key">
            <span class="pm-ico">{{ m.ico }}</span>
            <span>{{ m.name }}</span>
          </button>
        </div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="payOpen = false">取消</button>
          <button class="btn btn-primary" :disabled="paying" @click="pay">
            <span v-if="paying" class="spinner"></span>确认支付 ¥{{ total }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { planShopApi, ordersApi } from '../../api'
import { toast } from '../../composables/toast'

const route = useRoute()
const router = useRouter()

const PAY_METHODS = [
  { key: 'wechat', name: '微信支付', ico: '💚' },
  { key: 'alipay', name: '支付宝', ico: '🔷' },
  { key: 'card', name: '银行卡', ico: '💳' },
]
const DAY_MARKS = ['日', '一', '二', '三', '四', '五', '六']

const plan = ref(null)
const loading = ref(true)
const order = ref(null)
const done = ref(false)
const payOpen = ref(false)
const paying = ref(false)
const submitting = ref(false)
const method = ref('wechat')
const form = reactive({ name: '', phone: '', date: '', persons: 2 })

const dateOptions = computed(() => {
  const out = []
  const today = new Date()
  for (let i = 1; i <= 30; i++) {
    const d = new Date(today.getTime() + i * 86400000)
    out.push({
      value: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
      text: `${i === 1 ? '明天' : i === 2 ? '后天' : `${d.getMonth() + 1}月${d.getDate()}日`}（周${DAY_MARKS[d.getDay()]}）`,
    })
  }
  return out
})
const total = computed(() => (plan.value ? plan.value.per_price * form.persons : 0))
const valid = computed(() => plan.value && !!form.date && form.name.trim() && /^1\d{10}$/.test(form.phone))

function fmtDate(v) {
  if (!v) return ''
  const d = new Date(v)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

async function load() {
  loading.value = true
  const id = route.query.product
  if (!id) { loading.value = false; return }
  try {
    const r = await planShopApi.detail(id)
    plan.value = r.plan
    form.persons = Math.max(plan.value.min_persons || 2, Number(route.query.persons) || 2)
    form.date = String(route.query.date || dateOptions.value[2]?.value || '')
  } catch (e) { plan.value = null } finally { loading.value = false }
}

async function submit() {
  if (!valid.value) { toast('请补齐日期、姓名和手机号', 'warn'); return }
  if ((plan.value.stock || 0) <= 0) { toast('该团期已满', 'warn'); return }
  submitting.value = true
  try {
    const payload = {
      product_id: plan.value.id,
      persons: form.persons,
      use_date: form.date,
      start_date: form.date,
      contact: { name: form.name, phone: form.phone },
    }
    const r = await ordersApi.create(payload)
    order.value = r.order
    payOpen.value = true
    toast('订单已创建，请完成支付', 'ok')
  } catch (e) {
    toast('下单失败：' + (e.message || e), 'err')
  } finally { submitting.value = false }
}

async function pay() {
  paying.value = true
  try {
    const r = await ordersApi.pay(order.value.order_id || order.value.id, method.value)
    order.value = r.order
    payOpen.value = false
    done.value = true
    toast('支付成功', 'ok')
  } catch (e) {
    toast('支付失败：' + (e.message || e), 'err')
  } finally { paying.value = false }
}

onMounted(load)
</script>

<style scoped>
.co { max-width: 1040px; padding: 26px 0 50px; }
.co-head h1 { font-size: 24px; font-weight: 900; color: var(--ink-900); margin: 0; }
.co-head p { font-size: 13px; color: var(--ink-500); margin: 4px 0 20px; }
.load-wrap { text-align: center; padding: 80px 0; color: var(--ink-500); }
.load-wrap .spinner { margin: 0 auto 12px; }

.co-grid { display: grid; grid-template-columns: 1fr 330px; gap: 16px; align-items: start; }
.co-main { display: flex; flex-direction: column; gap: 14px; }
.co-item { display: flex; gap: 14px; align-items: center; padding: 18px 20px; }
.co-item-cover { width: 96px; height: 72px; flex: none; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 44px; }
.coi-cat { font-size: 12px; color: var(--brand-700); font-weight: 700; }
.coi-name { font-size: 18px; font-weight: 800; color: var(--ink-900); margin-top: 3px; }
.coi-sub { font-size: 12.5px; color: var(--ink-500); margin-top: 2px; }
.coi-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.coi-tags span { font-size: 11px; color: var(--ink-500); background: var(--ink-100); border-radius: 4px; padding: 2px 7px; }
.coi-price { margin-left: auto; font-weight: 900; font-size: 22px; color: var(--danger); }
.coi-price span { font-size: 11.5px; font-weight: 500; color: var(--ink-400); }

.co-section { padding: 20px 24px; }
.co-section-title { font-weight: 800; font-size: 15px; color: var(--ink-900); margin-bottom: 14px; }
.co-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.co-field { display: flex; flex-direction: column; gap: 6px; }
.co-field label { font-size: 12.5px; font-weight: 700; color: var(--ink-600); }
.co-field label b { color: var(--danger); }
.stepper { display: flex; align-items: center; gap: 6px; }
.step-btn { width: 30px; height: 30px; border-radius: 7px; border: 1px solid var(--ink-300); background: #fff; cursor: pointer; font-size: 15px; }
.step-btn:disabled { opacity: .4; }
.stepper .num { min-width: 32px; text-align: center; font-weight: 800; }
.unit { font-size: 12px; color: var(--ink-400); margin-left: 6px; }
.co-note { font-size: 12px; color: var(--ink-400); margin: 12px 0 0; line-height: 1.6; background: var(--ink-50); border-radius: 8px; padding: 8px 12px; }
.co-include { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.co-include li { font-size: 13.5px; color: var(--ink-700); display: flex; gap: 8px; }
.co-include span { color: var(--ok-700, #15803D); font-weight: 900; }
.co-excl { font-size: 12.5px; color: var(--ink-400); margin-top: 14px; border-top: 1px dashed var(--ink-200); padding-top: 10px; }

.co-side { padding: 20px 22px; position: sticky; top: 96px; box-shadow: 0 10px 30px rgba(15,23,42,.08); }
.co-price-title { font-weight: 800; font-size: 15px; color: var(--ink-900); margin-bottom: 14px; }
.co-line { display: flex; justify-content: space-between; gap: 14px; font-size: 13px; color: var(--ink-700); padding: 7px 0; }
.co-line.dim { font-size: 12px; color: var(--ink-400); }
.co-total { display: flex; justify-content: space-between; align-items: baseline; border-top: 1px dashed var(--ink-200); margin-top: 10px; padding-top: 12px; font-size: 14px; color: var(--ink-700); font-weight: 700; }
.amt b { font-size: 26px; color: var(--danger); font-weight: 900; }
.block { width: 100%; margin-top: 14px; }
.co-safe { font-size: 11px; color: var(--ink-400); line-height: 1.7; text-align: center; margin: 10px 0 0; }

.ok-panel { text-align: center; padding: 60px 30px; max-width: 620px; margin: 40px auto; }
.ok-ico { font-size: 60px; }
.ok-title { font-size: 24px; font-weight: 900; color: var(--ink-900); margin-top: 12px; }
.ok-sub { color: var(--ink-500); font-size: 13.5px; margin: 6px 0 22px; }
.ok-order { background: var(--ink-50); border-radius: 12px; padding: 18px; max-width: 420px; margin: 0 auto 24px; text-align: left; }
.oo-no { font-size: 13px; color: var(--ink-400); }
.oo-no b { color: var(--ink-800); }
.oo-line { font-size: 13px; color: var(--ink-600); margin-top: 6px; }
.oo-total { display: flex; justify-content: space-between; margin-top: 12px; border-top: 1px dashed var(--ink-300); padding-top: 10px; font-size: 14px; color: var(--ink-700); }
.oo-total b { color: var(--danger); font-size: 22px; font-weight: 900; }
.ok-actions { display: flex; gap: 10px; justify-content: center; }

.modal-mask { position: fixed; inset: 0; background: rgba(10,15,25,.5); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal { width: 360px; padding: 24px; }
.modal-title { font-weight: 800; font-size: 17px; color: var(--ink-900); }
.pay-amount { text-align: center; font-size: 34px; font-weight: 900; color: var(--ink-900); margin: 14px 0 4px; }
.pay-amount span { font-size: 12.5px; font-weight: 500; color: var(--ink-400); }
.pay-methods { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 18px 0 4px; }
.pay-method { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 12px 4px; border: 1.5px solid var(--ink-200); border-radius: 10px; background: #fff; cursor: pointer; font-size: 11.5px; color: var(--ink-600); transition: all .12s; }
.pay-method.on { border-color: var(--brand-500); color: var(--brand-700); background: var(--brand-50); }
.pm-ico { font-size: 22px; }
.modal-actions { display: flex; gap: 10px; margin-top: 18px; }
.modal-actions .btn { flex: 1; }

@media (max-width: 860px) {
  .co-grid { grid-template-columns: 1fr; }
  .co-side { position: static; }
  .co-form-grid { grid-template-columns: 1fr; }
}
</style>
