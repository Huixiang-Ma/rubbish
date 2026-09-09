// 行程编排草稿状态机（W2：Planner 新建 与 TripBook 编辑 共用同一事实来源）
// ---------------------------------------------------------------------------
// 背景：旧 PlannerView 的 step2/3（draft + delta + 换品抽屉 + 保存装配）与
// 行程书“就地编辑”需要同一套 UI/逻辑，直接复制两遍必然漂移。本 composable
// 把 状态 + 领域操作 抽为单例可复用单元：
//   - openCreate(tpl, seed)   —— 从模板新建（预置种子商品）
//   - openEdit(trip)          —— 从已保存行程书恢复编辑
//   - 换品 / 加品 / 删品、时段倒挂保护、delta 差价、校验接入、saveTrip 装配
// 组件只负责渲染与事件；保存后产物直接写入 tripStore。
// ---------------------------------------------------------------------------
import { ref, reactive, computed } from 'vue'
import { productsApi } from '../api'
import { useTripStore } from './tripStore'
import { toast } from './toast'
import { buildDaysFromTemplate, snapshotProduct as snapshot, DEFAULT_START_DATE } from './tripFactory'
import { validateTripDraft, issueSummary } from './validators/trip'

export const CATS = [
  { name: '景点', emoji: '🏛', color: '#0EA5E9' },
  { name: '餐饮', emoji: '🍜', color: '#F59E0B' },
  { name: '住宿', emoji: '🏨', color: '#8B5CF6' },
  { name: '交通', emoji: '🚄', color: '#10B981' },
  { name: '购物', emoji: '🛍', color: '#EC4899' },
  { name: '文化', emoji: '📚', color: '#6366F1' },
]
export const PERIODS = {
  morning: { label: '上午', start: '08:30' },
  midday: { label: '午餐', start: '11:30' },
  afternoon: { label: '下午', start: '14:00' },
  evening: { label: '晚间', start: '17:30' },
  night: { label: '夜宿', start: '21:00' },
}
const DAY_SLOTS = ['morning', 'midday', 'afternoon', 'evening']

// 标品目录模块级缓存：一次会话内多次进出编辑器不必反复拉全量
let catalogCache = null
let catalogFetching = null
function fetchCatalog() {
  if (catalogCache) return Promise.resolve(catalogCache)
  if (catalogFetching) return catalogFetching
  catalogFetching = productsApi
    .list({ page_size: 200 })
    .then(r => {
      catalogCache = r.items || []
      return catalogCache
    })
    .catch(e => {
      catalogCache = []
      throw e
    })
    .finally(() => { catalogFetching = null })
  return catalogFetching
}

function cloneDays(days) {
  return JSON.parse(JSON.stringify(days || []))
}
function newBlockId() {
  return 'b_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 7)
}

let _draftSingleton = null

