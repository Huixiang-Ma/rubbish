// 行程书本地仓库：localStorage 持久化，按登录账号分域存储
//   键：trailmind.local_trips_v1__<用户名|guest> —— 不同账号登录各看各的行程书，互不可见
// 数据来源：AI 规划结果沉淀 / 手动组装器保存；后端暂无 /api/trips，接入后仅需替换本文件实现。
import { reactive } from 'vue'
import { auth } from './auth.js'

const STORAGE_BASE = 'trailmind.local_trips_v1'

function storageKey() {
  const u = (auth.traveler && auth.traveler.username) || 'guest'
  return STORAGE_BASE + '__' + u
}

function readAll() {
  try {
    const raw = localStorage.getItem(storageKey())
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr.map(normalizeTrip).filter(Boolean) : []
  } catch {
    return []
  }
}

// 形状规范化：localStorage 可能存有旧版前端遗留数据（字段缺失/结构不同），
// 不清洗会让列表/详情/地图页在渲染时抛 TypeError 白屏；不合规条目直接丢弃。
function normalizeTrip(t) {
  if (!t || typeof t !== 'object' || !t.id) return null
  const dayPlans = Array.isArray(t.dayPlans)
    ? t.dayPlans.map((d, di) => ({
        day: Number(d && d.day) || di + 1,
        title: String((d && d.title) || `第 ${di + 1} 天`),
        summary: String((d && d.summary) || ''),
        items: (Array.isArray(d && d.items) ? d.items : [])
          .filter(it => it && it.stop && it.stop.name)
          .map(it => ({ time: String(it.time || '弹性安排'), stop: it.stop })),
      }))
    : []
  if (!dayPlans.length) return null
  return {
    ...t,
    title: String(t.title || '未命名行程'),
    city: String(t.city || ''),
    days: Number(t.days) || dayPlans.length,
    theme: String(t.theme || ''),
    pace: String(t.pace || ''),
    people: Number(t.people ?? t.travelers) || 1,
    date: String(t.date || ''),
    budget: Number(t.budget) || 0,
    stops: Number(t.stops) || dayPlans.reduce((n, d) => n + d.items.length, 0),
    cats: Number(t.cats) || new Set(dayPlans.flatMap(d => d.items.map(i => i.stop.cat))).size || 1,
    dayPlans,
  }
}

function writeAll(list) {
  try {
    localStorage.setItem(storageKey(), JSON.stringify(list))
  } catch { /* 存储满 / 隐私模式：静默失败 */ }
}

const byUpdatedDesc = (a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || ''))

export const tripsStore = reactive({
  items: [],
  loadedFor: null,
  load() {
    const u = (auth.traveler && auth.traveler.username) || 'guest'
    if (this.loadedFor === u) return
    this.loadedFor = u
    this.items = readAll().sort(byUpdatedDesc)
  },
  byId(id) {
    this.load()
    return this.items.find(t => t.id === id) || null
  },
  save(trip) {
    this.load()
    const next = { ...trip, updated_at: new Date().toISOString() }
    const idx = this.items.findIndex(t => t.id === next.id)
    if (idx >= 0) this.items.splice(idx, 1, next)
    else this.items.unshift(next)
    writeAll(this.items)
    return next
  },
  remove(id) {
    this.load()
    this.items = this.items.filter(t => t.id !== id)
    writeAll(this.items)
  },
})

/* —— 后端行程结构 → 本地行程书（trip={id,title,city,days,people,date,budget,dayPlans:[{day,title,summary,items:[{stop,time}]}]}） —— */
// 后端 itinerary 每天形如 {day, theme, items:[{time, title, spot:{name,tags,lat,lng,ticket_price,visit_minutes,rating,main_pic,knowledge}}]}
const CAT_KEYS = ['景点', '餐饮', '住宿', '交通', '购物', '文化', '体验']
function guessCat(spot) {
  const tags = Array.isArray(spot && spot.tags) ? spot.tags.join(',') : ''
  if (/酒店|民宿|宾馆|客栈|公寓/.test(spot && spot.name || '') || /住宿|酒店/.test(tags)) return '住宿'
  if (/餐厅|美食|菜|小吃|茶|咖啡|面|火锅|烧烤/.test(spot && spot.name || '') || /餐饮|美食/.test(tags)) return '餐饮'
  if (/博物馆|馆|寺|园|故居|遗址|教堂/.test(spot && spot.name || '')) return '文化'
  if (/机场|车站|码头|索道|轮渡|地铁/.test(spot && spot.name || '') || /交通/.test(tags)) return '交通'
  return '景点'
}

