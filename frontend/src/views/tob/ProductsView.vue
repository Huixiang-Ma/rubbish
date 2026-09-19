<script setup>
import { ref, computed, onMounted } from 'vue'
import TobIcon from '../../components/TobIcon.vue'
import ProductFormDrawer from './ProductFormDrawer.vue'
import { productsApi, planShopApi, govApi } from '../../api/index.js'

const f = ref({ keyword: '', category: '', city: '', status: 'all' })

const drawerOpen = ref(false)
const editTarget = ref(null)
function openCreate() { editTarget.value = null; drawerOpen.value = true }
function openEdit(p) { editTarget.value = p; drawerOpen.value = true }

/* —— 标品素材库：GET /api/products/manage + create/update/status/delete（回退演示数据） —— */
const FALLBACK = [
  { id: 'SKU-0001', name: '拙政园', category: '景点', city: '苏州', price: 78, priceMax: 96, stock: 420, zero: false, sales: 1286, listed: true, manual: false },
  { id: 'SKU-0002', name: '平江路摇橹船', category: '体验', city: '苏州', price: 120, priceMax: 150, stock: 86, zero: false, sales: 742, listed: true, manual: false },
  { id: 'SKU-0003', name: '苏帮菜 · 松鹤楼', category: '餐饮', city: '苏州', price: 158, priceMax: 268, stock: 240, zero: false, sales: 508, listed: true, manual: false },
]
const products = ref(FALLBACK)
const loading = ref(false)
const toastMsg = ref('')

function toRow(raw = {}) {
  const stock = Number(raw.stock ?? (raw.skus || []).reduce((n, s) => n + Number(s.stock || 0), 0)) || 0
  return {
    id: raw.id, name: raw.name, category: raw.category || '景点', city: raw.city || '',
    price: Number(raw.price_min ?? raw.price) || 0,
    priceMax: Number(raw.price_max ?? raw.priceMax) || Number(raw.price_min ?? raw.price) || 0,
    stock, zero: stock <= 0,
    sales: Number(raw.sales) || 0,
    listed: raw.listed !== false,
    manual: !raw._seed,
    tags: raw.tags || [],
    dwell: raw.typical_dwell || '',
    slot: raw.best_slot || 'morning',
    rating: raw.rating || 4.5,
    note: raw.description || '',
  }
}

async function load() {
  loading.value = true
  try {
    const res = await productsApi.manageList({ keyword: f.value.keyword, category: f.value.category, page: 1, page_size: 300 })
    const rows = (res && res.items) || []
    if (rows.length) products.value = rows.map(toRow)
  } catch { /* 未登录/网络异常：保留演示数据 */ }
  loading.value = false
}

/* 环5 价格时效：最近完成任务实采票价 vs 素材标准价 → 漂移告警 */
const drift = ref(null)
async function loadDrift() {
  try { drift.value = await govApi.priceDrift() } catch { /* staff 才可读 */ }
}

/* 素材贡献：在售方案销量按 product_ids 聚合 */
const contribMap = ref({})
async function loadContrib() {
  try {
    const pl = await planShopApi.manageList({ page: 1, page_size: 100 })
    const contrib = {}
    for (const p of (pl && pl.items) || []) {
      for (const pid of (p.product_ids || [])) {
        contrib[pid] = (contrib[pid] || 0) + (p.sales || 0)
      }
    }
    contribMap.value = contrib
  } catch { /* ignore */ }
}

/* 素材自动化：POI 批量拉取 → 勾选入库（自动挂语料） */
const poiCity = ref('')
const poiLoading = ref(false)
const poiItems = ref([])
const poiPicked = ref({})
async function pullPoi() {
  if (!poiCity.value.trim() || poiLoading.value) return
  poiLoading.value = true
  try {
    const res = await productsApi.poiCandidates(poiCity.value.trim())
    poiItems.value = (res.items || []).filter(x => !x.duplicate)
    poiPicked.value = {}
  } catch { poiItems.value = [] }
  poiLoading.value = false
}
function togglePoi(name) { poiPicked.value[name] = !poiPicked.value[name] }
const poiPickedCount = () => Object.values(poiPicked.value).filter(Boolean).length
async function importPoi() {
  const picks = poiItems.value.filter(x => poiPicked.value[x.name])
  if (!picks.length) return
  let ok = 0
  for (const x of picks) {
    try {
      await productsApi.create({
        name: x.name, category: '景点', city: x.city,
        price_min: x.price || 0, price_max: x.price || 0, stock: 20,
        typical_dwell: `${Math.round((x.visit_minutes || 120) / 30) / 2}h`,
        rating: Number(x.rating) || 4.5,
        description: x.description, tags: (x.tags || []).slice(0, 3), listed: true,
      })
      ok++
    } catch { /* 单条失败跳过 */ }
  }
  window.alert(`已入库 ${ok} 条素材（自动挂载语料）`)
  poiItems.value = []
  poiPicked.value = {}
  load()
}
onMounted(() => { load(); loadDrift(); loadContrib() })

