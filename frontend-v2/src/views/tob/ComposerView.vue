<template>
  <div class="cv">
    <header class="cv-head">
      <div>
        <h1>🧩 行程组装器 <small>由标品直接拼装可发布的行程模板</small></h1>
        <p class="hint">从标品目录（行程规划用的最小知识单元）挑选条目，算法按 <b>最佳时段</b> + <b>地理就近</b> + <b>行程节奏</b> 自动排成多日行程。生成结果与 RAG 实验室共享标品库，可作为白标交付的"行程模板底稿"。</p>
      </div>
      <div class="head-stats">
        <span>库内标品 <b>{{ catalog.length }}</b> 条</span>
        <span>已选 <b style="color:var(--brand)">{{ selected.length }}</b> 条</span>
        <span>预计天数 <b>{{ params.days }}</b> 天 · {{ paceLabel }}</span>
      </div>
    </header>

    <div class="cv-body">
      <!-- 左：标品目录 -->
      <section class="cv-catalog">
        <div class="cv-controls">
          <div class="seg">
            <button v-for="c in CATEGORIES" :key="c.key"
              :class="['seg-item', { active: filterCat === c.key }]"
              @click="filterCat = c.key">{{ c.emoji }} {{ c.key }}</button>
          </div>
          <select v-model="filterCity" class="select">
            <option value="">全部城市</option>
            <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
        <div class="product-list">
          <article v-for="p in filteredCatalog" :key="p.id"
                   :class="['product', { selected: selected.includes(p.id) }]"
                   @click="toggle(p.id)">
            <div class="p-emoji">{{ catEmoji(p.category) }}</div>
            <div class="p-body">
              <div class="p-title">{{ p.name }}
                <span class="p-tag">{{ p.level }}</span>
              </div>
              <div class="p-meta">
                <span>📍 {{ p.city }}</span>
                <span>⏱ {{ p.typical_dwell }}</span>
                <span v-if="p.ticket.startsWith('¥')">💰 {{ p.ticket }}</span>
                <span v-else>🎫 {{ p.ticket }}</span>
              </div>
              <div class="p-tags">
                <span v-for="t in p.tags" :key="t" class="tg">{{ t }}</span>
              </div>
            </div>
            <div class="p-bar"><i :style="{ width: (p.demand * 100) + '%' }" /></div>
            <button class="p-toggle">
              {{ selected.includes(p.id) ? '✓ 已选' : '＋ 加入' }}
            </button>
          </article>
        </div>
      </section>

      <!-- 中：参数 + 生成 -->
      <section class="cv-compose">
        <div class="card params">
          <h3>行程参数</h3>
          <label>
            <span>天数</span>
            <input type="number" v-model.number="params.days" min="1" max="7" />
          </label>
          <label>
            <span>节奏</span>
            <div class="seg seg-3">
              <button :class="['seg-item', { active: params.pace === 'relaxed' }]" @click="params.pace = 'relaxed'">🛋 悠闲</button>
              <button :class="['seg-item', { active: params.pace === 'standard' }]" @click="params.pace = 'standard'">⚖ 标准</button>
              <button :class="['seg-item', { active: params.pace === 'tight' }]" @click="params.pace = 'tight'">⚡ 紧凑</button>
            </div>
          </label>
          <label>
            <span>人均预算（可选）</span>
            <input type="number" v-model.number="params.budget" placeholder="不限" />
          </label>
          <label>
            <span>锚点城市</span>
            <select v-model="params.city" class="select">
              <option value="">自动</option>
              <option v-for="c in cities" :key="c">{{ c }}</option>
            </select>
          </label>
          <button class="btn btn-primary btn-block" :disabled="!selected.length || composing" @click="onCompose">
            {{ composing ? '生成中…' : `🪄 用 ${selected.length} 个标品生成行程` }}
          </button>
        </div>

        <div v-if="result" class="card result" data-test="composer-result">
          <h3>生成结果 <span class="badge">job_id = {{ (result.job_id || '').slice(0, 16) }}…</span></h3>
          <div class="kpi-row">
            <div class="kpi"><span>标品覆盖率</span><b>{{ (result.coverage_score * 100).toFixed(0) }}%</b></div>
            <div class="kpi"><span>总预算</span><b>¥ {{ result.budget_estimate.total }}</b></div>
            <div class="kpi"><span>未排入</span><b :style="{ color: result.missing_slots > 0 ? 'var(--warn)' : 'var(--ok)' }">{{ result.missing_slots }}</b></div>
          </div>
          <div v-if="result.warnings?.length" class="warn-box">
            <b>⚠ 算法提示：</b>
            <ul><li v-for="w in result.warnings" :key="w">{{ w }}</li></ul>
          </div>
          <div class="day-list">
            <article v-for="d in result.itinerary" :key="d.day" class="day">
              <div class="day-head">
                <span class="day-no">第 {{ d.day }} 天</span>
                <span class="day-count">{{ d.blocks.length }} 个时段</span>
              </div>
              <div class="slots">
                <div v-for="(b, i) in d.blocks" :key="i" class="slot">
                  <div class="slot-time">{{ b.start }}<br><em>{{ b.duration }}</em></div>
                  <div class="slot-body">
                    <b>{{ b.title }}</b>
                    <span class="slot-type">{{ catEmoji(b.type) }} {{ b.type }}</span>
                    <p>{{ b.note }}</p>
                  </div>
                  <div class="slot-tag">{{ slotLabel(b.slot) }}</div>
                </div>
              </div>
            </article>
          </div>
          <div class="action-bar">
            <button class="btn">📤 导出 JSON 模板</button>
            <button class="btn">🏷 转白标交付</button>
            <button class="btn btn-primary">🚀 发布到客户工作台</button>
          </div>
        </div>

        <div v-else class="empty-card">
          <div class="empty-illu">🧩</div>
          <p>从左侧目录挑选标品 → 设置天数与节奏 → 点击生成</p>
          <p class="sub">算法按「最佳时段 + 地理就近 + 节奏密度」三维自动排程</p>
        </div>
      </section>

      <!-- 右：已选清单 -->
      <aside class="cv-selected">
        <h3>已选标品 <span class="badge">{{ selected.length }}</span></h3>
        <ul v-if="selected.length">
          <li v-for="id in selected" :key="id" class="sel-row">
            <span class="sel-emoji">{{ catEmoji(productById(id)?.category) }}</span>
            <div class="sel-body">
              <b>{{ productById(id)?.name }}</b>
              <em>{{ productById(id)?.city }} · {{ productById(id)?.typical_dwell }}</em>
            </div>
            <button class="x" @click="toggle(id)">×</button>
          </li>
        </ul>
        <div v-else class="empty-sel">点击左侧任意标品即可加入</div>
        <div class="alg-box">
          <h4>🔬 组装算法说明</h4>
          <ol>
            <li><b>最佳时段匹配</b>：每个标品有 <code>best_slot</code> 字段（morning / midday / afternoon / evening），优先排在对应时段</li>
            <li><b>地理就近</b>：用 <code>coords</code> 排序，避免一天内跨城</li>
            <li><b>节奏密度</b>：悠闲 3 段/天、标准 4 段、紧凑 5 段</li>
            <li><b>预算估算</b>：按交通 18% / 住宿 32% / 餐饮 28% / 门票 100% 加权</li>
            <li><b>覆盖率评分</b>：已用标品数 / (天数 × 节奏段数)</li>
          </ol>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { composerApi } from '../../api'