export function itineraryToTrip(result, jobId = '') {
  const itin = result && result.itinerary
  if (!Array.isArray(itin) || !itin.length) return null
  const input = result.user_input || {}
  const tripId = `t_${jobId || Date.now().toString(36)}`
  const dayPlans = itin.map((d, di) => ({
    day: d.day || di + 1,
    title: d.theme || `第 ${d.day || di + 1} 天`,
    summary: d.summary || (Array.isArray(d.fun_tip) && d.fun_tip[0]) || '',
    items: (d.items || []).map(it => ({
      time: it.time || '弹性安排',
      title: it.title,
      transport: it.transport,
      reason: it.reason,
      stop: {
        id: `SPOT-${di}-${(it.spot && it.spot.name) || (it.title || '')}`,
        name: (it.spot && it.spot.name) || it.title || '未命名停留点',
        cat: guessCat(it.spot),
        city: input.destination || '',
        price: Number((it.spot && it.spot.ticket_price) || 0),
        dwell: (it.spot && it.spot.visit_minutes) ? `${Math.round(it.spot.visit_minutes / 30) / 2}h` : '',
        rating: Number((it.spot && it.spot.rating) || 0) || undefined,
        x: it.spot && it.spot.lng != null ? it.spot.lng : null,
        y: it.spot && it.spot.lat != null ? it.spot.lat : null,
        note: (it.spot && (it.spot.knowledge || it.reason)) || it.transport || '',
        pic: it.spot && it.spot.main_pic,
        catKey: CAT_KEYS[0],
      },
    })),
  }))
  const stops = dayPlans.flatMap(d => d.items.map(i => i.stop))
  return {
    id: tripId,
    jobId,
    title: `${input.destination || '我的'}${input.days || dayPlans.length}日行程`,
    city: input.destination || '',
    days: dayPlans.length,
    theme: '',
    pace: '',
    people: Number(input.travelers) || 2,
    date: input.departure_date || '',
    budget: Number(input.budget) || 0,
    stops: stops.length,
    cats: new Set(stops.map(s => s.cat)).size,
    template: '',
    delta: '',
    dayPlans,
  }
}

/* —— 组装器结果（composer compose）→ 本地行程书 ——
 * 后端返回：{job_id, days:数字, itinerary:[{day, blocks:[{slot,slot_zh,start,duration,
 *   product_id,title,type,note,knowledge{content,source}}]}], budget_estimate, coverage_score, warnings, city}
 */
export function composeToTrip(composed, meta = {}) {
  const days = (composed && Array.isArray(composed.itinerary)) ? composed.itinerary
    : (composed && Array.isArray(composed.days)) ? composed.days : []
  const tripId = `t_manual_${Date.now().toString(36)}`
  const dayPlans = days.map((d, di) => ({
    day: d.day || di + 1,
    title: d.title || d.theme || `第 ${di + 1} 天`,
    summary: d.summary || '',
    items: (d.blocks || d.items || []).map(b => {
      const p = b.product || {}
      return {
        time: b.time || (b.start ? `${b.start} · ${b.slot_zh || ''}`.trim() : '弹性安排'),
        stop: {
          id: b.product_id || p.id || `SKU-${Math.random().toString(36).slice(2, 8)}`,
          name: b.title || p.name || '',
          cat: b.type || p.category || '景点',
          city: meta.city || '',
          price: Number(p.price_min ?? p.price ?? 0),
          dwell: b.duration || p.typical_dwell || '',
          x: (Array.isArray(p.coords) ? p.coords[0] : (p.coords && p.coords.lng)) ?? null,
          y: (Array.isArray(p.coords) ? p.coords[1] : (p.coords && p.coords.lat)) ?? null,
          note: (b.knowledge && b.knowledge.content) || p.description || b.note || '',
        },
      }
    }),
  }))
  if (!dayPlans.length) return null
  const stops = dayPlans.flatMap(d => d.items.map(i => i.stop))
  const budgetRaw = composed && composed.budget_estimate
  return {
    id: tripId,
    title: meta.name || '我的手动行程',
    city: meta.city || '',
    days: dayPlans.length,
    theme: '',
    pace: meta.pace || '',
    people: meta.people || 2,
    date: meta.date || '',
    budget: Number(typeof budgetRaw === 'object' && budgetRaw ? (budgetRaw.total ?? budgetRaw.grand_total) : budgetRaw) || stops.reduce((n, s) => n + (s.price || 0), 0),
    stops: stops.length,
    cats: new Set(stops.map(s => s.cat)).size,
    template: '手动组装',
    delta: '',
    dayPlans,
  }
}
