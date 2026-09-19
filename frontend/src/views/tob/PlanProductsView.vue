<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TobIcon from '../../components/TobIcon.vue'
import { planShopApi } from '../../api/index.js'

/* 方案上架自动化：热门目的地 → 自动生成方案草稿（下架态）→ 人工审核上架 */
const autoSug = ref([])
const autoLoading = ref(false)
const autoMsg = ref('')
async function loadAutoSuggestions() {
  autoLoading.value = true
  try {
    const res = await fetch('/api/plan-products/autodraft-suggestions').then(x => x.json())
    autoSug.value = (res && res.items) || []
  } catch { /* ignore */ }
  autoLoading.value = false
}
async function autoCreate(s) {
  autoMsg.value = ''
  try {
    await planShopApi.create({
      title: `${s.city}${s.suggested_days}日 · 热门需求线路`, city: s.city, category: '热门需求',
      days: s.suggested_days, per_price: s.suggested_per_price,
      original_per_price: Math.round(s.suggested_per_price * 1.15),
      min_persons: 2, stock: 20, listed: false,
      subtitle: `依据 ${s.completed_plans} 个真实完成行程自动生成，待审核上架`,
      badges: ['热门需求', '自动生成'],
    })
    autoMsg.value = `已生成「${s.city}」方案草稿（下架态），请在下方列表核对后点「上架」`
    s.done = true
    load()
  } catch (e) { autoMsg.value = e.message || '生成失败' }
}

const router = useRouter()
const kw = ref('')
const onlyOff = ref(false)

/* —— 在售方案管理：GET /api/plan-products/manage + status/remove（回退演示数据） —— */
const FALLBACK = [
  { id: 1, title: '园林三日 · 拙政留园', subtitle: '水巷慢游 · 苏帮菜 · 评弹夜色', city: '苏州', days: 3, poi: 12, pace: '标准', price: 1280, orig: 1480, min: 2, stock: 18, sales: 342, rating: 4.8, listed: true },
  { id: 2, title: '西湖人文四日', subtitle: '环湖骑行 · 龙井问茶 · 灵隐禅意', city: '杭州', days: 4, poi: 15, pace: '悠闲', price: 1680, orig: 0, min: 2, stock: 6, sales: 218, rating: 4.9, listed: true },
  { id: 3, title: '苍洱五日 · 白族家访', subtitle: '洱海生态 · 喜洲古镇 · 扎染工坊', city: '大理', days: 5, poi: 16, pace: '悠闲', price: 2280, orig: 2580, min: 2, stock: 12, sales: 186, rating: 4.7, listed: true },
]
const plans = ref(FALLBACK)

function toRow(raw = {}) {
  return {
    id: raw.id,
    title: raw.title || raw.name || '',
    subtitle: raw.subtitle || '',
    city: raw.city || '',
    days: raw.days || 1,
    poi: raw.poi_count || 0,
    pace: raw.pace_zh ? raw.pace_zh.replace('节奏', '') : (raw.pace === 'standard' ? '标准' : raw.pace === 'relaxed' ? '悠闲' : raw.pace === 'tight' ? '紧凑' : (raw.pace || '标准')),
    price: Number(raw.per_price) || 0,
    orig: Number(raw.original_per_price) || 0,
    min: raw.min_persons || 2,
    stock: raw.stock ?? 0,
    sales: raw.sales || 0,
    rating: raw.rating || 4.8,
    listed: raw.listed !== false,
  }
}

async function load() {
  try {
    const res = await planShopApi.manageList({ page: 1, page_size: 100 })
    const rows = (res && res.items) || []
    if (rows.length) plans.value = rows.map(toRow)
  } catch { /* 未登录/网络异常：保留演示数据 */ }
}
onMounted(() => { load(); loadAutoSuggestions() })
async function refresh() { await load() }

async function toggleListed(p) {
  try {
    await planShopApi.setStatus(p.id, !p.listed)
    p.listed = !p.listed
  } catch { p.listed = !p.listed }
}
async function removePlan(p) {
  if (!window.confirm(`确认删除方案「${p.title}」?`)) return
  try { await planShopApi.remove(p.id) } catch { /* 本地仍移除 */ }
  plans.value = plans.value.filter(x => x.id !== p.id)
}

