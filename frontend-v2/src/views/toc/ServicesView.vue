<template>
  <div class="container svc-page">
    <div class="sec-title">旅行服务大厅</div>
    <p class="sec-desc">火车 / 机票 · 酒店 · 景点 · 商圈 · 娱乐，一站式查询，点击直达预订（含官方渠道指引）</p>

    <!-- 查询条件 -->
    <div class="card card-pad q-card">
      <div class="q-grid">
        <div class="field"><label>目的地 *</label>
          <input v-model.trim="q.destination" class="input" placeholder="北京市" /></div>
        <div class="field"><label>出发地</label>
          <input v-model.trim="q.origin" class="input" placeholder="上海" /></div>
        <div class="field"><label>天数</label>
          <select v-model.number="q.days" class="select"><option v-for="d in 14" :key="d" :value="d">{{ d }} 天</option></select></div>
        <div class="field" style="justify-content:flex-end">
          <button class="btn btn-primary" :disabled="searching || !q.destination" @click="searchAll">
            {{ searching ? '查询中…' : '🔍 一键查询' }}</button>
        </div>
      </div>
    </div>

    <template v-if="travel">
      <!-- 火车 -->
      <Section title="🚄 火车票" :source="travel.trains?.source" :note="travel.trains?.note">
        <template #extra>
          <span v-if="travel.trains?.guide?.route" class="tag tag-blue">{{ travel.trains.guide.route }}</span>
        </template>
        <TicketList :tickets="travel.trains?.tickets || []" kind="train" @book="onBook" />
        <ChannelList v-if="travel.trains?.guide?.channels" :channels="travel.trains.guide.channels" />
      </Section>

      <!-- 机票 -->
      <Section title="✈️ 机票" :source="travel.flights?.source" :note="travel.flights?.note">
        <TicketList :tickets="travel.flights?.flights || travel.flights?.tickets || []" kind="flight" @book="onBook" />
        <ChannelList v-if="travel.flights?.guide?.channels" :channels="travel.flights.guide.channels" />
      </Section>

      <!-- 酒店 -->
      <Section title="🏨 酒店" :source="travel.hotels?.source" :note="travel.hotels?.note">
        <div v-if="!(travel.hotels?.hotels || []).length" class="empty"><p>暂无数据</p></div>
        <div class="hotel-grid">
          <div v-for="(h, i) in travel.hotels?.hotels || []" :key="i" class="card h-card">
            <div class="h-name">{{ h.name }}</div>
            <div class="h-meta">
              <span class="tag tag-purple">{{ h.category || h.tier || '酒店' }}</span>
              <span v-if="h.distance_km" class="h-dist">距市中心 {{ h.distance_km }}km</span>
            </div>
            <div class="h-foot">
              <span v-if="h.nights" class="h-nights">{{ h.nights }}</span>
              <a v-if="h.booking_url" class="btn btn-primary btn-sm" :href="h.booking_url" target="_blank" rel="noopener" @click="onBook('flight')">预订</a>
            </div>
          </div>
        </div>
      </Section>
    </template>

    <template v-if="kinds.length">
      <!-- 景点 -->
      <Section v-if="attr" title="🎡 景点门票" :source="attr.source" :note="attr.note">
        <div v-if="!attr.attractions?.length" class="empty"><p>暂无数据</p></div>
        <div class="spot-grid">
          <div v-for="(a, i) in attr.attractions || []" :key="i" class="card s-card">
            <div class="s-name">{{ a.name }}</div>
            <div class="s-tags"><span v-for="t in (a.tags || []).slice(0, 3)" :key="t" class="tag tag-gray">{{ t }}</span></div>
            <div class="s-rows">
              <span v-if="a.ticket_price">🎫 ¥{{ a.ticket_price }}</span>
              <span v-if="a.visit_minutes">⏱ 约 {{ a.visit_minutes }} 分钟</span>
              <span v-if="a.open_time">🕘 {{ a.open_time }}</span>
            </div>
            <a v-if="a.booking_url" class="btn btn-soft btn-sm" style="margin-top:10px" :href="a.booking_url" target="_blank" rel="noopener" @click="onBook('attraction')">去购票</a>
          </div>
        </div>
      </Section>

      <!-- 商圈 -->
      <Section v-if="mer" title="🛍 商圈与美食" :source="mer.source" :note="mer.note">
        <div v-if="!mer.merchants?.length" class="empty"><p>暂无数据</p></div>
        <div class="mer-list">
          <div v-for="(m, i) in mer.merchants || []" :key="i" class="card m-card">
            <div class="m-name">{{ m.name }}</div>
            <div class="m-meta">
              <span class="tag tag-blue">{{ m.category }}</span>
              <span v-if="m.distance_km">📍 {{ m.distance_km }}km</span>
              <span v-if="m.price_hint">💰 {{ m.price_hint }}</span>
            </div>
            <div v-if="m.address" class="m-addr">{{ m.address }}</div>
          </div>
        </div>
      </Section>

      <!-- 娱乐 -->
      <Section v-if="ent" title="🎭 夜间娱乐" :source="ent.source" :note="ent.note">
        <div v-if="!ent.entertainments?.length" class="empty"><p>暂无数据</p></div>
        <div class="mer-list">
          <div v-for="(e, i) in ent.entertainments || []" :key="i" class="card m-card">
            <div class="m-name">{{ e.name }} <span class="tag tag-purple" style="margin-left:6px">{{ e.type }}</span></div>
            <div class="m-meta">
              <span v-if="e.time">🕒 {{ e.time }}</span>
              <span v-if="e.location">📍 {{ e.location }}</span>
              <span v-if="e.price">💰 {{ e.price }}</span>
            </div>
          </div>
        </div>
      </Section>
    </template>

    <div v-if="!travel && !searching && searched" class="empty card"><div class="icon">🔍</div><p>没有查到服务数据，换个目的地试试</p></div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { svcApi } from '../../api'