import { toast } from '../../composables/toast'

const CATEGORIES = [
  { key: '', 名称: '全部' },
  { key: '景点', 名称: '景点' },
  { key: '餐饮', 名称: '餐饮' },
  { key: '住宿', 名称: '住宿' },
  { key: '交通', 名称: '交通' },
  { key: '购物', 名称: '购物' },
  { key: '文化', 名称: '文化' },
]
const CAT_EMOJI = { 景点: '🏛', 餐饮: '🍜', 住宿: '🏨', 交通: '🚄', 购物: '🛍', 文化: '📚' }

const catalog = ref([])
const selected = ref([])
const filterCat = ref('')
const filterCity = ref('')
const composing = ref(false)
const result = ref(null)

const params = ref({ days: 2, pace: 'standard', budget: null, city: '' })

const cities = computed(() => Array.from(new Set(catalog.value.map(p => p.city.split('→')[0].trim()))))
const filteredCatalog = computed(() => {
  let list = catalog.value
  if (filterCat.value) list = list.filter(p => p.category === filterCat.value)
  if (filterCity.value) list = list.filter(p => p.city.includes(filterCity.value))
  return list
})
const paceLabel = computed(() => ({ relaxed: '🛋 悠闲', standard: '⚖ 标准', tight: '⚡ 紧凑' })[params.value.pace])

