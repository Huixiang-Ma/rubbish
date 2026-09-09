<template>
  <div class="container svc-page">
    <div class="svc-head">
      <div>
        <div class="sec-title">旅行服务大厅</div>
        <p class="sec-desc">火车 / 机票 / 酒店 / 景点 / 商圈美食 / 娱乐全部窗口一件查，点击直达预订（含官方渠道指引）</p>
      </div>
      <div class="svc-badges">
        <span class="tag tag-green">⚡ 飞猪实时检索</span>
        <span class="tag tag-blue">📍 本地口径与官方渠道</span>
        <span class="tag tag-purple">📷 目的地实拍</span>
      </div>
    </div>

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

    <!-- 目的地实拍图（对应 /services/city/photo；无图时自动不渲染） -->
    <div v-if="photo.url" class="dest-hero">
      <img :src="photo.url" :alt="photo.name || q.destination" loading="lazy" />
      <div class="dest-hero-cap"><span>📷</span>{{ photo.name || q.destination }} 实拍</div>
    </div>

    <!-- 火车窗口：走 /services/train，飞猪有实时班次/预订时覆盖展示 -->
    <Section v-if="train" title="🚄 火车票" :source="train?.source" :note="train?.note">
      <template #extra>
        <span v-if="train?.guide?.route" class="tag tag-blue">{{ train.guide.route }}</span>
      </template>
      <TicketList :tickets="train?.tickets || []" kind="train" @book="onBook" />
      <ChannelList v-if="train?.guide?.channels" :channels="train.guide.channels" />
    </Section>

    <!-- 机票窗口：走 /services/flight -->
    <Section v-if="flight" title="✈️ 机票" :source="flight?.source" :note="flight?.note">
      <TicketList :tickets="flight?.flights || flight?.tickets || []" kind="flight" @book="onBook" />
      <ChannelList v-if="flight?.guide?.channels" :channels="flight.guide.channels" />
    </Section>

    <!-- 酒店：住宿检索（/services/travel 内 hotels 模块） -->
    <Section v-if="travel" title="🏨 酒店" :source="travel.hotels?.source" :note="travel.hotels?.note">
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
            <a v-if="h.booking_url" class="btn btn-primary btn-sm" :href="h.booking_url" target="_blank" rel="noopener" @click="onBook('merchant')">预订</a>
          </div>
        </div>
      </div>
    </Section>

    <!-- 景点门票 -->
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
            <span v-if="a.address">📍 {{ a.address }}</span>
          </div>
          <a v-if="a.booking_url" class="btn btn-soft btn-sm m-book" :href="a.booking_url" target="_blank" rel="noopener" @click="onBook('attraction')">去购票 ↗</a>
        </div>
      </div>
    </Section>

    <!-- 商圈与美食：含飞猪实时酒店档（/services/merchant 返回的 hotels 字段） -->
    <Section v-if="mer" :title="merTitle" :source="mer?.source" :note="merNote">
      <div v-if="!(mer.merchants || []).length" class="empty"><p>暂无数据</p></div>
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

      <div v-if="(mer?.hotels || []).length" class="hfg">
        <div class="hfg-title">🏨 周边可订酒店（飞猪实时窗口）</div>
        <div class="mer-list">
          <div v-for="(hh, i) in mer.hotels" :key="'hotel' + i" class="card m-card">
            <div class="m-name">{{ hh.name }}</div>
            <div class="m-meta">
              <span class="tag tag-green">{{ hh.category || '酒店' }}</span>
              <span v-if="hh.score">⭐ {{ hh.score }}</span>
              <span v-if="hh.price_hint">💰 {{ hh.price_hint }}</span>
            </div>
            <div v-if="hh.position" class="m-addr">{{ hh.position }}</div>
            <a v-if="hh.booking_url" class="btn btn-soft btn-sm m-book" :href="hh.booking_url" target="_blank" rel="noopener" @click="onBook('merchant')">在线预订 ↗</a>
          </div>
        </div>
      </div>
    </Section>

    <!-- 夜间娱乐 -->
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

    <div v-if="!gotAny && !searching && searched" class="empty card"><div class="icon">🔍</div><p>没有查到服务数据，换个目的地试试</p></div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { svcApi } from '../../api'
import Section from './panels/SvcSection.vue'
import TicketList from './panels/TicketList.vue'
import ChannelList from './panels/ChannelList.vue'

const q = reactive({ destination: '北京市', origin: '上海', days: 3 })
const searching = ref(false)
const searched = ref(false)
// 与后端能力一一对应：train/flight 独立窗口 + travel(酒店) + attraction/merchant/entertainment 窗口
const train = ref(null)
const flight = ref(null)
const travel = ref(null)
const attr = ref(null)
const mer = ref(null)
const ent = ref(null)
const photo = ref({ url: '', name: '' })
const gotAny = computed(() => [train, flight, travel, attr, mer, ent].some((r) => r.value))

const merTitle = computed(() => (mer.value?.hotels?.length ? '🛍 商圈美食 · 周边住宿' : '🛍 商圈与美食'))
const merNote = computed(() => {
  const m = mer.value
  if (!m) return ''
  const hs = m.hotels || []
  return hs.length ? `${m.note || ''} 周边酒店为飞猪 AI 实时窗口，支持在线预订。` : (m.note || '')
})

async function searchAll() {
  searching.value = true
  try {
    const [tr, fl, tv, a, m, e] = await Promise.allSettled([
      svcApi.byKind('train', q.destination, q.origin),
      svcApi.byKind('flight', q.destination, q.origin),
      svcApi.travel(q.destination, q.origin, q.days),
      svcApi.byKind('attraction', q.destination, q.origin),
      svcApi.byKind('merchant', q.destination, q.origin),
      svcApi.byKind('entertainment', q.destination, q.origin),
    ])
    if (tr.status === 'fulfilled') train.value = tr.value
    if (fl.status === 'fulfilled') flight.value = fl.value
    if (tv.status === 'fulfilled') travel.value = tv.value
    if (a.status === 'fulfilled') attr.value = a.value
    if (m.status === 'fulfilled') mer.value = m.value
    if (e.status === 'fulfilled') ent.value = e.value
    searched.value = true
    // 目的地实拍图：后端 /services/city/photo（未配置 key / 无图时静默降级）
    try {
      const p = await svcApi.cityPhoto(q.destination)
      if (p && p.url) photo.value = p
    } catch { /* 图源失败不影响结果 */ }
  } finally { searching.value = false }
}

async function onBook(kind) {
  try { await svcApi.bookingClick(kind) } catch { /* 埋点失败不影响跳转 */ }
}
</script>

<style scoped>
.svc-page { padding-top: 32px; padding-bottom: 40px; }
.svc-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
.svc-badges { display: flex; gap: 8px; flex-wrap: wrap; }
.dest-hero { position: relative; margin: 22px 0 4px; border-radius: 16px; overflow: hidden; height: 176px; box-shadow: 0 12px 34px rgba(15,23,42,.14); }
.dest-hero img { width: 100%; height: 100%; object-fit: cover; display: block; }
.dest-hero-cap { position: absolute; left: 14px; bottom: 12px; display: flex; align-items: center; gap: 6px; color: #fff; font-size: 14px; font-weight: 800; text-shadow: 0 1px 6px rgba(0,0,0,.4); background: rgba(0,0,0,.28); padding: 4px 12px; border-radius: 999px; }
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
.m-book { margin-top: 10px; }
.hfg { margin-top: 22px; }
.hfg-title { font-size: 14.5px; font-weight: 800; color: var(--ink-900); margin-bottom: 12px; }
</style>
