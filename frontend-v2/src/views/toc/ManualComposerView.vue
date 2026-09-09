<template>
  <div class="container mc">
    <header class="mc-head">
      <div>
        <h1>🧩 手动行程规划</h1>
        <p>从企业标品库挑选景点 / 餐饮 / 住宿 / 交通，按节奏自动排成逐日行程，保存后进入「我的行程」，还能继续微调。</p>
      </div>
    </header>

    <div class="mc-grid">
      <!-- 左：选品（RAG 语义搜索 + 分类过滤） -->
      <section class="card mc-pick">
        <div class="pick-bar">
          <input v-model="q" class="input" placeholder="想玩什么？如「园林 文化」「亲子 美食」" @keyup.enter="onSearch" />
          <button class="btn btn-primary" :disabled="searching || !q.trim()" @click="onSearch">{{ searching ? '检索中…' : '🔍 RAG 搜' }}</button>
        </div>
        <div class="pick-cats">
          <button v-for="c in CATS" :key="c.name" class="chip" :class="{ active: cat === c.name }" @click="cat = c.name; loadCatalog()">{{ c.name }}</button>
        </div>
        <div class="pick-list">
          <article v-for="p in catalog" :key="p.id"
                   :class="['pick-item', { picked: pickedIds.includes(p.id) }]" @click="toggle(p.id)">
            <span class="pi-emoji">{{ p.category === '餐饮' ? '🍜' : p.category === '住宿' ? '🏨' : p.category === '交通' ? '🚄' : p.category === '文化' ? '📜' : '📍' }}</span>
            <div class="pi-body">
              <b>{{ p.name }}</b>
              <em>{{ p.city }} · ⏱ {{ p.typical_dwell || '—' }}</em>
            </div>
            <span class="pi-price">{{ p.price_min ? '¥' + p.price_min + ' 起' : '免费' }}</span>
            <button class="pi-add">{{ pickedIds.includes(p.id) ? '✓' : '＋' }}</button>
          </article>
          <div v-if="!catalog.length" class="pick-empty">{{ searching ? '检索中…' : '暂无标品，换个关键词试试' }}</div>
        </div>
      </section>

      <!-- 中：参数 + 生成 -->
      <section class="card mc-form">
        <h3>行程参数</h3>
        <label class="mf-field"><span>行程名称</span>
          <input v-model.trim="meta.title" class="input" placeholder="如：苏州周末两日" maxlength="24" /></label>
        <div class="mf-row">
          <label class="mf-field"><span>出发日期</span>
            <input v-model="meta.start_date" class="input" type="date" :min="today" /></label>
          <label class="mf-field"><span>出行人数</span>
            <input v-model.number="meta.travelers" class="input" type="number" min="1" max="20" /></label>
        </div>
        <div class="mf-row">
          <label class="mf-field"><span>节奏</span>
            <select v-model="pace" class="select">
              <option value="relaxed">🛋 悠闲（3 段/天）</option>
              <option value="standard">⚖ 标准（4 段/天）</option>
              <option value="tight">⚡ 紧凑（5 段/天）</option>
            </select></label>
          <label class="mf-field"><span>锚点城市</span>
            <select v-model="anchorCity" class="select">
              <option value="">自动</option>
              <option v-for="c in citiesFromCatalog" :key="c" :value="c">{{ c }}</option>
            </select></label>
        </div>
        <button class="btn btn-primary btn-block" :disabled="!pickedIds.length || composing" @click="onCompose">
          {{ composing ? '排程中…' : `🪄 用 ${pickedIds.length} 个标品生成行程` }}
        </button>

        <div v-if="result" class="mc-result">
          <div class="kpi-row">
            <div class="kpi"><span>覆盖率</span><b>{{ (result.coverage_score * 100).toFixed(0) }}%</b></div>
            <div class="kpi"><span>预估门票</span><b>¥{{ result.budget_estimate?.tickets }}</b></div>
            <div class="kpi"><span>总预算</span><b>¥{{ result.budget_estimate?.total }}</b></div>
          </div>
          <div v-if="result.warnings?.length" class="mc-warn">⚠ {{ result.warnings[0] }}</div>
          <ol class="day-list">
            <li v-for="d in result.itinerary" :key="d.day">
              <b>第 {{ d.day }} 天</b>
              <span v-for="b in d.blocks" :key="b.product_id" class="day-chip">{{ b.title }}</span>
            </li>
          </ol>
          <p class="kb-tip">📖 每个时段已附 RAG 知识背书，进入编辑后可查看</p>
          <button class="btn btn-primary btn-block" @click="toEditor">下一步 → 编排细节并保存</button>
        </div>
        <div v-else class="mc-empty">选好标品 → 设置参数 → 一键生成逐日行程</div>
      </section>
    </div>
  </div>