function toggle(id) {
  const i = selected.value.indexOf(id)
  if (i >= 0) selected.value.splice(i, 1)
  else selected.value.push(id)
}
function productById(id) { return catalog.value.find(p => p.id === id) }
function catEmoji(cat) { return CAT_EMOJI[cat] || '📌' }
function slotLabel(s) { return { morning: '上午', midday: '午间', afternoon: '下午', evening: '傍晚' }[s] || s }

async function loadCatalog() {
  try {
    const r = await composerApi.listProducts()
    catalog.value = r.products || []
  } catch (e) {
    // mock 兜底（shoot.mjs 会注入 fetch mock）
    toast('标品目录加载失败：' + (e.message || e), 'err')
  }
}

async function onCompose() {
  composing.value = true
  try {
    const r = await composerApi.compose({
      product_ids: selected.value,
      days: params.value.days,
      pace: params.value.pace,
      budget: params.value.budget || undefined,
      anchor: params.value.city ? { city: params.value.city } : undefined,
    })
    result.value = r
    toast(`已用 ${selected.value.length} 个标品生成 ${params.value.days} 天行程模板`, 'ok')
  } catch (e) {
    toast('生成失败：' + (e.message || e), 'err')
  } finally {
    composing.value = false
  }
}

onMounted(loadCatalog)
</script>

<style scoped>
.cv { display: flex; flex-direction: column; gap: 18px; min-height: calc(100vh - 60px); }
.cv-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 18px; flex-wrap: wrap; }
.cv-head h1 { font-size: 22px; font-weight: 800; margin: 0; }
.cv-head h1 small { font-size: 12.5px; font-weight: 600; color: var(--text-faint); margin-left: 8px; }
.cv-head .hint { color: var(--text-dim); font-size: 13px; margin: 6px 0 0; line-height: 1.7; max-width: 720px; }
.head-stats { display: flex; gap: 18px; font-size: 12.5px; color: var(--text-faint); }
.head-stats b { color: var(--text); font-size: 14px; }

.cv-body { display: grid; grid-template-columns: 1fr 1.1fr 280px; gap: 16px; flex: 1; min-height: 0; }
.cv-catalog, .cv-compose, .cv-selected { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px; min-height: 0; }

.cv-controls { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.seg { display: flex; flex-wrap: wrap; gap: 4px; padding: 4px; background: var(--bg-hover); border-radius: 9px; }
.seg-3 { flex: 1; }
.seg-item { padding: 6px 12px; border: none; background: transparent; color: var(--text-dim); border-radius: 6px; cursor: pointer; font-size: 12.5px; transition: all .15s; }
.seg-item.active { background: var(--card); color: var(--brand); font-weight: 700; box-shadow: 0 1px 2px rgba(0,0,0,.05); }
.select { background: var(--bg-hover); color: var(--text); border: 1px solid var(--line); padding: 7px 10px; border-radius: 8px; font-size: 13px; }
.product-list { display: flex; flex-direction: column; gap: 8px; overflow-y: auto; max-height: calc(100vh - 320px); padding-right: 4px; }
.product { display: grid; grid-template-columns: 38px 1fr auto; gap: 10px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px; cursor: pointer; transition: all .14s; position: relative; overflow: hidden; }
.product:hover { border-color: var(--brand); background: var(--bg-hover); }
.product.selected { border-color: var(--brand); background: rgba(14, 165, 233, .07); }
.p-emoji { font-size: 22px; line-height: 38px; text-align: center; }
.p-body { min-width: 0; }
.p-title { font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px; }
.p-tag { font-size: 11px; padding: 1px 6px; background: var(--bg-hover); color: var(--text-faint); border-radius: 4px; font-weight: 600; }
.p-meta { display: flex; gap: 12px; margin-top: 4px; font-size: 12px; color: var(--text-faint); flex-wrap: wrap; }
.p-tags { margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap; }
.tg { font-size: 11px; padding: 1px 6px; background: var(--bg-hover); color: var(--text-dim); border-radius: 999px; }
.p-bar { position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: var(--line); }
.p-bar i { display: block; height: 100%; background: var(--brand); transition: width .4s; }
.p-toggle { padding: 4px 10px; background: var(--brand); color: #fff; border: none; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer; white-space: nowrap; }
.product:not(.selected) .p-toggle { background: transparent; color: var(--brand); border: 1px solid var(--brand); }

.params { display: flex; flex-direction: column; gap: 12px; }
.params h3 { margin: 0 0 6px; font-size: 14.5px; }
.params label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--text-faint); }
.params input { background: var(--bg-hover); border: 1px solid var(--line); color: var(--text); padding: 8px 10px; border-radius: 8px; font-size: 13px; }
.btn { padding: 9px 14px; border: 1px solid var(--line); background: var(--card); color: var(--text); border-radius: 8px; font-size: 13px; cursor: pointer; font-weight: 600; }
.btn-primary { background: var(--brand); color: #fff; border-color: var(--brand); }
.btn-block { width: 100%; }
.btn:hover { background: var(--bg-hover); }
.btn-primary:hover { filter: brightness(1.07); }
.btn:disabled { opacity: .5; cursor: not-allowed; }

.kpi-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 12px 0; }
.kpi { background: var(--bg-hover); padding: 10px 12px; border-radius: 8px; }
.kpi span { display: block; font-size: 11px; color: var(--text-faint); margin-bottom: 4px; }
.kpi b { font-size: 18px; font-weight: 800; color: var(--text); }