async function onSaved(data) {
  const payload = {
    name: data.name, category: data.category, city: data.city,
    price_min: Number(data.price) || 0, price_max: Number(data.priceMax) || Number(data.price) || 0,
    stock: Number(data.stock) || 0, typical_dwell: data.dwell || '2h', best_slot: data.slot || 'morning',
    rating: data.rating || 4.5, description: data.note || data.name, tags: data.tags || [],
  }
  try {
    if (data.id && products.value.some(p => p.id === data.id)) {
      await productsApi.update(data.id, payload)
    } else {
      const res = await productsApi.create(payload)
      const row = toRow(res.product || {})
      products.value.unshift(row)
      toastMsg.value = '素材已创建'
      setTimeout(() => toastMsg.value = '', 2400)
      return
    }
    await load()
    toastMsg.value = '素材已保存'
    setTimeout(() => toastMsg.value = '', 2400)
  } catch (e) {
    // 后端不可用/未登录：本地列表兜底更新，保持可演示
    const i = products.value.findIndex(p => p.id === data.id)
    const row = { ...data, priceMax: data.priceMax || data.price, zero: (data.stock || 0) <= 0 }
    if (i >= 0) products.value[i] = { ...products.value[i], ...row }
    else products.value.unshift({ ...row, id: data.id || `SKU-${String(Date.now()).slice(-4)}`, sales: 0, listed: data.listed !== false })
    toastMsg.value = `已本地保存（后端：${e.message || '不可用'}）`
    setTimeout(() => toastMsg.value = '', 3000)
  }
}

async function toggleListed(p) {
  try {
    await productsApi.setStatus(p.id, !p.listed)
    p.listed = !p.listed
  } catch { p.listed = !p.listed }
}
async function removeProduct(p) {
  if (!window.confirm(`确认删除素材「${p.name}」?`)) return
  try { await productsApi.remove(p.id) } catch { /* 本地仍移除 */ }
  products.value = products.value.filter(x => x.id !== p.id)
}

const CATS = ['景点', '餐饮', '住宿', '交通', '体验', '购物']
const CITIES = ['苏州', '杭州', '大理', '成都', '厦门', '西安']

const selected = ref([])
const allChecked = computed(() => rows.value.length > 0 && selected.value.length === rows.value.length)

const stats = computed(() => ({
  online: products.value.filter(p => p.listed).length,
  offline: products.value.filter(p => !p.listed).length,
  skus: products.value.length * 2,
  stock: products.value.reduce((s, p) => s + p.stock, 0),
  low: products.value.filter(p => p.zero).length,
  sales: products.value.reduce((s, p) => s + p.sales, 0),
}))

const rows = computed(() => products.value.filter(p =>
  (f.value.status === 'all' || (f.value.status === 'listed' ? p.listed : !p.listed)) &&
  (!f.value.keyword || (p.name + p.id).toLowerCase().includes(f.value.keyword.toLowerCase())) &&
  (!f.value.category || p.category === f.value.category) &&
  (!f.value.city || p.city === f.value.city)
))

