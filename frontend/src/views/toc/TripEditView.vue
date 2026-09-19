<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { tripById, STOPS, catMeta, CATS } from './mock.js'
import { composerApi } from '../../api/index.js'
import { tripsStore } from '../../stores/trips.js'

const route = useRoute()
const router = useRouter()
const isCreate = computed(() => route.params.id === 'new')

tripsStore.load()
const source = computed(() => tripsStore.byId(route.params.id) || tripById(route.params.id || 't001'))
const title = ref(isCreate.value ? '未命名行程' : source.value.title)
const catList = Object.entries(CATS)

/* 编辑副本:基于行程书深拷贝 */
const days = ref(JSON.parse(JSON.stringify(source.value.dayPlans)))

/* 新增停留点抽屉:标品池走真实接口（GET /api/composer/products），失败回退内置 STOPS */
const showPick = ref(false)
const pickDay = ref(0)
const kw = ref('')
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
const pickList = computed(() =>
  POOL.value.filter(s => !kw.value || s.name.includes(kw.value) || s.cat.includes(kw.value))
)
function openPick(di) { pickDay.value = di; showPick.value = true }
function addStop(s) {
  days.value[pickDay.value].items.push({ stop: s, time: '弹性安排' })
  showPick.value = false
}
function removeItem(di, ii) { days.value[di].items.splice(ii, 1) }
function addDay() {
  days.value.push({ day: days.value.length + 1, title: '自由日', summary: '新的一天,自由安排。', items: [] })
}
function removeDay(di) { if (days.value.length > 1) days.value.splice(di, 1) }

/* 保存:写入本地行程书仓（后端暂无 /api/trips） */
function save() {
  if (isCreate.value || !tripsStore.byId(route.params.id)) {
    const created = tripsStore.save({
      id: route.params.id !== 'new' ? route.params.id : `t_manual_${Date.now().toString(36)}`,
      title: title.value, city: source.value.city || '', days: days.value.length,
      theme: source.value.theme || '', pace: source.value.pace || '', people: source.value.people || 2,
      date: source.value.date || '', budget: source.value.budget || 0,
      stops: days.value.reduce((n, d) => n + d.items.length, 0),
      cats: new Set(days.value.flatMap(d => d.items.map(it => it.stop.cat))).size,
      template: '', delta: '', dayPlans: days.value,
    })
    router.push(`/trip/${created.id}`)
  } else {
    tripsStore.save({ ...tripsStore.byId(route.params.id), title: title.value, days: days.value.length, dayPlans: days.value, stops: days.value.reduce((n, d) => n + d.items.length, 0) })
    router.push(`/trip/${route.params.id}`)
  }
}
function cancel() { router.push(isCreate.value ? '/plans' : `/trip/${route.params.id}`) }

/* 汇总 */
const totalStops = computed(() => days.value.reduce((n, d) => n + d.items.length, 0))
const budget = computed(() => days.value.reduce((n, d) => n + d.items.reduce((m, it) => m + (it.stop.price || 0), 0), 0) * (source.value.people || 2))
</script>

<template>
  <div class="trip-edit">
    <div class="container">

      <header class="te-head">
        <div>
          <RouterLink :to="`/trip/${source.id}`" class="back">← 返回行程书</RouterLink>
          <h1 class="te-title">{{ isCreate ? '新建行程' : '编辑行程' }} · {{ title }}</h1>
          <p class="te-sub">{{ source.city }} · {{ days.length }} 天 · {{ totalStops }} 个停留点 · 预估 ¥{{ budget.toLocaleString() }}/{{ source.people }}人</p>
        </div>
        <div class="te-btns">
          <button class="btn btn-ghost" @click="cancel">取消</button>
          <button class="btn btn-primary" @click="save">保存行程书</button>
        </div>
      </header>

      <div class="te-name card">
        <label>行程名称</label>
        <input v-model="title" placeholder="给这次旅行起个名字" />
      </div>

      <section v-for="(d, di) in days" :key="di" class="day-edit card">
        <div class="de-head">
          <span class="de-day">D{{ d.day }}</span>
          <input v-model="d.title" class="de-title" placeholder="当日主题" />
          <input v-model="d.summary" class="de-summary" placeholder="一句话摘要" />
          <div class="de-ops">
            <button class="op" title="删除当日" @click="removeDay(di)">🗑</button>
          </div>
        </div>

        <div v-for="(it, ii) in d.items" :key="it.stop.id + ii" class="de-row">
          <i class="de-dot" :style="{ background: catMeta(it.stop.cat).color }"></i>
          <span class="de-emoji">{{ catMeta(it.stop.cat).emoji }}</span>
          <b class="de-name">{{ it.stop.name }}</b>
          <input v-model="it.time" class="de-time" />
          <span class="de-meta">{{ it.stop.dwell }} · {{ it.stop.price ? '¥' + it.stop.price : '免费' }}</span>
          <button class="op" @click="removeItem(di, ii)">✕</button>
        </div>

        <button class="de-add" @click="openPick(di)">＋ 从标品库添加停留点</button>
      </section>

      <button class="add-day" @click="addDay">＋ 增加一天</button>
    </div>

    <!-- 选品抽屉 -->
    <div v-if="showPick" class="drawer-mask" @click.self="showPick = false">
      <div class="drawer card">
        <div class="dw-head">
          <b>为 D{{ pickDay + 1 }} 添加停留点</b>
          <button class="op" @click="showPick = false">✕</button>
        </div>
        <input v-model="kw" class="dw-search" placeholder="搜索标品:名称 / 品类" />
        <div class="dw-list">
          <button v-for="s in pickList" :key="s.id" class="dw-item" @click="addStop(s)">
            <span class="de-emoji">{{ catMeta(s.cat).emoji }}</span>
            <div class="dw-info">
              <b>{{ s.name }}</b>
              <span>{{ s.city }} · {{ s.dwell }} · {{ s.price ? '¥' + s.price : '免费' }}</span>
            </div>
            <span class="dw-cat" :style="{ color: catMeta(s.cat).color, background: catMeta(s.cat).soft }">{{ s.cat }}</span>
          </button>
          <p v-if="!pickList.length" class="dw-empty">未命中标品,可联系管家定制。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trip-edit { padding: var(--s-7) 0 var(--s-9); }