import { toast } from '../../composables/toast'
import Section from './panels/SvcSection.vue'
import TicketList from './panels/TicketList.vue'
import ChannelList from './panels/ChannelList.vue'

const q = reactive({ destination: '北京市', origin: '上海', days: 3 })
const searching = ref(false)
const searched = ref(false)
const travel = ref(null)
const attr = ref(null)
const mer = ref(null)
const ent = ref(null)
const kinds = computed(() => [attr.value, mer.value, ent.value].filter(Boolean))

async function searchAll() {
  searching.value = true
  try {
    const [t, a, m, e] = await Promise.allSettled([
      svcApi.travel(q.destination, q.origin, q.days),
      svcApi.byKind('attraction', q.destination, q.origin),
      svcApi.byKind('merchant', q.destination, q.origin),
      svcApi.byKind('entertainment', q.destination, q.origin),
    ])
    if (t.status === 'fulfilled') travel.value = t.value
    if (a.status === 'fulfilled') attr.value = a.value
    if (m.status === 'fulfilled') mer.value = m.value
    if (e.status === 'fulfilled') ent.value = e.value
    searched.value = true
  } finally { searching.value = false }
}

async function onBook(kind) {
  try { await svcApi.bookingClick(kind) } catch { /* 埋点失败不影响跳转 */ }
}
</script>

<style scoped>
.svc-page { padding-top: 32px; padding-bottom: 40px; }
.q-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.hotel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 13px; }
.h-card { padding: 18px 20px; }
.h-name { font-weight: 800; font-size: 15px; }
.h-meta { display: flex; align-items: center; gap: 9px; margin-top: 9px; flex-wrap: wrap; }
.h-dist { font-size: 12.5px; color: var(--ink-500); }
.h-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 13px; }
.h-nights { font-size: 12.5px; color: var(--ink-400); }
.spot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 13px; }
.s-card { padding: 18px 20px; }
.s-name { font-weight: 800; font-size: 15px; }
.s-tags { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
.s-rows { display: flex; flex-direction: column; gap: 4px; margin-top: 10px; font-size: 13px; color: var(--ink-500); }
.mer-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 13px; }
.m-card { padding: 18px 20px; }
.m-name { font-weight: 800; font-size: 15px; display: flex; align-items: center; flex-wrap: wrap; }
.m-meta { display: flex; gap: 10px; margin-top: 9px; font-size: 12.5px; color: var(--ink-500); flex-wrap: wrap; }
.m-addr { font-size: 12.5px; color: var(--ink-400); margin-top: 7px; }
</style>
