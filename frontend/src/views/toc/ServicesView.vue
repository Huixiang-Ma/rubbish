<script setup>
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { TRAINS, FLIGHTS, HOTELS, ATTRACTIONS, MERCHANTS, ENTERTAINMENTS } from './mock.js'
import { svcApi } from '../../api/index.js'

const TABS = [
  { key: 'train',    label: '🚄 火车票',   api: 'train' },
  { key: 'flight',   label: '✈ 机票',     api: 'flight' },
  { key: 'hotel',    label: '🏨 住宿',     api: null },
  { key: 'ticket',   label: '🎫 景点门票', api: 'attraction' },
  { key: 'food',     label: '🍜 餐饮商户', api: 'merchant' },
  { key: 'show',     label: '🎭 演艺娱乐', api: 'entertainment' },
]
const tab = ref('train')

const from = ref('上海')
const to = ref('苏州')

/* —— 数据：GET /api/services/{kind}（高德实时检索；未配置密钥/网络异常时回退演示数据） —— */
const TRAINS_R = ref(TRAINS)
const FLIGHTS_R = ref(FLIGHTS)
const HOTELS_R = ref(HOTELS)          // 后端服务窗无 hotel kind，保留静态酒店参考
const ATTRACTIONS_R = ref(ATTRACTIONS)
const MERCHANTS_R = ref(MERCHANTS)
const ENTERTAINMENTS_R = ref(ENTERTAINMENTS)
const svcNote = ref('')
const loading = ref(false)

async function loadKind(key) {
  const kind = TABS.find(t => t.key === key).api
  if (!kind) return
  loading.value = true
  try {
    const res = await svcApi.byKind(kind, to.value, from.value)
    svcNote.value = res.note || ''
    const rows = res.attractions || res.merchants || res.entertainments || res.tickets || res.flights || []
    if (rows.length) {
      if (kind === 'attraction') {
        ATTRACTIONS_R.value = rows.map(a => ({
          name: a.name, tags: a.tags || [], price: a.ticket_price ?? 0, mins: a.visit_minutes ?? 120,
          open: a.open_time || '以景区公告为准', addr: a.address || to.value,
        }))
      } else if (kind === 'merchant') {
        MERCHANTS_R.value = rows.map(m => ({
          name: m.name, cat: (m.tags && m.tags[0]) || '本地商户', dist: m.dist_km ?? m.distance ?? '—',
          hint: m.price_hint || (m.ticket_price != null ? `人均 ¥${m.ticket_price}` : '到店咨询'),
          addr: m.address || to.value,
        }))
      } else if (kind === 'entertainment') {
        ENTERTAINMENTS_R.value = rows.map(e => ({
          name: e.name, type: (e.tags && e.tags[0]) || '休闲体验', time: e.open_time || '以现场公告为准',
          loc: e.address || to.value, price: e.ticket_price != null ? `¥${e.ticket_price}` : '—',
        }))
      } else if (kind === 'train') {
        TRAINS_R.value = rows.map(t => ({
          no: t.no || t.train_no, from: t.from || from.value, to: t.to || to.value,
          dep: t.dep || t.dep_time || '—', arr: t.arr || t.arr_time || '—', dur: t.dur || t.duration || '—',
          price: t.price ?? '—', left: t.left || '—',
        }))
      } else if (kind === 'flight') {
        FLIGHTS_R.value = rows.map(f => ({
          no: f.no || f.flight_no, from: f.from || from.value, to: f.to || to.value,
          dep: f.dep || f.dep_time || '—', arr: f.arr || f.arr_time || '—', dur: f.dur || f.duration || '—',
          price: f.price ?? '—', discount: f.discount || '—',
        }))
      }
    }
  } catch { /* 回退演示数据 */ }
  loading.value = false
}

watch(tab, (k) => { loadKind(k) }, { immediate: true })

/* 预订点击埋点（POST /api/services/booking/click） */
function booking(kind) { svcApi.bookingClick(kind).catch(() => {}) }
</script>