const rows = computed(() => plans.value.filter(p =>
  (!onlyOff.value || !p.listed) &&
  (!kw.value || (p.title + p.city).includes(kw.value))
))

const stats = computed(() => ({
  online: plans.value.filter(p => p.listed).length,
  offline: plans.value.filter(p => !p.listed).length,
  stock: plans.value.reduce((s, p) => s + (p.stock || 0), 0),
  sales: plans.value.reduce((s, p) => s + p.sales, 0),
}))

const FLOW = [
  { n: '1', t: '素材库', d: '景点/餐饮/住宿标品(需已启用)', on: false },
  { n: '2', t: '行程组装器', d: '按天排动线、定节奏(Composer)', on: false },
  { n: '3', t: '方案上架', d: '定整订人均报价 / 余位 → 一键上架', on: true },
  { n: '4', t: '游客整订', d: '游客端只卖「方案」,不再单卖门票车票', on: false },
]
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">商品运营</div>
        <h1 class="page-title">方案上架</h1>
        <p class="page-desc">
          把素材按天排好的线路变成游客可整订的产品:报价按人、余位按团期、上下架即游客端可见开关。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="refresh"><TobIcon name="refresh" :size="14" />刷新</button>
        <button class="btn btn-primary btn-sm" @click="router.push('/manual')"><TobIcon name="plus" :size="14" />新建方案</button>
      </div>
    </div>

    <!-- 流程说明 -->
<!-- 方案上架自动化：热门目的地建议 -->
    <div v-if="autoSug.length || autoMsg" class="card autosug-card">
      <div class="as-head"><b>🤖 自动上架建议</b><span class="mono-xs">被反复规划但无在售方案的城市，一键生成草稿（下架态）→ 审核后上架</span></div>
      <div v-for="s in autoSug" :key="s.city" class="as-row">
        <b>{{ s.city }}</b>
        <span class="mono-xs">{{ s.completed_plans }} 个已完成任务 · 建议 {{ s.suggested_days }} 日 · 建议人均 ¥{{ s.suggested_per_price }} · 素材 {{ s.material_count }} 条</span>
        <button class="btn btn-primary btn-sm" :disabled="s.done" @click="autoCreate(s)">{{ s.done ? '已生成草稿' : '生成草稿' }}</button>
      </div>
      <p v-if="autoMsg" class="as-msg">{{ autoMsg }}</p>
    </div>
        <div class="card flow">
      <template v-for="(s, i) in FLOW" :key="s.n">
        <div class="flow-step" :class="{ on: s.on }">
          <i>{{ s.n }}</i>
          <b>{{ s.t }}</b>
          <span>{{ s.d }}</span>
        </div>
        <TobIcon v-if="i < FLOW.length - 1" name="chevron" :size="16" class="flow-arr" />
      </template>
    </div>

    <!-- 统计 -->
    <div class="stat-grid">
      <div class="stat-card"><div class="k">已上架方案</div><div class="v">{{ stats.online }}</div><div class="sub">游客端可见</div></div>
      <div class="stat-card"><div class="k">草稿 / 下架</div><div class="v">{{ stats.offline }}</div><div class="sub">暂不对游客展示</div></div>
      <div class="stat-card"><div class="k">当前总余位</div><div class="v">{{ stats.stock }}</div><div class="sub">全部团期合计</div></div>
      <div class="stat-card"><div class="k">累计售出(人·团)</div><div class="v">{{ stats.sales.toLocaleString() }}</div><div class="sub">历史整订人次</div></div>
    </div>

    <!-- 工具栏 -->
    <div class="card toolbar">
      <div class="search-box">
        <span class="s-ico"><TobIcon name="search" :size="15" /></span>
        <input v-model.trim="kw" placeholder="按方案名 / 城市 / 主题筛选…" />
      </div>
      <button class="btn btn-ghost btn-sm">查询</button>
      <label class="only-check">
        <input type="checkbox" v-model="onlyOff" />
        只看下架 / 草稿
      </label>
    </div>

    <!-- 表格 -->
    <div class="card table-card">
      <table class="table">
        <thead>
          <tr>
            <th>方案(动线就绪)</th>
            <th>城市 / 天数</th>
            <th>整订报价</th>
            <th>余位 / 销量</th>
            <th>评分</th>
            <th>状态</th>
            <th style="text-align:right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in rows" :key="p.id">
            <td>
              <div class="plan-cell">
                <span class="plan-cover"><TobIcon name="compass" :size="16" /></span>
                <div>
                  <div class="cell-main">{{ p.title }}</div>
                  <div class="cell-sub">{{ p.subtitle }}</div>
                </div>
              </div>
            </td>
            <td>
              <div class="cell-main" style="font-weight:var(--fw-regular)">{{ p.city }} · {{ p.days }} 日</div>
              <div class="cell-sub">{{ p.poi }} 点位 · {{ p.pace }}</div>
            </td>
            <td>
              <div><b class="price">¥{{ p.price.toLocaleString() }}</b><span class="cell-sub" style="display:inline"> /人</span></div>
              <s v-if="p.orig > p.price" class="orig">¥{{ p.orig }}</s>
              <div class="cell-sub">≥ {{ p.min }} 人成团</div>
            </td>
            <td>
              <div :class="{ 'stock-low': p.stock <= 5 }">余 {{ p.stock }}</div>
              <div class="cell-sub">售 {{ p.sales }}</div>
            </td>
            <td><span class="rate">★ {{ p.rating.toFixed(1) }}</span></td>
            <td><span class="pill" :class="p.listed ? 'pill-on pill-dot' : 'pill-off pill-dot'">{{ p.listed ? '已上架' : '已下架' }}</span></td>
            <td>
              <div class="ops">
                <button class="op" @click="router.push(`/malls/product/${p.id}`)">编辑</button>
                <button class="op" @click="toggleListed(p)">{{ p.listed ? '下架' : '上架' }}</button>
                <button class="op danger" @click="removePlan(p)">删除</button>
                <button class="op" @click="router.push(`/malls/product/${p.id}`)">游客预览</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
