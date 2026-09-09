// 本地行程书存储（单例 + 响应式 + 变更广播）
// ---------------------------------------------------------------------------
// 设计说明：
//  - 模块级单例：避免多个页面各自 new 一份、反复读盘导致状态分叉；
//  - 每次增删改都会写 localStorage，并向订阅者广播（供列表页 / 详情页联动刷新）；
//  - 导出响应式 tripList，组件可直接在模板里绑定，删除 / 保存后自动更新；
//  - 后端接入时只需把 readAll / writeAll 替换为 /api/trips CRUD，调用方 API 不变。
// ---------------------------------------------------------------------------
import { ref } from 'vue'

export const TRIP_STORE_KEY = 'trailmind.local_trips_v1'

function readAll() {
  try {
    const raw = localStorage.getItem(TRIP_STORE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function writeAll(list) {
  try {
    localStorage.setItem(TRIP_STORE_KEY, JSON.stringify(list))
  } catch {
    /* 存储满 / 隐私模式：静默失败 */
  }
}

// ---- 单例状态 -------------------------------------------------------------
const tripList = ref([])
let loaded = false
const listeners = new Set()

function byUpdatedDesc(a, b) {
  return String(b.updated_at || '').localeCompare(String(a.updated_at || ''))
}

function ensureLoaded() {
  if (!loaded) {
    tripList.value = readAll().sort(byUpdatedDesc)
    loaded = true
  }
}

function emitChange() {
  listeners.forEach(fn => {
    try { fn(tripList.value) } catch { /* 订阅者异常不影响主流程 */ }
  })
}

/** 以「排序后的新数组」落盘并广播：保持响应式引用的可替换语义 */
function commit(list) {
  tripList.value = list.sort(byUpdatedDesc)
  writeAll(list)
  emitChange()
}

// ---- 领域派生函数（供列表卡片 / 详情页 / 地图页共用）-----------------------
function pad2(n) { return String(n).padStart(2, '0') }
function fmtDate(d) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` }

/** 行程最后一天（start_date + days - 1），start_date 非法则返回 '' */
export function tripEndDate(t) {
  const s = t && t.start_date
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(String(s))) return ''
  const d = new Date(`${s}T00:00:00`)
  if (Number.isNaN(d.getTime())) return ''
  d.setDate(d.getDate() + Math.max(1, Number(t.days) || 1) - 1)
  return fmtDate(d)
}

/** 「2026-09-20 ~ 2026-09-21」区间文案；无 start_date 时返回 '' */
export function tripDateRange(t) {
  const s = t && t.start_date
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(String(s))) return ''
  const e = tripEndDate(t)
  return e && e !== String(s) ? `${s} ~ ${e}` : String(s)
}

/** 停留点总数（跨天累加） */
export function tripStopCount(t) {
  return (t && t.dayPlans || []).reduce((sum, d) => sum + (d.blocks || []).length, 0)
}

/** 预算拆解：base_total + delta（换品差价），返回 { total, base, delta } */
export function tripBudget(t) {
  const base = Number((t && t.base_total) || 0)
  const delta = Number((t && t.delta) || 0)
  return { total: base + delta, base, delta }
}

/** 预算文案：`¥6,880` 或带差价 `¥7,120（+¥240）`；无预算返回 '' */
export function tripBudgetText(t) {
  const { total, delta } = tripBudget(t)
  if (!total) return ''
  const t0 = `¥${total.toLocaleString()}`
  if (delta !== 0) {
    const sign = delta > 0 ? '+' : '-'
    return `${t0}（${sign}¥${Math.abs(delta).toLocaleString()}）`
  }
  return t0
}

// ---- 对外 API（向后兼容：list / get / save / remove 签名不变）-------------
export function useTripStore() {
  ensureLoaded()
  return {
    /** 全部行程（按 updated_at 倒序） */
    list() {
      ensureLoaded()
      return tripList.value
    },
    /** 单条行程，不存在返回 null */
    get(id) {
      ensureLoaded()
      return tripList.value.find(t => t.id === id) || null
    },
    /** 新增或整条覆盖保存；返回带 updated_at 的新对象 */
    save(trip) {
      ensureLoaded()
      const next = { ...trip, updated_at: new Date().toISOString() }
      const idx = tripList.value.findIndex(t => t.id === next.id)
      if (idx >= 0) tripList.value.splice(idx, 1, next)
      else tripList.value.push(next)
      commit(tripList.value.slice())
      return next
    },
    /** 软删 = 从库中移除（归档能力在接入后端后由 status 承担） */
    remove(id) {
      ensureLoaded()
      commit(tripList.value.filter(t => t.id !== id))
    },
    /** 订阅变更：fn 在每次增删改后收到最新数组；返回退订函数 */
    subscribe(fn) {
      listeners.add(fn)
      return () => listeners.delete(fn)
    },
  }
}

export { tripList }
