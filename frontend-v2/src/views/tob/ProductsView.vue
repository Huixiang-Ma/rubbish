<template>
  <div>
    <div class="page-head">
      <div>
        <h1>标品素材库</h1>
        <div class="desc" style="color:var(--text-faint)">
          标品 = 行程规划的<b style="color:var(--text-dim)">内容素材</b>（景点 / 餐饮 / 住宿…），只被「方案」引用，
          不直接对游客零售。维护营业信息、参考票价、建议时段与<b style="color:var(--text-dim)">素材启停用</b>；
          下架 = 新方案不再引用该素材。
        </div>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="load">↻ 刷新</button>
        <button class="btn btn-primary btn-sm" @click="openNew">＋ 新建素材</button>
      </div>
    </div>

    <!-- 统计条 -->
    <div class="pm-stats">
      <div class="pm-stat"><span>启用素材</span><b>{{ stats.online }}</b><i>可被方案引用</i></div>
      <div class="pm-stat"><span>停用</span><b>{{ stats.offline }}</b><i>新方案不引用</i></div>
      <div class="pm-stat"><span>规格</span><b>{{ stats.skus }}</b><i>参考价位明细</i></div>
      <div class="pm-stat"><span>参考余量</span><b>{{ stats.stock }}</b><i>随订单扣减（演示）</i></div>
      <div class="pm-stat warn"><span>需维护</span><b>{{ stats.low }}</b><i>存在 0 余量规格</i></div>
      <div class="pm-stat"><span>累计进入方案</span><b>{{ stats.sales }}</b><i>次</i></div>
    </div>

    <!-- 筛选条 -->
    <div class="card pm-toolbar">
      <div class="pm-search">
        <span class="s-ico">⌕</span>
        <input v-model.trim="f.keyword" placeholder="搜名称 / 标签 / ID…" @keyup.enter="applyFilter" />
      </div>
      <select v-model="f.category" @change="applyFilter">
        <option value="">全部分类</option>
        <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="f.city" @change="applyFilter">
        <option value="">全部城市</option>
        <option v-for="c in cityOptions" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="f.sort" @change="applyFilter">
        <option value="">最近更新</option>
        <option value="sales">按销量</option>
        <option value="price_desc">价格高→低</option>
        <option value="price_asc">价格低→高</option>
        <option value="newest">按新建</option>
      </select>
      <div class="pm-status-tabs">
        <button :class="{ on: f.status === 'all' }" @click="setStatus('all')">全部 {{ rows.length }}</button>
        <button :class="{ on: f.status === 'listed' }" @click="setStatus('listed')">启用 {{ stats.online }}</button>
        <button :class="{ on: f.status === 'off' }" @click="setStatus('off')">停用 {{ stats.offline }}</button>
      </div>
    </div>

    <!-- 批量操作 -->
    <div class="pm-batch" v-if="selected.length">
      已选 <b class="num">{{ selected.length }}</b> 个标品
      <button class="btn btn-primary btn-sm" @click="bulkSet(true)">批量上架</button>
      <button class="btn btn-ghost btn-sm" @click="bulkSet(false)">批量下架</button>
      <button class="pm-unselect" @click="selected = []">取消选择 ✕</button>
    </div>

    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>加载中…</div>

    <!-- 表格 -->
    <div v-else-if="!rows.length" class="empty card">
      <div class="icon">📦</div><p>暂无匹配的素材，点右上角「新建素材」收录第一个点位吧；收录后即可在「行程组装器」编排进方案。</p>
    </div>

    <div v-else class="card pm-table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th style="width:36px"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
            <th>标品</th>
            <th>分类 / 城市</th>
            <th>价格（起）</th>
            <th>库存</th>
            <th>销量</th>
            <th>状态</th>
            <th style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in rows" :key="p.id">
            <td><input type="checkbox" v-model="selected" :value="p.id" /></td>
            <td>
              <div class="pm-prod">
                <span class="pm-cover" :style="{ background: p.cover?.gradient }">{{ p.cover?.emoji }}</span>
                <div class="pm-prod-info">
                  <b>{{ p.name }}</b>
                  <span class="pm-id">{{ p.id }}<i v-if="p.source === 'manual'" class="pm-tag-manual">自建</i></span>
                </div>
              </div>
            </td>
            <td>
              <span class="pm-cat">{{ p.category }}</span>
              <span class="pm-city">📍 {{ p.city }}</span>
            </td>
            <td class="pm-price">
              <template v-if="p.price_min === 0 && p.skus.every(s => s.price === 0)">免费</template>
              <template v-else>
                ¥{{ p.skus.filter(s => s.price > 0).length ? minPositive(p.skus) : 0 }}
                <span v-if="p.price_max > p.price_min" class="dim">~¥{{ p.price_max }}</span>
              </template>
            </td>
            <td class="pm-stock">
              {{ totalStock(p.skus) }}
              <span v-if="hasZeroStock(p.skus)" class="dot-warn" title="存在 0 库存规格">●</span>
            </td>
            <td>{{ p.sales }}</td>
            <td><span class="pm-state" :class="p.listed ? 'on' : 'off'">{{ p.listed ? '在架' : '下架' }}</span></td>
            <td>
              <div class="pm-ops">
                <button class="op" @click="openEdit(p)">编辑</button>
                <button class="op" @click="toggleStatus(p)">{{ p.listed ? '停用' : '启用' }}</button>
                <button class="op" @click="goContainingPlan(p)">含它的方案</button>
                <button v-if="p.source === 'manual'" class="op danger" @click="removeOne(p)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建 / 编辑抽屉 -->
    <ProductFormDrawer v-if="showEditor" :product="editorProduct"
                       @close="showEditor = false" @save="onSave" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { productsApi, planShopApi } from '../../api'