<template>
  <div class="services">
    <div class="container">

      <header class="sv-head">
        <div>
          <h1>服务大厅</h1>
          <p class="sv-sub">行程之外的周边服务一站购齐 —— 数据来自景区/铁路/航司开放接口与核验商户库。</p>
        </div>
        <RouterLink to="/plans" class="btn btn-ghost btn-sm">我的行程</RouterLink>
      </header>

      <div class="sv-route card">
        <span class="route-label">路线</span>
        <input v-model="from" class="route-input" />
        <button class="swap">⇄</button>
        <input v-model="to" class="route-input" />
        <button class="btn btn-primary btn-sm" @click="loadKind(tab)">查询</button>
      </div>

      <nav class="sv-tabs card">
        <button v-for="t in TABS" :key="t.key" :class="{ on: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
      </nav>

      <!-- 火车票 -->
      <section v-if="tab === 'train'" class="card sv-card">
        <table class="sv-table">
          <thead><tr><th>车次</th><th>出发站</th><th>到达站</th><th>出发</th><th>到达</th><th>历时</th><th>余票</th><th>票价</th><th></th></tr></thead>
          <tbody>
            <tr v-for="t in TRAINS_R" :key="t.no">
              <td><b>{{ t.no }}</b></td><td>{{ t.from }}</td><td>{{ t.to }}</td>
              <td class="time">{{ t.dep }}</td><td class="time">{{ t.arr }}</td><td>{{ t.dur }}</td>
              <td><span class="left" :class="{ tight: t.left === '紧张' }">{{ t.left }}</span></td>
              <td class="price">¥{{ t.price }}</td>
              <td><button class="btn btn-ghost btn-sm" @click="booking('train')">预订</button></td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 机票 -->
      <section v-else-if="tab === 'flight'" class="card sv-card">
        <table class="sv-table">
          <thead><tr><th>航班</th><th>出发</th><th>到达</th><th>起降</th><th>历时</th><th>折扣</th><th>票价</th><th></th></tr></thead>
          <tbody>
            <tr v-for="f in FLIGHTS_R" :key="f.no">
              <td><b>{{ f.no }}</b></td><td>{{ f.from }}</td><td>{{ f.to }}</td>
              <td class="time">{{ f.dep }} - {{ f.arr }}</td><td>{{ f.dur }}</td>
              <td><span class="discount">{{ f.discount }}</span></td>
              <td class="price">¥{{ f.price }}</td>
              <td><button class="btn btn-ghost btn-sm" @click="booking('flight')">预订</button></td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 住宿 -->
      <section v-else-if="tab === 'hotel'" class="hotel-grid">
        <div v-for="h in HOTELS_R" :key="h.name" class="card hotel-card">
          <div class="h-head">
            <b>{{ h.name }}</b>
            <span class="h-price">{{ h.price }}</span>
          </div>
          <span class="h-tier">{{ h.tier }}</span>
          <span class="h-meta">距古城区 {{ h.dist }} km · {{ h.nights }}</span>
          <div class="h-foot">
            <span class="h-near">📍 临近 D1 动线</span>
            <button class="btn btn-primary btn-sm" @click="booking('hotel')">预订</button>
          </div>
        </div>
      </section>

      <!-- 门票 -->
      <section v-else-if="tab === 'ticket'" class="ticket-grid">
        <div v-for="a in ATTRACTIONS_R" :key="a.name" class="card ticket-card">
          <div class="t-head">
            <b>{{ a.name }}</b>
            <span class="t-price">¥{{ a.price }}</span>
          </div>
          <div class="t-tags"><span v-for="tg in a.tags" :key="tg" class="t-tag">{{ tg }}</span></div>
          <span class="t-meta">建议游玩 {{ Math.floor(a.mins / 60) }}h{{ a.mins % 60 ? (a.mins % 60) + 'm' : '' }} · 营业 {{ a.open }}</span>
          <span class="t-addr">📍 {{ a.addr }}</span>
          <button class="btn btn-primary btn-sm t-btn" @click="booking('attraction')">购买门票</button>
        </div>
      </section>

      <!-- 餐饮 -->
      <section v-else-if="tab === 'food'" class="food-grid">
        <div v-for="m in MERCHANTS_R" :key="m.name" class="card food-card">
          <div class="f-head">
            <b>{{ m.name }}</b>
            <span class="f-cat">{{ m.cat }}</span>
          </div>
          <span class="f-meta">{{ m.hint }} · 距 D1 动线 {{ m.dist }} km</span>
          <span class="f-addr">📍 {{ m.addr }}</span>
          <div class="f-foot">
            <span class="f-verified">✓ 核验商户</span>
            <button class="btn btn-ghost btn-sm" @click="booking('merchant')">预订餐位</button>
          </div>
        </div>
      </section>

      <!-- 演艺 -->
      <section v-else-if="tab === 'show'" class="show-grid">
        <div v-for="e in ENTERTAINMENTS_R" :key="e.name" class="card show-card">
          <b>{{ e.name }}</b>
          <span class="e-type">{{ e.type }}</span>
          <span class="e-meta">{{ e.time }} · {{ e.loc }}</span>
          <div class="e-foot">
            <span class="e-price">{{ e.price }}</span>
            <button class="btn btn-primary btn-sm" @click="booking('entertainment')">订座</button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.services { padding: var(--s-7) 0 var(--s-9); }