</template>

<script setup>
// toC 手动行程规划（需求4）：toB 组装器能力的游客版
//   RAG 搜索/分类选品 → /api/composer/from-products 排程 → applyComposerResult 装配草稿
//   → 跳 /trip/_new/manual/edit 用 TripDayEditor 继续编排并保存进「我的行程」
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { composerApi, productsApi } from '../../api'
import { toast } from '../../composables/toast'
import { useTripDraft, CATS } from '../../composables/tripDraft'

const router = useRouter()
const D = useTripDraft()

const q = ref('')
const cat = ref('')
const catalog = ref([])
const searching = ref(false)
const pickedIds = ref([])
const composing = ref(false)
const result = ref(null)
const pace = ref('standard')
const anchorCity = ref('')
const meta = reactive({ title: '', start_date: new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10), travelers: 2 })
const today = new Date().toISOString().slice(0, 10)

const citiesFromCatalog = computed(() => [...new Set(catalog.value.map(p => String(p.city || '').split('→')[0].trim()).filter(Boolean))])

async function loadCatalog() {
  try {
    const r = await productsApi.list({ page_size: 100, ...(cat.value ? { category: cat.value } : {}) })
    catalog.value = r.items || []
  } catch (e) { toast('标品目录加载失败：' + (e.message || e), 'err') }
}

async function onSearch() {
  if (!q.value.trim()) return
  searching.value = true
  try {
    const r = await composerApi.searchProducts(q.value.trim(), { top_k: 30 })
    catalog.value = (r.results || []).map(x => x.product)
    toast(`RAG 命中 ${catalog.value.length} 个标品`, 'ok')
  } catch (e) {
    toast('RAG 检索失败：' + (e.message || e), 'err')
  } finally { searching.value = false }
}

function toggle(id) {
  const i = pickedIds.value.indexOf(id)
  i >= 0 ? pickedIds.value.splice(i, 1) : pickedIds.value.push(id)
}

async function onCompose() {
  composing.value = true
  try {
    const perDay = pace.value === 'tight' ? 5 : pace.value === 'relaxed' ? 3 : 4
    const days = Math.max(1, Math.ceil(pickedIds.value.length / perDay))
    const r = await composerApi.compose({
      product_ids: pickedIds.value,
      days,
      pace: pace.value,
      anchor: anchorCity.value ? { city: anchorCity.value } : undefined,
    })
    result.value = r
    toast(`已生成 ${r.itinerary?.length || 0} 天行程`, 'ok')
  } catch (e) {
    toast('生成失败：' + (e.message || e), 'err')
  } finally { composing.value = false }
}

async function toEditor() {
  if (!result.value) return
  const firstPicked = catalog.value.find(p => p.id === pickedIds.value[0])
  const city = anchorCity.value || String(firstPicked?.city || '').split('→')[0] || ''
  const tpl = {
    id: 'manual_' + Date.now().toString(36),
    title: meta.title || '手动行程',
    city, days: result.value.itinerary?.length || 1, pace: pace.value,
    theme: '手动编排', audience: '', season: '全年',
    cover: { emoji: '🧩', gradient: 'linear-gradient(135deg,#86EFAC,#60A5FA)' },
    badges: ['手动'], product_ids: [...pickedIds.value],
    price_total: result.value.budget_estimate?.tickets || 0,
    audience: '', 
  }
  await D.applyComposerResult(tpl, result.value)
  D.draft.meta.title = meta.title || `${city}手动行程`
  D.draft.meta.travelers = meta.travelers || 2
  if (meta.start_date) D.draft.meta.start_date = meta.start_date
  router.push({ name: 'trip-edit', params: { id: '_new' }, query: { manual: 1 } })
}