export function useTripDraft() {
  if (_draftSingleton) return _draftSingleton
  const store = useTripStore()

  // —— 状态 ——
  const stage = ref(1)          // 1 逐日编排 / 2 确认保存
  const ready = ref(false)      // 数据就绪（新建需先拉标品再排日）
  const dayIdx = ref(0)
  const editId = ref('')
  const seedProduct = ref(null)
  const prods = ref([])

  const draft = reactive({
    template: null,             // 模板元信息（新建=全量；编辑=从行程书还原的轻量对象）
    city: '',
    days: [],
    meta: { title: '', travelers: 2, budget: null, start_date: '', audience: '', note: '' },
  })
  const baseTotal = ref(0)      // 模板参考价
  const delta = ref(0)          // 换品/加删 差价
  const createdTs = ref('')     // 编辑时保留原 created_at

  const picker = reactive({ show: false, mode: 'swap', cat: '景点', cur: null })

  // —— 派生 ——
  const isEdit = computed(() => !!editId.value)
  const prodMap = computed(() => new Map(prods.value.map(p => [p.id, p])))
  const blockCount = computed(() => draft.days.reduce((s, d) => s + d.blocks.length, 0))
  const coveredCats = computed(() => {
    const set = new Set()
    for (const d of draft.days) for (const b of d.blocks) set.add(b.product.category)
    return set.size
  })
  const totalCost = computed(() => baseTotal.value + delta.value)
  const pickerOptions = computed(() => {
    const curId = picker.cur?.product?.id
    return prods.value
      .filter(p => p.category === picker.cat && p.city.includes(draft.city) && p.id !== curId)
      .slice(0, 30)
  })
  const issues = computed(() => validateTripDraft({ days: draft.days, meta: draft.meta }))
  const errCount = computed(() => issues.value.filter(i => i.level === 'error').length)
  const issueText = computed(() => issueSummary(issues.value))
  const curTemplate = computed(() => draft.template || {})
  const canSave = computed(() => !!String(draft.meta.title || '').trim() && errCount.value === 0)

  // —— 生命周期：新建 / 恢复 ——
  function reset() {
    editId.value = ''
    seedProduct.value = null
    dayIdx.value = 0
    stage.value = 1
    ready.value = false
    baseTotal.value = 0
    delta.value = 0
    createdTs.value = ''
    picker.show = false
    picker.cur = null
    draft.template = null
    draft.city = ''
    draft.days = []
    draft.meta = { title: '', travelers: 2, budget: null, start_date: '', audience: '', note: '' }
  }

  async function openCreate(tpl, seed) {
    reset()
    if (!tpl) return
    draft.template = tpl
    draft.city = tpl.city || ''
    baseTotal.value = tpl.price_total || 0
    draft.meta = {
      title: '',
      travelers: 2,
      budget: tpl.price_total || null,
      start_date: DEFAULT_START_DATE,
      audience: tpl.audience || '',
      note: '',
    }
    seedProduct.value = seed || null
    try {
      await ensureCatalog()
      draft.days = buildDaysFromTemplate(tpl, prodMap.value, seedProduct.value)
    } catch {
      toast('标品目录加载失败，编排可预览但无法换品', 'err')
      draft.days = buildDaysFromTemplate(tpl, prodMap.value, seedProduct.value)
    }
    ready.value = true
    dayIdx.value = 0
    stage.value = 1
  }

  /** 手动行程规划：把组装器（/api/composer/from-products）的排程结果装配为草稿 */
  async function applyComposerResult(composerTpl, composed) {
    reset()
    if (!composerTpl) return
    await ensureCatalog().catch(() => {})
    draft.template = composerTpl
    draft.city = composerTpl.city || ''
    baseTotal.value = Number(composed && composed.budget_estimate && composed.budget_estimate.tickets) || 0
    draft.meta = {
      title: '',
      travelers: 2,
      budget: (composed && composed.budget_estimate && composed.budget_estimate.total) || null,
      start_date: DEFAULT_START_DATE,
      audience: composerTpl.audience || '',
      note: '',
    }
    const byId = new Map()
    for (const p of prods.value) byId.set(p.id, p)
    const days = []
    for (const d of (composed && composed.itinerary) || []) {
      const blocks = []
      for (const b of (d.blocks || [])) {
        const p = byId.get(b.product_id) || {
          id: b.product_id, name: b.title, category: b.type, city: '',
          tags: [], price_min: 0, rating: 4.5, sales: 0,
        }
        const slot = b.slot || 'morning'
        blocks.push({ key: newBlockId(), period: slot, start: b.start || (PERIODS[slot] ? PERIODS[slot].start : '08:30'), tag: '', product: snapshot(p) })
      }
      days.push({ day: d.day, blocks })
    }
    draft.days = days
    ready.value = true
    dayIdx.value = 0
    stage.value = 1
  }

  function openEdit(trip) {
    reset()
    if (!trip) return
    editId.value = trip.id
    createdTs.value = trip.created_at || ''
    draft.template = {
      id: trip.template_id || '',
      title: trip.title,
      city: trip.city,
      days: trip.days,
      cover: trip.cover,
      pace: trip.pace || '',
      theme: trip.theme || '',
      season: trip.season || '',
      audience: trip.audience || '',
    }
    draft.city = trip.city || ''
    draft.days = cloneDays(trip.dayPlans || [])
    draft.meta = {
      title: trip.title || '',
      travelers: trip.travelers || 2,
      budget: trip.budget ?? null,
      start_date: trip.start_date || '',
      audience: trip.audience || '',
      note: trip.note || '',
    }
    baseTotal.value = trip.base_total || 0
    delta.value = trip.delta || 0
    ready.value = true
    dayIdx.value = 0
    stage.value = 1
    // 异步预取标品目录（换品抽屉用），失败不影响查看/保存
    ensureCatalog().catch(() => {})
  }

  async function ensureCatalog() {
    const list = await fetchCatalog()
    prods.value = list
    return list
  }

  // —— 编辑动作 ——
  function stopCountOf(d) { return d.blocks.length }

  function dayTitle(i) {
    const d = draft.days[i]
    if (!d) return ''
    const day = d.blocks.filter(b => b.period !== 'night')
    const names = day.slice(0, 2).map(b => b.product.name)
    return names.length ? names.join(' → ') + (day.length > 2 ? ' 等' : '') : '自由安排'
  }

  function openSwap(b) {
    picker.mode = 'swap'
    picker.cat = (b.product && b.product.category) || '景点'
    picker.cur = b
    picker.show = true
  }

  function openAdd() {
    picker.mode = 'add'
    picker.cat = '景点'
    picker.cur = null
    picker.show = true
  }

  /** 换品/加品时按新品类推导合理时段（防 夜宿/交通/白天 倒挂） */
  function periodFor(newCat, cur) {
    if (newCat === '住宿') return 'night'
    if (newCat === '交通') return 'morning'
    // 白天标品：
    if (cur && cur.period === 'night') return 'evening'   // 住宿位被白天品替换 → 挪到晚间
    if (cur && DAY_SLOTS.includes(cur.period)) return cur.period
    return nextFreePeriod()
  }

  function nextFreePeriod() {
    const day = draft.days[dayIdx.value]
    const used = new Set((day ? day.blocks : []).filter(b => b.period !== 'night').map(b => b.period))
    return DAY_SLOTS.find(s => !used.has(s)) || 'evening'
  }

  function mkBlock(p, period, start, tag) {
    return { key: newBlockId(), period, start, tag, product: snapshot(p) }
  }

  function pick(p) {
    const day = draft.days[dayIdx.value]
    if (!day || !p) return
    if (picker.mode === 'swap' && picker.cur) {
      const old = picker.cur
      const newCat = p.category
      const oldPrice = old.product.price_min || 0
      const period = periodFor(newCat, old)
      const isTraffic = newCat === '交通'
      const isHotel = newCat === '住宿'
      old.product = snapshot(p)
      old.period = period
      old.start = PERIODS[period] ? PERIODS[period].start : (isTraffic ? '08:00' : '14:00')
      old.tag = isHotel ? old.tag : isTraffic ? (old.tag || '去程') : ''
      delta.value += (p.price_min || 0) - oldPrice
    } else {
      const cut = day.blocks.findIndex(b => b.period === 'night')
      const at = cut >= 0 ? cut : day.blocks.length
      const period = periodFor(p.category, null)
      const start = p.category === '交通' ? '08:00' : PERIODS[period] ? PERIODS[period].start : '14:00'
      const block = mkBlock(p, period, start, p.category === '交通' ? '去程' : '')
      day.blocks.splice(at, 0, block)
      delta.value += p.price_min || 0
    }
    picker.show = false
  }

  function removeBlock(bi) {
    const day = draft.days[dayIdx.value]
    const b = day && day.blocks[bi]
    if (!b) return
    delta.value -= b.product.price_min || 0
    day.blocks.splice(bi, 1)
  }

  function goStage(n) {
    stage.value = n
    if (n === 1 && draft.days.length && dayIdx.value >= draft.days.length) dayIdx.value = 0
  }

  // —— 保存装配 ——
  function saveTrip() {
    const tpl = curTemplate.value
    const id = editId.value || 'lt_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
    const trip = {
      id,
      template_id: tpl.id || draft.template?.id || '',
      source: 'planner',
      title: String(draft.meta.title || '').trim(),
      city: draft.city,
      days: draft.days.length,
      pace: tpl.pace || '',
      theme: tpl.theme || '',
      audience: draft.meta.audience || tpl.audience || '',
      season: tpl.season || '',
      cover: tpl.cover || { emoji: '🧩', gradient: 'linear-gradient(135deg,#60A5FA,#8B5CF6)' },
      travelers: draft.meta.travelers,
      budget: draft.meta.budget ?? null,
      start_date: draft.meta.start_date || '',
      note: draft.meta.note || '',
      base_total: baseTotal.value,
      delta: delta.value,
      dayPlans: cloneDays(draft.days),
      created_at: createdTs.value || new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    store.save(trip)
    return trip
  }

  // —— 展示工具 ——
  function fmt(n) { return Number(n || 0).toLocaleString('zh-CN') }
  function fmtSales(n) { return n >= 10000 ? (n / 10000).toFixed(1) + 'w' : String(n) }
  function paceLabel(p) { return ({ relaxed: '🛋 悠闲', standard: '⚖ 标准', tight: '⚡ 紧凑' })[p] || p }
  function periodLabel(k) { return (PERIODS[k] || {}).label || k }
  function catColor(c) { return (CATS.find(x => x.name === c) || {}).color || '#64748B' }
  function priceText(p) {
    if (!p || p.price_min == null) return '—'
    if (p.price_min === 0) return '免费'
    const max = p.price_max && p.price_max > p.price_min ? '~' + p.price_max : ''
    return '¥' + p.price_min + max
  }
  function diffText(n, o) {
    const diff = (n.price_min || 0) - (o.price_min || 0)
    if (!diff) return '同价'
    return (diff > 0 ? '+' : '−') + '¥' + fmt(Math.abs(diff))
  }

  _draftSingleton = {
    store,
    // state
    stage, ready, dayIdx, editId, seedProduct, prods, draft,
    baseTotal, delta, picker, createdTs,
    // derived
    isEdit, prodMap, blockCount, coveredCats, totalCost, pickerOptions,
    issues, errCount, issueText, curTemplate, canSave,
    // actions
    reset, openCreate, openEdit, applyComposerResult, ensureCatalog,
    openSwap, openAdd, pick, removeBlock, goStage,
    stopCountOf, dayTitle, saveTrip,
    // tools
    fmt, fmtSales, paceLabel, periodLabel, catColor, priceText, diffText,
    CATS, PERIODS, DAY_SLOTS,
  }
  return _draftSingleton
}