.sv-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: var(--s-5); flex-wrap: wrap; gap: var(--s-3); }
.sv-head h1 { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; }
.sv-sub { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-3); max-width: 560px; }

.sv-route { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-4) var(--s-5); margin-bottom: var(--s-4); }
.route-label { font-size: var(--fs-xs); color: var(--text-3); font-weight: var(--fw-bold); flex: none; }
.route-input { width: 130px; text-align: center; font-weight: var(--fw-bold); }
.swap { border: none; background: var(--surface-2); border-radius: 50%; width: 30px; height: 30px; cursor: pointer; color: var(--accent); }
.sv-route .btn { margin-left: auto; }

.sv-tabs { display: flex; gap: 2px; padding: 4px; width: fit-content; max-width: 100%; overflow-x: auto; margin-bottom: var(--s-4); }
.sv-tabs button { border: none; background: transparent; padding: 8px var(--s-4); border-radius: calc(var(--r) - 3px); font-size: var(--fs-sm); color: var(--text-3); white-space: nowrap; }
.sv-tabs button.on { background: var(--surface-2); color: var(--text); font-weight: var(--fw-bold); }

.sv-card { padding: var(--s-2) var(--s-4) var(--s-4); overflow-x: auto; }
.sv-table { width: 100%; border-collapse: collapse; font-size: var(--fs-sm); }
.sv-table th { text-align: left; font-size: var(--fs-xs); color: var(--text-faint); font-weight: var(--fw-medium); padding: var(--s-3) var(--s-2); border-bottom: 1px solid var(--border-soft); white-space: nowrap; }
.sv-table td { padding: var(--s-3) var(--s-2); border-bottom: 1px solid var(--border-soft); color: var(--text-2); white-space: nowrap; }
.sv-table tr:last-child td { border-bottom: none; }
.sv-table b { color: var(--text); }
.time { font-variant-numeric: tabular-nums; }
.left { font-size: var(--fs-xs); color: #4C7A5A; font-weight: var(--fw-bold); }
.left.tight { color: #B0685C; }
.discount { font-size: var(--fs-xs); color: #9A7B54; background: #F5EFE7; padding: 2px 8px; border-radius: var(--r-sm); }
.price { color: #B0685C; font-weight: var(--fw-bold); }

.hotel-grid, .ticket-grid, .food-grid, .show-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--s-4); }
.hotel-card, .ticket-card, .food-card, .show-card { padding: var(--s-5); display: flex; flex-direction: column; gap: 6px; }
.h-head, .t-head, .f-head, .e-foot { display: flex; justify-content: space-between; align-items: center; gap: var(--s-2); }
.h-head b, .t-head b, .f-head b, .show-card b { font-size: var(--fs-sm); }
.h-price, .t-price, .e-price { font-size: var(--fs-sm); color: #B0685C; font-weight: var(--fw-bold); }
.h-tier { font-size: var(--fs-xs); color: var(--accent-3, #7B8DA0); }
.h-meta, .t-meta, .t-addr, .f-meta, .f-addr, .e-meta { font-size: var(--fs-xs); color: var(--text-faint); }
.h-foot, .f-foot { display: flex; justify-content: space-between; align-items: center; margin-top: var(--s-2); }
.h-near { font-size: var(--fs-xs); color: var(--accent); }
.t-tags { display: flex; gap: 6px; }
.t-tag { font-size: 10px; color: var(--accent); border: 1px solid var(--accent); padding: 1px 8px; border-radius: var(--r-pill); }
.t-btn { margin-top: var(--s-2); align-self: flex-start; }
.f-cat { font-size: var(--fs-xs); color: var(--text-3); background: var(--surface-2); padding: 2px 8px; border-radius: var(--r-sm); }
.f-verified { font-size: var(--fs-xs); color: #4C7A5A; }
.e-type { font-size: var(--fs-xs); color: var(--accent-3, #7B8DA0); }
</style>