function toggleAll() { selected.value = allChecked.value ? [] : rows.value.map(p => p.id) }
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">素材管理</div>
        <h1 class="page-title">标品素材库</h1>
        <p class="page-desc">
          标品 = 行程规划的<b>内容素材</b>(景点 / 餐饮 / 住宿…),只被「方案」引用,不直接对游客零售。
          维护营业信息、参考票价、建议时段与<b>素材启停用</b>;下架 = 新方案不再引用该素材。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="load"><TobIcon name="refresh" :size="14" />刷新</button>
        <button class="btn btn-primary btn-sm" @click="openCreate"><TobIcon name="plus" :size="14" />新建素材</button>
      </div>
    </div>

    <!-- 统计条 -->
    <div class="stat-grid cols-6">
      <div class="stat-card"><div class="k">启用素材</div><div class="v">{{ stats.online }}</div><div class="sub">可被方案引用</div></div>
      <div class="stat-card"><div class="k">停用</div><div class="v">{{ stats.offline }}</div><div class="sub">新方案不引用</div></div>
      <div class="stat-card"><div class="k">规格</div><div class="v">{{ stats.skus }}</div><div class="sub">参考价位明细</div></div>
      <div class="stat-card"><div class="k">参考余量</div><div class="v">{{ stats.stock.toLocaleString() }}</div><div class="sub">随订单扣减(演示)</div></div>
      <div class="stat-card"><div class="k" style="color:var(--warn)">需维护</div><div class="v" style="color:var(--warn)">{{ stats.low }}</div><div class="sub">存在 0 余量规格</div></div>
      <div class="stat-card"><div class="k">累计进入方案</div><div class="v">{{ stats.sales.toLocaleString() }}</div><div class="sub">次</div></div>
    </div>

    <!-- 筛选条 -->
    <div class="card toolbar">
      <div class="search-box">
        <span class="s-ico"><TobIcon name="search" :size="15" /></span>
        <input v-model.trim="f.keyword" placeholder="搜名称 / 标签 / ID…" />
      </div>
      <select v-model="f.category" class="select-slim">
        <option value="">全部分类</option>
        <option v-for="c in CATS" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="f.city" class="select-slim">
        <option value="">全部城市</option>
        <option v-for="c in CITIES" :key="c" :value="c">{{ c }}</option>
      </select>
      <div class="status-tabs" style="margin-left:auto">
        <button :class="{ on: f.status === 'all' }" @click="f.status = 'all'">全部 <i>{{ rows.length }}</i></button>
        <button :class="{ on: f.status === 'listed' }" @click="f.status = 'listed'">启用 <i>{{ stats.online }}</i></button>
        <button :class="{ on: f.status === 'off' }" @click="f.status = 'off'">停用 <i>{{ stats.offline }}</i></button>
      </div>
    </div>

    <!-- 批量操作 -->
    <div v-if="selected.length" class="batch-bar">
      已选 <b>{{ selected.length }}</b> 个标品
      <button class="btn btn-primary-soft btn-sm">批量上架</button>
      <button class="btn btn-ghost btn-sm">批量下架</button>
      <button class="batch-clear" @click="selected = []">取消选择</button>
    </div>

    <!-- 表格 -->
    <div class="card table-card">
      <!-- 环5 价格漂移告警 -->
      <div v-if="drift && drift.total" class="card drift-banner">
        ⚠ 价格漂移 {{ drift.total }} 处（任务 {{ drift.job_id }} 实采 vs 素材库标准价）：
        <span v-for="(d, i) in drift.items.slice(0, 3)" :key="i" class="tag tag-warn" style="margin:0 4px">
          {{ d.spot }} 票面 {{ d.used_price }} / 素材 {{ d.catalog_price ?? '未覆盖' }}
        </span>
        <button class="btn btn-ghost btn-sm" @click="drift = null">知道了</button>
      </div>

      <!-- 素材自动化：POI 批量拉取 -->
      <div class="card poi-panel">
        <div class="poi-head">
          <b>📥 按城市批量拉取素材候选</b>
          <div class="row gap-2">
            <input v-model.trim="poiCity" class="input" style="width:160px;height:34px" placeholder="如：杭州" @keyup.enter="pullPoi" />
            <button class="btn btn-primary btn-sm" :disabled="poiLoading" @click="pullPoi">{{ poiLoading ? '拉取中…' : '拉取候选' }}</button>
          </div>
        </div>
        <div v-if="poiItems.length" class="poi-list">
          <label v-for="x in poiItems" :key="x.name" class="poi-row" :class="{ picked: poiPicked[x.name] }">
            <input type="checkbox" :checked="poiPicked[x.name]" @change="togglePoi(x.name)" />
            <b>{{ x.name }}</b>
            <span class="mono-xs">{{ x.price ? '¥' + x.price : '免费' }} · {{ x.visit_minutes }} 分钟 · {{ (x.tags || []).join('/') }}</span>
          </label>
          <button class="btn btn-primary btn-sm" style="margin-top:var(--s-3)" :disabled="!poiPickedCount()" @click="importPoi">
            入库选中 {{ poiPickedCount() }} 条（自动挂语料）
          </button>
        </div>
        <p v-else-if="poiCity" class="mono-xs" style="color:var(--text-faint);margin:var(--s-2) 0 0">该城市暂无候选（或已全部入库）</p>
      </div>

      <table class="table">
        <thead>
          <tr>
            <th style="width:36px"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
            <th>标品</th>
            <th>分类 / 城市</th>
            <th>价格(起)</th>
            <th>库存</th>
            <th>销量</th>
            <th>方案贡献</th>
            <th>状态</th>
            <th style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in rows" :key="p.id">
            <td><input type="checkbox" v-model="selected" :value="p.id" /></td>
            <td>
              <div class="prod-cell">
                <span class="prod-cover" :class="p.category">{{ p.name.slice(0, 1) }}</span>
                <div>
                  <div class="cell-main">{{ p.name }}</div>
                  <div class="mono-xs">{{ p.id }} <em v-if="p.manual" class="manual-tag">自建</em></div>
                </div>
              </div>
            </td>
            <td>
              <div class="cell-main" style="font-weight:var(--fw-regular)">{{ p.category }}</div>
              <div class="cell-sub">{{ p.city }}</div>
            </td>
            <td>
              <span class="num">¥{{ p.price }}</span>
              <span v-if="p.priceMax > p.price" class="cell-sub">~ ¥{{ p.priceMax }}</span>
            </td>
            <td>
              <span :class="{ 'num-low': p.zero }">{{ p.stock }}</span>
              <span v-if="p.zero" class="warn-dot" title="存在 0 库存规格">●</span>
            </td>
            <td class="num">{{ p.sales.toLocaleString() }}</td>
            <td class="num" style="color:var(--text-3)">{{ contribMap[p.id] ? '¥' + contribMap[p.id].toLocaleString() : '—' }}</td>
            <td><span class="pill" :class="p.listed ? 'pill-on pill-dot' : 'pill-off pill-dot'">{{ p.listed ? '在架' : '下架' }}</span></td>
            <td>
              <div class="ops">
                <button class="op" @click="openEdit(p)">编辑</button>
                <button class="op" @click="toggleListed(p)">{{ p.listed ? '停用' : '启用' }}</button>
                <button class="op" @click="removeProduct(p)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 标品新建/编辑抽屉 -->
    <ProductFormDrawer :open="drawerOpen" :product="editTarget" @close="drawerOpen = false" @save="onSaved" />
  </div>
