// Pinia 行程书仓库
// ---------------------------------------------------------------------------
// 职责：把 composables/tripStore.js 的 localStorage 持久层 + 响应式单例
// 包装为 Pinia store，组件里用 useTripsStore() 统一调用。
//
// 设计要点：
//  - **数据来源单点**：state.items 是唯一来源，列表 / 详情 / 地图 / 拼装器
//    都从这同一份内存态读，避免多页各自 load 产生分叉；
//  - **派生 getters 复用**：`byId / latest / totalStops` 等不重复计算；
//  - **API 兼容**：list/get/save/remove 签名与旧 composable 一致，
//    现有调用方零改动即可迁移；
//  - **后端零侵入**：未来把 load/save/remove 切到 /api/trips 时，
//    只需替换 actions 内部实现，组件层不动。
// ---------------------------------------------------------------------------
import { defineStore } from 'pinia'
import { tripDateRange, tripBudgetText, tripStopCount } from '../composables/tripStore'

const STORAGE_KEY = 'trailmind.local_trips_v1'

function readAll() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}
function writeAll(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    /* 存储满 / 隐私模式：静默失败 */
  }
}
function byUpdatedDesc(a, b) {
  return String(b.updated_at || '').localeCompare(String(a.updated_at || ''))
}

export const useTripsStore = defineStore('trips', {
  state: () => ({
    items: [],          // 当前内存态（与 localStorage 双向同步）
    loaded: false,      // 是否已从 localStorage 装载（避免反复读盘）
  }),
  getters: {
    /** 按 updated_at 倒序的列表 */
    list: (s) => (s.loaded ? s.items : s.items.slice().sort(byUpdatedDesc)),
    /** 通过 id 取单条（响应式：列表变更后取到的也是新引用） */
    byId: (s) => (id) => s.items.find(t => t.id === id) || null,
    /** 累计停留点数（列表卡 KPI） */
    totalStops: (s) => s.items.reduce((sum, t) => sum + tripStopCount(t), 0),
    /** 最近一次更新时间 */
    latest: (s) => s.items.slice().sort(byUpdatedDesc)[0] || null,
  },
  actions: {
    /** 首次读盘；后续调用为 no-op */
    load() {
      if (this.loaded) return
      this.items = readAll().sort(byUpdatedDesc)
      this.loaded = true
    },
    /** 强制从 localStorage 重新读盘（多标签页同步场景用） */
    reload() {
      this.items = readAll().sort(byUpdatedDesc)
      this.loaded = true
    },
    /** 整条覆盖保存；返回保存后的对象（带 updated_at） */
    save(trip) {
      this.load()
      const next = { ...trip, updated_at: new Date().toISOString() }
      const idx = this.items.findIndex(t => t.id === next.id)
      if (idx >= 0) this.items.splice(idx, 1, next)
      else this.items.push(next)
      this._commit()
      return next
    },
    /** 按 id 软删（归档能力在接入后端后由 status 字段承担） */
    remove(id) {
      this.load()
      this.items = this.items.filter(t => t.id !== id)
      this._commit()
    },
    /** 复制一份并另存为新 id（来自总览"再编一份"按钮等） */
    duplicate(id) {
      this.load()
      const t = this.items.find(x => x.id === id)
      if (!t) return null
      const copy = {
        ...JSON.parse(JSON.stringify(t)),
        id: 'lt_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        title: (t.title || '未命名行程') + ' · 副本',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      this.items.push(copy)
      this._commit()
      return copy
    },
    /** 内部：排序 + 落盘 + 触发订阅 */
    _commit() {
      this.items = this.items.slice().sort(byUpdatedDesc)
      writeAll(this.items)
    },
  },
})

// 兼容旧导入：仍允许 useTripStore() 调用（透明转发到 Pinia store）
import { useTripsStore as _useTrips } from '../stores/trips'
export function useTripStore() {
  const s = _useTrips()
  s.load()
  return {
    list: () => s.list,
    get: (id) => s.byId(id),
    save: (t) => s.save(t),
    remove: (id) => s.remove(id),
    subscribe: (fn) => s.$subscribe(() => fn(s.list)),
  }
}

// 重导出领域派生函数（旧 composable 已提供，保持 API 不变）
export { tripDateRange, tripBudgetText, tripStopCount }

// 兼容旧 reactive 单例的导入：提供一个 ref 视图，组件里仍可解构 .value
import { computed } from 'vue'
export const tripList = computed(() => _useTrips().list)