.container { display: flex; flex-direction: column; gap: var(--s-4); }
.te-head { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--s-4); flex-wrap: wrap; }
.back { font-size: var(--fs-xs); color: var(--text-3); }
.back:hover { color: var(--text); }
.te-title { font-size: var(--fs-2xl); font-weight: var(--fw-bold); margin-top: var(--s-2); letter-spacing: -0.015em; }
.te-sub { margin-top: var(--s-2); font-size: var(--fs-sm); color: var(--text-3); }
.te-btns { display: flex; gap: var(--s-2); }

.te-name { display: flex; align-items: center; gap: var(--s-4); padding: var(--s-4) var(--s-5); }
.te-name label { font-size: var(--fs-sm); color: var(--text-3); flex: none; }
.te-name input { border: none; background: transparent; font-size: var(--fs-md); font-weight: var(--fw-medium); flex: 1; outline: none; }

.day-edit { padding: var(--s-5); }
.de-head { display: flex; align-items: center; gap: var(--s-3); margin-bottom: var(--s-3); }
.de-day { font-weight: var(--fw-bold); color: var(--accent); flex: none; }
.de-title { width: 160px; font-size: var(--fs-sm); font-weight: var(--fw-bold); border: none; border-bottom: 1px dashed var(--border); background: transparent; padding: 4px 0; outline: none; }
.de-summary { flex: 1; font-size: var(--fs-xs); color: var(--text-3); border: none; border-bottom: 1px dashed var(--border); background: transparent; padding: 4px 0; outline: none; }
.de-ops { margin-left: auto; }
.op { border: none; background: none; cursor: pointer; color: var(--text-faint); font-size: var(--fs-sm); padding: 2px 6px; border-radius: var(--r-sm); }
.op:hover { background: var(--surface-2); color: var(--danger, #B0685C); }

.de-row { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) var(--s-3); border-radius: var(--r-sm); }
.de-row:hover { background: var(--surface-2); }
.de-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.de-emoji { flex: none; }
.de-name { font-size: var(--fs-sm); flex: none; }
.de-time { width: 130px; font-size: var(--fs-xs); color: var(--accent); border: 1px solid var(--border-soft); border-radius: var(--r-sm); padding: 3px var(--s-2); background: var(--surface); outline: none; font-variant-numeric: tabular-nums; }
.de-meta { font-size: var(--fs-xs); color: var(--text-faint); margin-left: auto; }
.de-row .op { margin-left: var(--s-2); }

.de-add { margin-top: var(--s-3); width: 100%; padding: var(--s-3); border: 1px dashed var(--border); border-radius: var(--r); background: transparent; color: var(--text-3); font-size: var(--fs-sm); cursor: pointer; transition: all var(--dur-1) var(--ease); }
.de-add:hover { border-color: var(--accent); color: var(--accent); }

.add-day { padding: var(--s-3); border: 1px dashed var(--border); border-radius: var(--r); background: transparent; color: var(--text-3); font-size: var(--fs-sm); cursor: pointer; }
.add-day:hover { border-color: var(--accent); color: var(--accent); }

/* 抽屉 */
.drawer-mask { position: fixed; inset: 0; background: rgba(46,44,40,.35); display: flex; justify-content: flex-end; z-index: 90; }
.drawer { width: min(420px, 92vw); height: 100%; border-radius: 0; display: flex; flex-direction: column; padding: 0; overflow: hidden; }
.dw-head { display: flex; justify-content: space-between; align-items: center; padding: var(--s-4) var(--s-5); border-bottom: 1px solid var(--border-soft); }
.dw-head b { font-size: var(--fs-md); }
.dw-search { margin: var(--s-4) var(--s-5) var(--s-2); }
.dw-list { flex: 1; overflow-y: auto; padding: var(--s-2) var(--s-5) var(--s-5); display: flex; flex-direction: column; gap: var(--s-2); }
.dw-item { display: flex; align-items: center; gap: var(--s-3); text-align: left; padding: var(--s-3) var(--s-4); border: 1px solid var(--border-soft); border-radius: var(--r); background: var(--surface); cursor: pointer; transition: all var(--dur-1) var(--ease); }
.dw-item:hover { border-color: var(--accent); box-shadow: var(--shadow-xs); }
.dw-info b { font-size: var(--fs-sm); display: block; }
.dw-info span { font-size: var(--fs-xs); color: var(--text-faint); }
.dw-cat { margin-left: auto; font-size: var(--fs-xs); font-weight: var(--fw-bold); padding: 2px 10px; border-radius: var(--r-pill); flex: none; }
.dw-empty { text-align: center; font-size: var(--fs-sm); color: var(--text-faint); padding: var(--s-6) 0; }
</style>