.warn-box { background: rgba(245, 158, 11, .1); border-left: 3px solid var(--warn); padding: 9px 12px; border-radius: 6px; margin-bottom: 12px; font-size: 12.5px; }
.warn-box b { color: var(--warn); }
.warn-box ul { margin: 4px 0 0; padding-left: 20px; color: var(--text-dim); }

.day-list { display: flex; flex-direction: column; gap: 12px; max-height: 50vh; overflow-y: auto; }
.day { background: var(--bg-hover); border-radius: 10px; padding: 12px; }
.day-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.day-no { font-weight: 800; color: var(--brand); font-size: 14px; }
.day-count { font-size: 11px; color: var(--text-faint); }
.slots { display: flex; flex-direction: column; gap: 6px; }
.slot { display: grid; grid-template-columns: 60px 1fr auto; gap: 10px; background: var(--card); padding: 8px 10px; border-radius: 7px; align-items: center; }
.slot-time { text-align: center; font-size: 12.5px; font-weight: 700; color: var(--text); }
.slot-time em { font-size: 11px; color: var(--text-faint); font-style: normal; font-weight: 500; }
.slot-body b { font-size: 13px; }
.slot-type { margin-left: 6px; font-size: 11px; color: var(--text-faint); }
.slot-body p { margin: 2px 0 0; font-size: 11.5px; color: var(--text-faint); }
.slot-tag { font-size: 11px; padding: 3px 8px; background: var(--bg-hover); border-radius: 999px; color: var(--text-dim); }

.action-bar { display: flex; gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--line); flex-wrap: wrap; }

.empty-card { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 400px; color: var(--text-faint); text-align: center; }
.empty-illu { font-size: 64px; opacity: .35; }
.empty-card p { margin: 14px 0 0; font-size: 14px; }
.empty-card .sub { font-size: 12px; opacity: .75; }

.cv-selected h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 12px; font-size: 14px; }
.cv-selected ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; max-height: 38vh; overflow-y: auto; }
.sel-row { display: flex; align-items: center; gap: 10px; background: var(--bg-hover); padding: 8px 10px; border-radius: 7px; }
.sel-emoji { font-size: 18px; }
.sel-body b { font-size: 12.5px; display: block; }
.sel-body em { font-size: 11px; color: var(--text-faint); font-style: normal; }
.x { margin-left: auto; width: 22px; height: 22px; border-radius: 50%; background: transparent; border: none; color: var(--text-faint); cursor: pointer; }
.x:hover { background: var(--danger); color: #fff; }

.empty-sel { text-align: center; color: var(--text-faint); padding: 30px 0; font-size: 12.5px; }

.alg-box { margin-top: 16px; padding: 12px; background: rgba(14, 165, 233, .07); border: 1px dashed var(--brand); border-radius: 9px; }
.alg-box h4 { margin: 0 0 8px; font-size: 12.5px; color: var(--brand); }
.alg-box ol { padding-left: 18px; font-size: 11.5px; color: var(--text-dim); line-height: 1.7; margin: 0; }
.alg-box code { background: var(--bg-hover); padding: 1px 5px; border-radius: 3px; font-size: 11px; }
</style>