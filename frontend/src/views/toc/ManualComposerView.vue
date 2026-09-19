<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { STOPS, catMeta, CATS } from './mock.js'
import { composerApi } from '../../api/index.js'
import { tripsStore, composeToTrip } from '../../stores/trips.js'

const router = useRouter()
const catList = Object.entries(CATS)

/* —— 左栏:选品（GET /api/composer/products 真实标品库，失败回退内置 STOPS） —— */
const kw = ref('')
const activeCat = ref('全部')
const picked = ref([])
const POOL = ref(STOPS)
onMounted(async () => {
  try {
    const res = await composerApi.listProducts({})
    const rows = (res && res.products) || []
    if (rows.length) {
      POOL.value = rows.map(p => ({
        id: p.id, name: p.name, cat: p.category || '景点', city: p.city || '',
        price: p.price_min ?? 0, dwell: p.typical_dwell || '', rating: p.rating || undefined,
        x: Array.isArray(p.coords) ? p.coords[0] : (p.coords && p.coords.lng) ?? null,
        y: Array.isArray(p.coords) ? p.coords[1] : (p.coords && p.coords.lat) ?? null,
        note: p.description || (p.tags || []).join(' / '),
      }))
    }
  } catch { /* 回退内置标品 */ }
})

const pool = computed(() =>
  POOL.value.filter(s =>
    (activeCat.value === '全部' || s.cat === activeCat.value) &&
    (!kw.value || s.name.includes(kw.value) || (s.note || '').includes(kw.value))
  )
)
const pickedSet = computed(() => new Set(picked.value))
function toggle(id) {
  const i = picked.value.indexOf(id)
  i >= 0 ? picked.value.splice(i, 1) : picked.value.push(id)
}
const pickedStops = computed(() => picked.value.map(id => POOL.value.find(s => s.id === id)).filter(Boolean))

/* —— 右栏:参数 —— */
const name = ref('我的苏州行程')
const date = ref('2026-10-02')
const people = ref(2)
const pace = ref('standard')
const PACES = [
  { key: 'relaxed',  label: '松弛', per: 3, hint: '每天约 3 段' },
  { key: 'standard', label: '标准', per: 4, hint: '每天约 4 段' },
  { key: 'tight',    label: '紧凑', per: 5, hint: '每天约 5 段' },
]
const paceMeta = computed(() => PACES.find(p => p.key === pace.value))

/* —— 生成：POST /api/composer/from-products（确定性排程 + RAG 知识背书），失败回退本地拼排 —— */
const generated = ref(false)
const result = ref(null)
const composing = ref(false)
const composeErr = ref('')
async function generate() {
  if (composing.value) return
  composing.value = true
  composeErr.value = ''
  const segs = pickedStops.value
  const perDay = paceMeta.value.per
  const dayCount = Math.max(1, Math.ceil(segs.length / perDay))
  try {
    const res = await composerApi.compose({
      product_ids: picked.value,
      days: Math.min(7, dayCount),
      pace: pace.value,
      anchor: { city: name.value ? '' : '' },
    })
    const trip = composeToTrip(res, { name: name.value, city: (segs[0] && segs[0].city) || '', people: people.value, date: date.value, pace: pace.value })
    if (trip) {
      result.value = {
        dayCount: trip.days,
        ticket: 0,
        stay: 0,
        total: trip.budget || 0,
        coverage: Math.min(100, Math.round(segs.length / (trip.days * perDay) * 100)),
        warnings: [...(res.warnings || [])],
        days: trip.dayPlans.map(d => ({ day: d.day, items: d.items.map(it => ({ ...it.stop, time: it.time })) })),
        trip,
      }
      generated.value = true
      return
    }
    composeErr.value = '组装结果为空,已用本地排程兜底'
  } catch { composeErr.value = '' }
  // 本地兜底拼排（接口不可用时保持可用）
  const ticket = segs.reduce((n, s) => n + (s.cat === '景点' || s.cat === '文化' || s.cat === '体验' ? s.price : 0), 0)
  const stay = segs.filter(s => s.cat === '住宿').reduce((n, s) => n + s.price, 0) * dayCount
  const warnings = []
  if (composeErr.value) warnings.push('组装服务暂不可用,已按本地规则排程')
  if (!segs.some(s => s.cat === '餐饮')) warnings.push('未选择任何餐饮,行程可能缺少用餐安排')
  if (!segs.some(s => s.cat === '住宿') && dayCount > 1) warnings.push('多日行程未包含住宿')
  if (segs.length > dayCount * perDay) warnings.push(`停留点超出 ${dayCount} 天 × ${perDay} 段容量,请放宽天数或减少点位`)
  result.value = {
    dayCount, ticket, stay,
    total: ticket + stay,
    coverage: Math.min(100, Math.round(segs.length / (dayCount * perDay) * 100)),
    warnings,
    days: Array.from({ length: dayCount }, (_, i) => ({
      day: i + 1,
      items: segs.slice(i * perDay, (i + 1) * perDay),
    })),
  }
  generated.value = true
}