/* 流程条 */
.flow { display: flex; align-items: center; gap: var(--s-4); padding: var(--s-4) var(--s-5); }
.flow-step { display: flex; align-items: center; gap: var(--s-3); flex: 1; min-width: 0; }
.flow-step i {
  width: 26px; height: 26px; border-radius: 50%;
  border: 1px solid var(--border);
  display: inline-flex; align-items: center; justify-content: center;
  font-style: normal; font-size: var(--fs-xs); color: var(--text-3);
  flex: none; font-variant-numeric: tabular-nums;
  transition: all var(--dur-2) var(--ease);
}
.flow-step b { font-size: var(--fs-sm); font-weight: var(--fw-medium); white-space: nowrap; }
.flow-step span { font-size: var(--fs-xs); color: var(--text-faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.flow-step.on i { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
.flow-step.on b { color: var(--accent); }
.flow-arr { color: var(--text-faint); flex: none; }
@media (max-width: 1100px) {
  .flow { flex-wrap: wrap; }
  .flow-step { flex: 1 1 46%; }
  .flow-arr { display: none; }
  .flow-step span { white-space: normal; }
}

.only-check {
  display: inline-flex; align-items: center; gap: var(--s-2);
  margin-left: auto;
  font-size: var(--fs-xs); color: var(--text-3);
  cursor: pointer;
}
.only-check:hover { color: var(--text); }

.plan-cell { display: flex; align-items: center; gap: var(--s-3); }
.plan-cover {
  width: 36px; height: 36px; border-radius: var(--r);
  background: var(--accent-soft); color: var(--accent);
  display: inline-flex; align-items: center; justify-content: center; flex: none;
}
.price { font-variant-numeric: tabular-nums; }
.orig { font-size: var(--fs-xs); color: var(--text-faint); }
.stock-low { color: var(--warn); font-weight: var(--fw-medium); }
.rate { color: var(--accent-2); font-variant-numeric: tabular-nums; font-size: var(--fs-sm); }
.autosug-card { margin-bottom: var(--s-4); padding: var(--s-4) var(--s-5); border: 1px solid var(--accent); }
.as-head { display: flex; align-items: center; gap: var(--s-3); margin-bottom: var(--s-3); }
.as-head span { color: var(--text-3); }
.as-row { display: flex; align-items: center; gap: var(--s-4); padding: var(--s-2) 0; border-bottom: 1px dashed var(--border-soft); }
.as-row b { min-width: 80px; }
.as-msg { margin: var(--s-2) 0 0; font-size: var(--fs-xs); color: #5C7A9D; }
</style>