import { toast } from '../../composables/toast'
import ProductFormDrawer from './ProductFormDrawer.vue'

const loading = ref(true)
const all = ref([])             // 全量（含下架）
const rows = ref([])
const selected = ref([])
const showEditor = ref(false)
const editorProduct = ref(null)

const f = reactive({ keyword: '', category: '', city: '', status: 'all', sort: '' })

const stats = computed(() => {
  const online = all.value.filter(p => p.listed).length
  const offline = all.value.length - online
  const skus = all.value.reduce((s, p) => s + p.skus.length, 0)
  const stock = all.value.reduce((s, p) => s + totalStock(p.skus), 0)
  const low = all.value.filter(p => p.listed && hasZeroStock(p.skus)).length
  const sales = all.value.reduce((s, p) => s + (Number(p.sales) || 0), 0)
  return { online, offline, skus, stock, low, sales }
})
const categoryOptions = computed(() => [...new Set(all.value.map(p => p.category))])
const cityOptions = computed(() => [...new Set(all.value.map(p => p.city).filter(Boolean))])
const allChecked = computed(() => rows.value.length > 0 && selected.value.length === rows.value.length)

onMounted(load)
async function load() {
  loading.value = true
  try {
    const r = await productsApi.manageList({ page_size: 300 })
    all.value = r.items || []
    applyFilter()
  } catch (e) {
    toast('标品加载失败：' + (e.message || e), 'err')
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  let list = all.value.slice()
  const k = f.keyword.trim().toLowerCase()
  if (k) list = list.filter(p => (p.name + ' ' + (p.tags || []).join(' ') + ' ' + p.id).toLowerCase().includes(k))
  if (f.category) list = list.filter(p => p.category === f.category)
  if (f.city) list = list.filter(p => p.city === f.city)
  if (f.status === 'listed') list = list.filter(p => p.listed)
  else if (f.status === 'off') list = list.filter(p => !p.listed)
  if (f.sort === 'sales') list.sort((a, b) => b.sales - a.sales)
  else if (f.sort === 'newest') list.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
  else if (f.sort === 'price_asc') list.sort((a, b) => a.price_min - b.price_min)
  else if (f.sort === 'price_desc') list.sort((a, b) => b.price_min - a.price_min)
  rows.value = list
  selected.value = selected.value.filter(id => list.some(p => p.id === id))
}
function setStatus(s) { f.status = s; applyFilter() }
function toggleAll(e) {
  selected.value = e.target.checked ? rows.value.map(p => p.id) : []
}

function minPositive(skus) {
  const arr = skus.filter(s => s.price > 0).map(s => s.price)
  return arr.length ? Math.min(...arr) : 0
}
function totalStock(skus) { return (skus || []).reduce((s, k) => s + (Number(k.stock) || 0), 0) }
function hasZeroStock(skus) { return (skus || []).some(k => (Number(k.stock) || 0) === 0) }

function openNew() { editorProduct.value = null; showEditor.value = true }
function openEdit(p) { editorProduct.value = { ...p, skus: p.skus.map(s => ({ ...s })) }; showEditor.value = true }

async function onSave({ payload, editing }) {
  try {
    if (editing) {
      await productsApi.update(editorProduct.value.id, payload)
      toast(`「${payload.name}」已更新，游客端即时生效`, 'ok')
    } else {
      await productsApi.create(payload)
      toast(`「${payload.name}」已上架到游客端商城`, 'ok')
    }
    showEditor.value = false
    load()
  } catch (e) {
    toast('保存失败：' + (e.message || e), 'err')
  }
}

async function toggleStatus(p) {
  try {
    const r = await productsApi.setStatus(p.id, !p.listed)
    p.listed = r.listed
    toast(r.listed ? `「${p.name}」已启用，可被新方案引用` : `「${p.name}」已停用，不再入新方案`, 'ok')
    applyFilter()
  } catch (e) {
    toast('操作失败：' + (e.message || e), 'err')
  }
}

async function bulkSet(listed) {
  const targets = selected.value
  try {
    for (const id of targets) {
      await productsApi.setStatus(id, listed)
    }
    toast(`已批量${listed ? '上架' : '下架'} ${targets.length} 个标品`, 'ok')
    selected.value = []
    load()
  } catch (e) {
    toast('批量操作失败：' + (e.message || e), 'err')
  }
}

async function removeOne(p) {
  if (!window.confirm(`确认删除「${p.name}」？该标品将从游客端移除。`)) return
  try {
    await productsApi.remove(p.id)
    toast('标品已删除', 'ok')
    load()
  } catch (e) {
    toast('删除失败：' + (e.message || e), 'err')
  }
}

function goContainingPlan(p) {
  // 素材不再单独售卖：跳到「含它的方案」去走游客链路
  const item = p
  planShopApi.manageList({ page_size: 60 }).then(r => {
    const plans = (r.items || []).filter(x => x.listed && (x.product_ids || []).includes(item.id))
    if (!plans.length) { toast(`「${item.name}」暂未被任何已上架方案引用`, 'warn'); return }
    const first = plans[0]
    window.open(`${location.origin}${location.pathname}#/malls/product/${first.id}`, '_blank')
  }).catch(() => { toast('查询失败', 'err') })
}
</script>

<style scoped>
.page-actions { display: flex; gap: 10px; }
.pm-stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 16px; }
.pm-stat {
  background: var(--bg-panel); border: 1px solid var(--line); border-radius: 14px;
  padding: 14px 16px; display: flex; flex-direction: column; gap: 4px;
}
.pm-stat span { font-size: 12px; color: var(--text-faint); }
.pm-stat b { font-size: 24px; color: var(--text); font-family: var(--mono); }
.pm-stat i { font-size: 11px; color: var(--text-faint); font-style: normal; }
.pm-stat.warn b { color: var(--warn); }