onMounted(loadCatalog)
</script>

<style scoped>
.mc { padding: 26px 0 46px; }
.mc-head h1 { font-size: 22px; font-weight: 800; margin: 0 0 4px; }
.mc-head p { color: var(--ink-500); font-size: 13.5px; margin: 0 0 18px; }
.mc-grid { display: grid; grid-template-columns: 1.15fr 1fr; gap: 16px; align-items: start; }
.mc-pick { padding: 16px; }
.pick-bar { display: flex; gap: 8px; margin-bottom: 10px; }
.pick-bar .input { flex: 1; }
.pick-cats { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.chip { padding: 5px 13px; border-radius: 999px; border: 1px solid var(--ink-200); background: #fff; cursor: pointer; font-size: 12.5px; font-weight: 600; color: var(--ink-600); }
.chip.active { background: var(--brand-50); border-color: var(--brand-500); color: var(--brand-700); }
.pick-list { display: flex; flex-direction: column; gap: 7px; max-height: 480px; overflow-y: auto; }
.pick-item { display: grid; grid-template-columns: 30px 1fr auto 30px; gap: 8px; align-items: center; padding: 9px 12px; border: 1px solid var(--ink-150, #E4E8EF); border-radius: 11px; cursor: pointer; transition: all .14s; }
.pick-item:hover { border-color: var(--brand-500); background: var(--brand-50); }
.pick-item.picked { border-color: var(--brand-500); background: rgba(59,130,246,.08); }
.pi-emoji { font-size: 19px; text-align: center; }
.pi-body b { display: block; font-size: 13.5px; }
.pi-body em { font-style: normal; font-size: 11.5px; color: var(--ink-400); }
.pi-price { font-size: 12px; color: var(--ink-500); font-weight: 600; }
.pi-add { width: 26px; height: 26px; border-radius: 8px; border: 1px solid var(--ink-200); background: #fff; cursor: pointer; font-size: 14px; color: var(--brand-600); font-weight: 800; }
.pick-item.picked .pi-add { background: var(--brand-600); color: #fff; border-color: var(--brand-600); }
.pick-empty { padding: 30px; text-align: center; color: var(--ink-400); font-size: 13px; }

.mc-form { padding: 18px 20px; }
.mc-form h3 { margin: 0 0 12px; font-size: 15.5px; }
.mf-field { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; flex: 1; }
.mf-field span { font-size: 12.5px; font-weight: 700; color: var(--ink-700); }
.mf-row { display: flex; gap: 10px; }
.mc-result { margin-top: 16px; border-top: 1px dashed var(--ink-200); padding-top: 14px; }
.kpi-row { display: flex; gap: 10px; margin-bottom: 10px; }
.kpi { flex: 1; background: var(--ink-50); border-radius: 10px; padding: 9px 12px; }
.kpi span { font-size: 11px; color: var(--ink-400); display: block; }
.kpi b { font-size: 16px; }
.mc-warn { background: #FFFBEB; border: 1px solid #F59E0B; color: #92400E; font-size: 12px; padding: 8px 12px; border-radius: 9px; margin-bottom: 10px; }
.day-list { margin: 0 0 10px; padding-left: 18px; }
.day-list li { font-size: 12.5px; margin-bottom: 7px; color: var(--ink-700); }
.day-chip { display: inline-block; background: var(--ink-100); border-radius: 6px; padding: 1px 8px; margin: 2px 3px 0 0; font-size: 11.5px; }
.kb-tip { font-size: 11.5px; color: var(--ink-400); margin: 4px 0 12px; }
.mc-empty { margin-top: 16px; border-top: 1px dashed var(--ink-200); padding-top: 26px; text-align: center; color: var(--ink-400); font-size: 13px; }

@media (max-width: 960px) { .mc-grid { grid-template-columns: 1fr; } }
</style>
