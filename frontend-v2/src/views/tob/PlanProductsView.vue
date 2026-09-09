<template>
  <div class="plan-admin">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h1>🧭 方案上架</h1>
        <p>把素材按天排好的线路变成游客可整订的产品：报价按人、余位按团期、上下架即游客端可见开关。</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="load">↻ 刷新</button>
        <button class="btn btn-primary btn-sm" @click="openNew">＋ 新建方案</button>
      </div>
    </div>

    <!-- 流程说明 -->
    <div class="flow card">
      <div class="flow-step"><i>①</i><b>素材库</b><span>景点/餐饮/住宿标品（需已启用）</span></div>
      <div class="flow-arr">→</div>
      <div class="flow-step"><i>②</i><b>行程组装器</b><span>按天排动线、定节奏（Composer）</span></div>
      <div class="flow-arr">→</div>
      <div class="flow-step on"><i>③</i><b>方案上架</b><span>定整订人均报价 / 余位 → 一键上架</span></div>
      <div class="flow-arr">→</div>
      <div class="flow-step"><i>④</i><b>游客整订</b><span>游客端只卖「方案」，不再单卖门票车票</span></div>
    </div>

    <!-- 统计条 -->
    <div class="stats">
      <div class="stat card"><div class="st-label">已上架方案</div><div class="st-num">{{ online }}</div></div>
      <div class="stat card"><div class="st-label">草稿 / 下架</div><div class="st-num dim">{{ offline }}</div></div>
      <div class="stat card"><div class="st-label">当前总余位</div><div class="st-num">{{ stockSum }}</div></div>
      <div class="stat card"><div class="st-label">累计售出（人·团）</div><div class="st-num">{{ salesSum }}</div></div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar card">
      <input v-model.trim="kw" class="input" style="max-width:300px" placeholder="按方案名 / 城市 / 主题筛选…" @keydown.enter="load" />
      <button class="btn btn-soft btn-sm" @click="load">查询</button>
      <div class="spacer"></div>
      <label class="only"><input type="checkbox" v-model="onlyOff" @change="load" /> 只看下架/草稿</label>
    </div>

    <!-- 表格 -->
    <div class="table card">
      <table>
        <thead>
          <tr>
            <th class="c-plan">方案（动线就绪）</th>
            <th>城市 / 天数</th>
            <th>整订报价</th>
            <th>余位 / 销量</th>
            <th>评分</th>
            <th>状态</th>
            <th class="c-ops">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in list" :key="p.id">
            <td>
              <div class="plan-cell">
                <span class="pc-cover" :style="{ background: p.cover?.gradient || '#E08A3C' }">{{ p.cover?.emoji || '🧭' }}</span>
                <div>
                  <div class="pc-name">{{ p.title }}</div>
                  <div class="pc-sub">{{ p.subtitle || p.theme }}</div>
                  <div class="pc-tags">
                    <span v-for="b in (p.badges || []).slice(0, 3)" :key="b">{{ b }}</span>
                  </div>
                </div>
              </div>
            </td>
            <td>
              <div class="cell-main">{{ p.city }} · {{ p.days }} 日</div>
              <div class="cell-sub">{{ p.poi_count }} 点位 · {{ p.pace_zh }}</div>
            </td>
            <td>
              <div class="cell-price"><b>¥{{ p.per_price }}</b><span>/人</span></div>
              <s v-if="p.original_per_price > p.per_price" class="cell-orig">¥{{ p.original_per_price }}</s>
              <div class="cell-sub">≥ {{ p.min_persons }} 人成团</div>
            </td>
            <td>
              <div class="cell-stock" :class="{ low: (p.stock || 0) <= 3 }">余 {{ p.stock }}</div>
              <div class="cell-sub">售 {{ p.sales }} · ★ {{ Number(p.rating).toFixed(1) }}</div>
            </td>
            <td class="cell-star">★ {{ Number(p.rating).toFixed(1) }}</td>
            <td>
              <span class="st-pill" :class="p.listed ? 'on' : 'off'">{{ p.listed ? '已上架' : '已下架' }}</span>
            </td>
            <td>
              <div class="pm-ops">
                <button class="op" @click="openEdit(p)">编辑</button>
                <button class="op" @click="toggle(p)">{{ p.listed ? '下架' : '上架' }}</button>
                <button class="op danger" @click="removeOne(p)">删除</button>
                <button class="op link" @click="preview(p)">游客预览 →</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && !list.length" class="empty-row">
        暂无方案{{ onlyOff ? '（下架/草稿）' : '' }} —— 先在「行程组装器」排好动线，再回来定价上架
      </div>
    </div>

    <!-- 编辑抽屉 -->
    <div v-if="show" class="drawer-mask" @click.self="show = false">
      <div class="drawer card">
        <div class="dr-title">{{ editing ? '编辑方案 · 调整上架参数' : '新建方案上架' }}</div>

        <div class="dr-grid">
          <label class="field wide"><span>方案名称 <b>*</b></span>
            <input v-model.trim="f.title" class="input" placeholder="如：苏州园林双日经典" /></label>
          <label class="field"><span>城市 <b>*</b></span>
            <input v-model.trim="f.city" class="input" placeholder="苏州 / 北京" list="city-list" />
            <datalist id="city-list"><option v-for="c in cities" :key="c" :value="c" /></datalist></label>
          <label class="field"><span>主题分类</span>
            <select v-model="f.category" class="select">
              <option v-for="t in planTax" :key="t.name" :value="t.name">{{ t.emoji }} {{ t.name }}</option>
            </select></label>
          <label class="field"><span>天数</span>
            <select v-model.number="f.days" class="select">
              <option v-for="d in 7" :key="d" :value="d">{{ d }} 日</option>
            </select></label>
          <label class="field"><span>节奏</span>
            <select v-model="f.pace" class="select">
              <option value="leisure">悠闲</option><option value="standard">标准</option><option value="compact">紧凑</option>
            </select></label>
          <label class="field"><span>封面 emoji</span>
            <select v-model="f.coverEmoji" class="select">
              <option v-for="e in EMOJIS" :key="e" :value="e">{{ e }}</option>
            </select></label>

          <div class="sec-title-line">报价与库存</div>
          <label class="field"><span>整订人均价 ¥ <b>*</b></span>
            <input v-model.number="f.per_price" class="input" type="number" min="1" placeholder="例如 880" /></label>
          <label class="field"><span>门市参考价 ¥</span>
            <input v-model.number="f.original_per_price" class="input" type="number" min="0" placeholder="可不填" /></label>
          <label class="field"><span>余位（可成团数）</span>
            <input v-model.number="f.stock" class="input" type="number" min="0" placeholder="40" /></label>
          <label class="field"><span>成团人数（人起）</span>
            <input v-model.number="f.min_persons" class="input" type="number" min="1" placeholder="2" /></label>
          <label class="field wide"><span>卖点角标（逗号分隔）</span>
            <input v-model="f.badges" class="input" placeholder="热销, 亲子友好, 余位紧张" /></label>

          <p class="dr-note wide">点位动线请在「行程组装器」里编排；此处新建会先为该城市随机挂载一组已启用素材用于演示，回编辑器再精排。</p>
        </div>

        <div class="dr-foot">
          <label class="switch"><input type="checkbox" v-model="f.listed" /><i></i><span>立即上架（游客端可见）</span></label>
          <div class="dr-actions">
            <button class="btn btn-ghost" @click="show = false">取消</button>
            <button class="btn btn-primary" :disabled="saving || !f.title || !f.city || !f.per_price" @click="save">
              <span v-if="saving" class="spinner"></span>{{ editing ? '保存修改' : '创建并上架' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { planShopApi } from '../../api'
import { toast } from '../../composables/toast'

const list = ref([])
const loading = ref(true)
const kw = ref('')
const onlyOff = ref(false)
const show = ref(false)
const editing = ref(false)
const editingId = ref('')
const saving = ref(false)

const EMOJIS = ['🏯', '🏞', '🏛', '⛩', '🏮', '🧗', '🌊', '🏔', '🛶', '🎡', '🌆', '🗿', '🍜', '🏺']
// 主题分类取自后端方案馆分类接口（themes 与种子分类同源）
const planTax = ref([])
const f = reactive({ title: '', city: '', category: '园林古建', days: 2, pace: 'standard', coverEmoji: '🏯', per_price: null, original_per_price: null, stock: 40, min_persons: 2, badges: '', listed: true })

const cities = computed(() => {
  const s = new Set(list.value.map(p => p.city).filter(Boolean))
  return [...s]
})
const online = computed(() => list.value.filter(p => p.listed).length)
const offline = computed(() => list.value.length - online.value)
const stockSum = computed(() => list.value.reduce((a, p) => a + (Number(p.stock) || 0), 0))
const salesSum = computed(() => list.value.reduce((a, p) => a + (Number(p.sales) || 0), 0))

async function load() {
  loading.value = true
  try {
    const params = { page_size: 60 }
    if (kw.value.trim()) params.keyword = kw.value.trim()
    const r = await planShopApi.manageList(params)
    list.value = (r.items || []).filter(p => !onlyOff.value || !p.listed)
  } catch (e) {
    toast('方案管理列表加载失败：' + (e.message || e), 'err')
  } finally { loading.value = false }
}

function resetF() {
  Object.assign(f, { title: '', city: '', category: '园林古建', days: 2, pace: 'standard', coverEmoji: '🏯', per_price: null, original_per_price: null, stock: 40, min_persons: 2, badges: '', listed: true })
}
function openNew() {
  editing.value = false
  editingId.value = ''
  resetF()
  show.value = true
}
function openEdit(p) {
  editing.value = true
  editingId.value = p.id
  Object.assign(f, {
    title: p.title, city: p.city, category: p.category || '园林古建',
    days: p.days, pace: p.pace || 'standard', coverEmoji: p.cover?.emoji || '🏯',
    per_price: p.per_price, original_per_price: p.original_per_price || null,
    stock: p.stock, min_persons: p.min_persons || 2,
    badges: (p.badges || []).join(','), listed: !!p.listed,
  })
  show.value = true
}

async function save() {
  if (!f.title.trim() || !f.city.trim() || !f.per_price) { toast('请补齐名称、城市与人均报价', 'warn'); return }
  saving.value = true
  const payload = {
    title: f.title.trim(), city: f.city.trim(), category: f.category, days: Number(f.days) || 1,
    pace: f.pace, cover: { emoji: f.coverEmoji, gradient: null },
    per_price: Number(f.per_price), original_per_price: Number(f.original_per_price || f.per_price),
    stock: Number(f.stock || 0), min_persons: Number(f.min_persons || 2),
    badges: f.badges.split(/[,，]/).map(x => x.trim()).filter(Boolean),
    listed: f.listed,
  }
  try {
    if (editing.value) await planShopApi.update(editingId.value, payload)
    else await planShopApi.create(payload)
    toast(editing.value ? '方案已更新' : '方案已创建并上架', 'ok')
    show.value = false
    await load()
  } catch (e) {
    toast('保存失败：' + (e.message || e), 'err')
  } finally { saving.value = false }
}

async function toggle(p) {
  try {
    await planShopApi.setStatus(p.id, !p.listed)
    toast(`已${p.listed ? '下架' : '上架'}「${p.title}」`, 'ok')
    await load()
  } catch (e) { toast('操作失败：' + (e.message || e), 'err') }
}
async function removeOne(p) {
  if (!confirm(`确认删除方案「${p.title}」？该操作仅对演示数据生效。`)) return
  try {
    await planShopApi.remove(p.id)
    toast('已删除', 'ok')
    await load()
  } catch (e) { toast('删除失败：' + (e.message || e), 'err') }
}
function preview(p) {
  if (!p.listed) { toast('下架方案游客不可见；先上架再预览', 'warn'); return }
  window.open(`${location.origin}${location.pathname}#/malls/product/${p.id}`, '_blank')
}

onMounted(() => {
  load()
  // 主题分类：后端 /api/plan-products/categories（themes 与种子分类同源，含 emoji）
  planShopApi.categories()
    .then(r => { planTax.value = r.themes || [] })
    .catch(() => { planTax.value = [] })
})
</script>

<style scoped>
.plan-admin { display: flex; flex-direction: column; gap: 18px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.page-head h1 { margin: 0; font-size: 22px; font-weight: 800; color: var(--text); }
.page-head p { margin: 6px 0 0; font-size: 13px; color: var(--text-faint); max-width: 640px; line-height: 1.7; }
.page-actions { display: flex; gap: 8px; }
.card { background: var(--bg-panel); border: 1px solid var(--line); border-radius: 12px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all .14s; border: 1px solid transparent; }
.btn-sm { padding: 6px 12px; font-size: 12.5px; }
.btn-primary { background: var(--brand); color: #231a10; border-color: var(--brand); }
.btn-primary:hover { background: var(--brand-2); }
.btn-ghost { background: transparent; border-color: var(--line); color: var(--text-dim); }
.btn-ghost:hover { border-color: var(--brand); color: var(--brand); }
.btn-soft { background: var(--bg-raised); border-color: var(--line); color: var(--text-dim); }
.btn-soft:hover { color: var(--text); }
.spinner { width: 15px; height: 15px; border-radius: 50%; border: 2px solid rgba(255,255,255,.5); border-top-color: #fff; display: inline-block; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.flow { display: flex; align-items: center; gap: 8px; padding: 14px 18px; flex-wrap: wrap; }
.flow-step { display: flex; flex-direction: column; gap: 1px; min-width: 118px; font-size: 11px; color: var(--text-faint); }
.flow-step i { font-style: normal; font-size: 12px; color: var(--brand); font-weight: 700; }
.flow-step b { color: var(--text); font-size: 13px; }
.flow-step.on b { color: var(--brand); }
.flow-arr { color: var(--text-faint); opacity: .5; }

.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat { padding: 14px 18px; }
.st-label { font-size: 12px; color: var(--text-faint); }
.st-num { font-size: 24px; font-weight: 800; color: var(--brand); margin-top: 2px; }
.st-num.dim { color: var(--text-dim); }

.toolbar { display: flex; align-items: center; gap: 10px; padding: 12px 14px; flex-wrap: wrap; }
.spacer { flex: 1; }
.only { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--text-dim); cursor: pointer; }
.only input { accent-color: var(--brand); }

.table { overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead th {
  text-align: left; font-size: 11.5px; font-weight: 700; color: var(--text-faint); letter-spacing: .06em;
  padding: 12px 14px; border-bottom: 1px solid var(--line); background: var(--bg-raised);
  white-space: nowrap;
}
tbody td { padding: 12px 14px; border-bottom: 1px solid var(--line-soft); vertical-align: middle; }
tbody tr:hover td { background: rgba(255,255,255,.015); }
.c-plan { width: 30%; }
.c-ops { width: 200px; }
.plan-cell { display: flex; gap: 10px; align-items: center; }
.pc-cover { width: 46px; height: 40px; flex: none; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.pc-name { font-weight: 700; color: var(--text); font-size: 13.5px; }
.pc-sub { font-size: 12px; color: var(--text-faint); margin-top: 2px; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pc-tags { display: flex; gap: 4px; margin-top: 4px; }
.pc-tags span { font-size: 10.5px; color: var(--brand); background: var(--brand-bg); padding: 1px 7px; border-radius: 3px; }
.cell-main { color: var(--text); font-weight: 600; }
.cell-sub { font-size: 11.5px; color: var(--text-faint); margin-top: 2px; }
.cell-price b { font-size: 17px; color: var(--brand); font-weight: 800; }
.cell-price span { font-size: 11px; color: var(--text-faint); }
.cell-orig { font-size: 11px; color: var(--text-faint); opacity: .7; }
.cell-stock { font-weight: 700; color: var(--ok); }
.cell-stock.low { color: var(--warn); }
.cell-star { color: var(--warn); font-weight: 700; white-space: nowrap; }
.st-pill { padding: 3px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 700; white-space: nowrap; }
.st-pill.on { background: rgba(111,191,115,.14); color: var(--ok); }
.st-pill.off { background: rgba(224,122,107,.12); color: var(--danger); }
.pm-ops { display: flex; gap: 6px; flex-wrap: wrap; }
.pm-ops .op { background: none; border: none; cursor: pointer; font-size: 12px; color: var(--text-dim); padding: 2px 2px; }
.pm-ops .op:hover { color: var(--brand); }
.pm-ops .op.danger:hover { color: var(--danger); }
.pm-ops .op.link { color: var(--brand); font-weight: 600; }
.empty-row { text-align: center; color: var(--text-faint); padding: 40px 0; font-size: 13px; }

.drawer-mask { position: fixed; inset: 0; background: rgba(8,6,4,.6); z-index: 60; display: flex; justify-content: flex-end; }
.drawer { width: 620px; max-width: 94vw; height: 100%; border-radius: 0; display: flex; flex-direction: column; padding: 22px 26px; background: var(--bg-panel); overflow-y: auto; }
.dr-title { font-size: 17px; font-weight: 800; color: var(--text); margin-bottom: 18px; }
.dr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 14px; }
.field { display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; color: var(--text-dim); }
.field.wide { grid-column: 1 / -1; }
.field b { color: var(--danger); }
.sec-title-line { grid-column: 1 / -1; font-size: 12px; font-weight: 800; color: var(--brand); letter-spacing: .1em; border-top: 1px solid var(--line); padding-top: 10px; margin-top: 4px; }
.input, .select { background: var(--bg-raised); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 8px 10px; font-size: 13px; outline: none; width: 100%; box-sizing: border-box; }
.input:focus, .select:focus { border-color: var(--brand); }
.dr-note { font-size: 11.5px; color: var(--text-faint); line-height: 1.7; margin: 2px 0 0; background: var(--bg-raised); border-radius: 8px; padding: 8px 12px; }
.dr-foot { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 22px; border-top: 1px solid var(--line); padding-top: 16px; flex-wrap: wrap; }
.switch { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-dim); cursor: pointer; }
.switch input { display: none; }
.switch i { width: 36px; height: 20px; border-radius: 999px; background: var(--bg-hover); position: relative; transition: all .18s; }
.switch i::after { content: ''; position: absolute; left: 2px; top: 2px; width: 16px; height: 16px; border-radius: 50%; background: var(--text-faint); transition: all .18s; }
.switch input:checked + i { background: var(--brand-bg); }
.switch input:checked + i::after { left: 18px; background: var(--brand); }
.dr-actions { display: flex; gap: 10px; }
</style>