</template>

<style scoped>
.batch-bar {
  display: flex; align-items: center; gap: var(--s-3);
  font-size: var(--fs-sm); color: var(--text-2);
  padding: var(--s-3) var(--s-5);
  background: var(--accent-3-soft);
  border: 1px solid transparent;
  border-radius: var(--r-md);
}
.batch-clear {
  margin-left: auto; border: none; background: none;
  font-size: var(--fs-xs); color: var(--text-3);
}
.batch-clear:hover { color: var(--text); }

.drift-banner { display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; padding: var(--s-3) var(--s-4); margin-bottom: var(--s-4); border: 1px solid #EBD2CC; background: #F6EBE9; border-radius: var(--r); font-size: var(--fs-sm); color: #A8665C; }
.poi-panel { margin-bottom: var(--s-4); padding: var(--s-4) var(--s-5); }
.poi-head { display: flex; justify-content: space-between; align-items: center; gap: var(--s-3); margin-bottom: var(--s-2); }
.poi-list { display: flex; flex-direction: column; gap: 4px; margin-top: var(--s-2); }
.poi-row { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) var(--s-3); border: 1px solid var(--border-soft); border-radius: var(--r-sm); cursor: pointer; font-size: var(--fs-sm); }
.poi-row.picked { border-color: var(--accent); background: var(--accent-soft); }
.prod-cell { display: flex; align-items: center; gap: var(--s-3); }
.prod-cover {
  width: 36px; height: 36px; border-radius: var(--r);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--fs-sm); font-weight: var(--fw-semi); flex: none;
}
.prod-cover.景点 { background: var(--accent-soft); color: var(--accent); }
.prod-cover.餐饮 { background: var(--accent-2-soft); color: var(--accent-2); }
.prod-cover.住宿 { background: var(--accent-3-soft); color: var(--accent-3); }
.prod-cover.交通 { background: var(--bg-soft); color: var(--text-2); }
.prod-cover.体验 { background: var(--warn-soft); color: var(--warn); }
.prod-cover.购物 { background: var(--danger-soft); color: var(--danger); }

.manual-tag {
  font-style: normal; margin-left: 4px;
  font-size: 11px; color: var(--accent-2);
  background: var(--accent-2-soft);
  padding: 0 4px; border-radius: 4px;
}
.num { font-variant-numeric: tabular-nums; font-weight: var(--fw-medium); }
.num-low { color: var(--warn); font-weight: var(--fw-medium); }
.warn-dot { color: var(--warn); margin-left: 4px; font-size: 9px; }
</style>