/* 保存为行程书:写入本地行程书仓 */
function saveTrip() {
  if (result.value && result.value.trip) {
    const saved = tripsStore.save(result.value.trip)
    router.push(`/trip/${saved.id}`)
  } else if (result.value) {
    const saved = tripsStore.save({
      id: `t_manual_${Date.now().toString(36)}`,
      title: name.value || '我的手动行程',
      city: (pickedStops.value[0] && pickedStops.value[0].city) || '',
      days: result.value.dayCount, theme: '', pace: paceMeta.value.label, people: people.value,
      date: date.value, budget: result.value.total,
      stops: pickedStops.value.length, cats: new Set(pickedStops.value.map(s => s.cat)).size,
      template: '手动组装', delta: '',
      dayPlans: result.value.days.map(d => ({ day: d.day, title: `第 ${d.day} 天`, summary: '', items: d.items.map(it => ({ stop: it, time: '弹性安排' })) })),
    })
    router.push(`/trip/${saved.id}`)
  }
}
</script>

<template>
  <div class="composer">
    <div class="container">

      <header class="mc-head">
        <div>
          <h1 class="mc-title">手动组装行程</h1>
          <p class="mc-sub">从标品库自由挑选积木,设好节奏与人数,系统自动编排逐日框架并测算预算。</p>
        </div>
        <RouterLink to="/plans" class="btn btn-ghost btn-sm">我的行程</RouterLink>
      </header>

      <div class="mc-grid">
        <!-- 左:选品 -->
        <section class="card mc-left">
          <div class="mc-search">
            <span class="s-ico">⌕</span>
            <input v-model="kw" placeholder="语义搜索:例如「适合带孩子的园林」" />
          </div>
          <div class="mc-cats">
            <button class="chip chip-sm" :class="{ active: activeCat === '全部' }" @click="activeCat = '全部'">全部</button>
            <button v-for="[k, m] in catList" :key="k" class="chip chip-sm" :class="{ active: activeCat === k }" @click="activeCat = k">
              {{ m.emoji }} {{ k }}
            </button>
          </div>
          <div class="mc-pool">
            <button v-for="s in pool" :key="s.id" class="pick" :class="{ on: pickedSet.has(s.id) }" @click="toggle(s.id)">
              <span class="pk-emoji">{{ catMeta(s.cat).emoji }}</span>
              <div class="pk-info">
                <b>{{ s.name }}</b>
                <span>{{ s.city }} · {{ s.dwell }} · {{ s.price ? '¥' + s.price : '免费' }}</span>
              </div>
              <span class="pk-btn">{{ pickedSet.has(s.id) ? '✓ 已选' : '＋' }}</span>
            </button>
            <p v-if="!pool.length" class="pool-empty">没有命中的标品,换个关键词试试。</p>
          </div>
        </section>

        <!-- 右:参数 -->
        <section class="card mc-right">
          <h4 class="mr-title">行程参数</h4>

          <label class="field">
            <span>行程名称</span>
            <input v-model="name" placeholder="给行程起个名字" />
          </label>
          <div class="f-row">
            <label class="field">
              <span>出发日期</span>
              <input v-model="date" type="date" />
            </label>
            <label class="field">
              <span>人数</span>
              <input v-model.number="people" type="number" min="1" max="20" />
            </label>
          </div>

          <div class="field">
            <span>节奏</span>
            <div class="pace-opts">
              <button v-for="p in PACES" :key="p.key" :class="{ on: pace === p.key }" @click="pace = p.key">
                <b>{{ p.label }}</b><i>{{ p.hint }}</i>
              </button>
            </div>
          </div>

          <div class="picked-brief">
            <b>已选 {{ pickedStops.length }} 件标品</b>
            <div class="pb-chips">
              <span v-for="s in pickedStops" :key="s.id" class="pb-chip" :style="{ background: catMeta(s.cat).soft, color: catMeta(s.cat).color }">
                {{ catMeta(s.cat).emoji }} {{ s.name }}
              </span>
              <span v-if="!pickedStops.length" class="pb-empty">还没选择,从左侧挑选积木 →</span>
            </div>
          </div>

          <button class="btn btn-primary gen-btn" :disabled="!pickedStops.length" @click="generate">
            ⚙ 生成逐日框架
          </button>

          <!-- 结果 -->
          <div v-if="generated && result" class="gen-result">
            <div class="gr-kpis">
              <div class="gr-kpi"><b>{{ result.coverage }}%</b><span>框架覆盖</span></div>
              <div class="gr-kpi"><b>¥{{ result.ticket.toLocaleString() }}</b><span>预估门票体验</span></div>
              <div class="gr-kpi"><b>¥{{ result.total.toLocaleString() }}</b><span>总预算 / {{ people }}人</span></div>
            </div>
            <div v-for="w in result.warnings" :key="w" class="gr-warn">⚠ {{ w }}</div>
            <div class="gr-days">
              <div v-for="d in result.days" :key="d.day" class="gr-day">
                <span class="grd-no">D{{ d.day }}</span>
                <span v-for="it in d.items" :key="it.id" class="grd-chip" :style="{ background: catMeta(it.cat).soft, color: catMeta(it.cat).color }">
                  {{ catMeta(it.cat).emoji }} {{ it.name }}
                </span>
              </div>
            </div>
            <div class="gr-actions">
              <button class="btn btn-ghost btn-sm" @click="generated = false">调整</button>
              <button class="btn btn-primary btn-sm" @click="saveTrip">保存为行程书 →</button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.composer { padding: var(--s-7) 0 var(--s-9); }