.pm-toolbar { display: flex; gap: 10px; align-items: center; padding: 12px 14px; margin-bottom: 14px; flex-wrap: wrap; }
.pm-toolbar select {
  background: var(--bg-panel); color: var(--text-dim); border: 1px solid var(--line);
  border-radius: 8px; padding: 7px 10px; font-size: 13px; font-family: inherit;
}
.pm-search { position: relative; flex: 1; min-width: 200px; }
.pm-search .s-ico { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-faint); }
.pm-search input {
  width: 100%; background: var(--bg-panel); border: 1px solid var(--line); color: var(--text);
  border-radius: 8px; padding: 8px 12px 8px 34px; font-size: 13px; box-sizing: border-box;
}
.pm-status-tabs { display: flex; gap: 2px; background: var(--bg-panel); padding: 3px; border-radius: 9px; }
.pm-status-tabs button {
  border: none; background: transparent; color: var(--text-faint); padding: 7px 13px;
  border-radius: 7px; cursor: pointer; font-size: 13px; font-family: inherit;
}
.pm-status-tabs button.on { background: var(--brand-dim); color: #04121F; font-weight: 700; }

.pm-batch {
  display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding: 10px 14px;
  background: rgba(14, 165, 233, .12); border: 1px dashed var(--brand-dim); border-radius: 10px;
  color: var(--text-dim); font-size: 13px;
}
.pm-batch .num { color: var(--brand); font-family: var(--mono); }
.pm-unselect { border: none; background: none; color: var(--text-faint); cursor: pointer; margin-left: auto; }

.pm-table-wrap { padding: 4px 6px; }
.pm-prod { display: flex; align-items: center; gap: 10px; }
.pm-cover {
  width: 34px; height: 34px; border-radius: 8px; flex: none;
  display: flex; align-items: center; justify-content: center; font-size: 18px;
}
.pm-prod-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pm-prod-info b { color: var(--text); font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px; }
.pm-id { font-size: 11px; color: var(--text-faint); font-family: var(--mono); display: flex; align-items: center; gap: 6px; }
.pm-tag-manual { background: rgba(167, 139, 250, .18); color: var(--purple); font-size: 10px; padding: 1px 6px; border-radius: 5px; font-family: inherit; }
.pm-cat { color: var(--brand); font-size: 12px; }
.pm-city { color: var(--text-faint); font-size: 12px; margin-left: 4px; }
.pm-price { color: var(--warn); font-family: var(--mono); }
.pm-price .dim { color: var(--text-faint); font-size: 11.5px; }
.pm-stock { font-family: var(--mono); }
.dot-warn { color: var(--warn); margin-left: 5px; font-size: 10px; }
.pm-state { font-size: 12px; padding: 2px 10px; border-radius: 999px; font-weight: 600; }
.pm-state.on { background: rgba(52, 211, 153, .14); color: var(--ok); }
.pm-state.off { background: var(--bg-hover); color: var(--text-faint); }
.pm-ops { display: flex; gap: 10px; justify-content: flex-end; white-space: nowrap; }
.op { background: none; border: none; color: var(--brand); cursor: pointer; font-size: 12.5px; padding: 2px 0; }
.op:hover { text-decoration: underline; }
.op.danger { color: var(--danger); }
</style>
