# -*- coding: utf-8 -*-
"""trips.js 按账号分域迁移（跑完即删）"""
import io

p = 'stores/trips.js'
s = io.open(p, encoding='utf-8').read()

old = """// 行程书本地仓库：localStorage 持久化（trailmind.local_trips_v1，与旧版键名一致，存量可迁移）
// 数据来源：AI 规划结果沉淀 / 手动组装器保存；后端暂无 /api/trips，接入后仅需替换本文件实现。
import { reactive } from 'vue'

const STORAGE_KEY = 'trailmind.local_trips_v1'

function readAll() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    return Array.isArray(arr) ? arr.map(normalizeTrip).filter(Boolean) : []
  } catch {
    return []
  }
}

function writeAll(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch { /* 存储满 / 隐私模式：静默失败 */ }
}

const byUpdatedDesc = (a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || ''))

export const tripsStore = reactive({
  items: [],
  loaded: false,
  load() {
    if (this.loaded) return
    this.items = readAll().sort(byUpdatedDesc)
    this.loaded = true
  },"""

new = """// 行程书本地仓库：localStorage 持久化，按登录账号分域存储
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
  },"""

assert old in s, 'trips.js header not found'
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8').write(s)
print('trips store ok')