.mc-head { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--s-4); flex-wrap: wrap; margin-bottom: var(--s-5); }
.mc-title { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; }
.mc-sub { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-3); }

.mc-grid { display: grid; grid-template-columns: 1.25fr 1fr; gap: var(--s-5); align-items: start; }
.mc-left { padding: var(--s-5); }
.mc-search { display: flex; align-items: center; gap: var(--s-2); border: 1px solid var(--border); border-radius: var(--r); padding: 0 var(--s-3); background: var(--surface-2); }
.s-ico { color: var(--text-faint); }
.mc-search input { border: none; background: transparent; padding: 10px 0; flex: 1; outline: none; font-size: var(--fs-sm); }
.mc-cats { display: flex; gap: var(--s-2); flex-wrap: wrap; margin: var(--s-3) 0; }
.mc-pool { display: flex; flex-direction: column; gap: var(--s-2); max-height: 520px; overflow-y: auto; }
.pick { display: flex; align-items: center; gap: var(--s-3); text-align: left; padding: var(--s-3) var(--s-4); border: 1px solid var(--border-soft); border-radius: var(--r); background: var(--surface); cursor: pointer; transition: all var(--dur-1) var(--ease); }
.pick.on { border-color: var(--accent); background: #F4F6F1; }
.pk-emoji { font-size: 18px; flex: none; }
.pk-info b { font-size: var(--fs-sm); display: block; }
.pk-info span { font-size: var(--fs-xs); color: var(--text-faint); }
.pk-btn { margin-left: auto; flex: none; font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--accent); border: 1px solid var(--border); border-radius: var(--r-pill); padding: 3px 10px; }
.pick.on .pk-btn { background: var(--accent); color: #fff; border-color: var(--accent); }
.pool-empty { text-align: center; color: var(--text-faint); font-size: var(--fs-sm); padding: var(--s-6) 0; }

.mc-right { padding: var(--s-5) var(--s-6); }
.mr-title { font-size: var(--fs-md); margin-bottom: var(--s-4); }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: var(--s-4); }
.field > span { font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--text-2); }
.f-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
.pace-opts { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-2); }
.pace-opts button { border: 1px solid var(--border); background: var(--surface); border-radius: var(--r); padding: var(--s-2) var(--s-3); text-align: center; cursor: pointer; transition: all var(--dur-1) var(--ease); }
.pace-opts button b { display: block; font-size: var(--fs-sm); }
.pace-opts button i { font-style: normal; font-size: 10px; color: var(--text-faint); }
.pace-opts button.on { border-color: var(--accent); background: #F4F6F1; }

.picked-brief { border-top: 1px solid var(--border-soft); padding-top: var(--s-4); margin-bottom: var(--s-4); }
.picked-brief b { font-size: var(--fs-sm); }
.pb-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-top: var(--s-2); }
.pb-chip { font-size: var(--fs-xs); font-weight: var(--fw-medium); padding: 3px 10px; border-radius: var(--r-pill); }
.pb-empty { font-size: var(--fs-xs); color: var(--text-faint); }

.gen-btn { width: 100%; }
.gen-btn:disabled { opacity: .45; cursor: not-allowed; }

.gen-result { margin-top: var(--s-5); border-top: 1px solid var(--border-soft); padding-top: var(--s-4); }
.gr-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-3); }
.gr-kpi { background: var(--surface-2); border-radius: var(--r); padding: var(--s-3); text-align: center; }
.gr-kpi b { font-size: var(--fs-md); color: var(--accent); display: block; }
.gr-kpi span { font-size: 10px; color: var(--text-faint); }
.gr-warn { margin-top: var(--s-3); font-size: var(--fs-xs); color: #9A7B54; background: #F5EFE7; border-radius: var(--r-sm); padding: var(--s-2) var(--s-3); }
.gr-days { margin-top: var(--s-4); display: flex; flex-direction: column; gap: var(--s-2); }
.gr-day { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.grd-no { font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--accent); flex: none; width: 28px; }
.grd-chip { font-size: var(--fs-xs); padding: 3px 10px; border-radius: var(--r-pill); font-weight: var(--fw-medium); }
.gr-actions { display: flex; justify-content: flex-end; gap: var(--s-2); margin-top: var(--s-4); }

@media (max-width: 900px) { .mc-grid { grid-template-columns: 1fr; } }
</style>
