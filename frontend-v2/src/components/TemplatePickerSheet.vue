<template>
  <AppDrawer :title="title" @close="$emit('close')">
    <!-- 种子商品提示（商城/详情页用模板排行程的深链场景） -->
    <div v-if="seedProduct" class="seed-bar">
      <span>🛒 已预置商品</span>
      <b>{{ seedProduct.cover?.emoji }} {{ seedProduct.name }}</b>
      <small>（{{ seedProduct.category }} · {{ seedProduct.city }}）将自动编入所选模板第一天对应时段</small>
    </div>

    <!-- 城市筛选 -->
    <div class="filter-row">
      <div class="city-tabs">
        <button v-for="c in cityTabs" :key="c.key" class="chip" :class="{ active: cityFilter === c.key }"
                @click="cityFilter = c.key">{{ c.label }}<span v-if="c.key !== 'all'"> · {{ c.n }}</span></button>
      </div>
      <router-link :to="{ name: 'malls' }" class="link-more" target="_blank">没有合适的？去标品商城逛逛 →</router-link>
    </div>

    <!-- 状态 -->
    <div v-if="loading" class="loading-block"><div class="spinner spin"></div>模板加载中…</div>
    <div v-else-if="!tplList.length" class="empty card"><div class="icon">🧩</div><p>暂无匹配的行程模板</p></div>

    <!-- 模板网格 -->
    <div v-else class="tpl-grid">
      <div v-for="t in tplList" :key="t.id" class="tpl-card card" :class="{ picked: chosenId === t.id }"
           @click="onPick(t)">
        <div class="tpl-cover" :style="{ background: t.cover.gradient }">
          <span class="tpl-emoji">{{ t.cover.emoji }}</span>
          <div class="tpl-days">{{ t.days }} 天{{ t.days > 1 ? '·' + (t.days - 1) + ' 晚' : '' }}</div>
          <span v-for="b in t.badges" :key="b" class="bd">{{ b }}</span>
        </div>
        <div class="tpl-body">
          <div class="tpl-theme">{{ t.city }} · {{ t.theme }}</div>
          <div class="tpl-title">{{ t.title }}</div>
          <div class="tpl-meta">
            <span>{{ paceLabel(t.pace) }}</span><span>·</span><span>{{ t.audience }}</span><span>·</span><span>{{ t.season }}出行</span>
          </div>
          <div class="tpl-foot">
            <div class="tpl-price"><span class="y">¥</span><b>{{ t.price_total }}</b><span class="per">/人 起</span></div>
            <button class="btn btn-primary btn-sm">✦ 以此编排</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部说明 -->
    <div class="tips">
      <div class="tip"><b>为什么要从模板开始？</b><p>每一套模板都是 toB 行程组装器按「节奏 × 地理 × 时段」拼好的底稿，你只需微调，不用从零排行程。</p></div>
      <div class="tip"><b>模板里的每个标品都能换</b><p>进入编排后，任意时段都能在同城标品库中替换 / 增补，价格与评分实时对比。</p></div>
    </div>

    <template #foot>
      <button class="btn btn-ghost" @click="$emit('close')">取消</button>
    </template>
  </AppDrawer>
</template>

<script setup>
// 模板选择抽屉（W2：抽自 PlannerView，承载"选模板"单一职责）
// ---------------------------------------------------------------------------
// 父组件使用方式：
//   <TemplatePickerSheet
//     v-if="showPicker"
//     :seed="seedProduct"
//     @picked="onPicked"
//     @close="showPicker = false"
//   />
// 父组件 onPicked(template) 后负责跳 /trip/:id/edit?template=...&seed=...
// ---------------------------------------------------------------------------
import { ref, computed, onMounted } from 'vue'
import { routeTemplatesApi } from '../api'
import { toast } from '../composables/toast'
import AppDrawer from './AppDrawer.vue'

const props = defineProps({
  title: { type: String, default: '✦ 选一个标品行程模板' },
  seed: { type: Object, default: null },
})
const emit = defineEmits(['picked', 'close'])

const loading = ref(true)
const templates = ref([])
const cityFilter = ref('all')
const chosenId = ref('')

const tplList = computed(() => {
  if (cityFilter.value === 'all') return templates.value
  return templates.value.filter(t => t.city === cityFilter.value)
})
const cityTabs = computed(() => {
  const counter = {}
  for (const t of templates.value) counter[t.city] = (counter[t.city] || 0) + 1
  const tabs = [{ key: 'all', label: '全部' }]
  for (const c of Object.keys(counter)) tabs.push({ key: c, label: c, n: counter[c] })
  return tabs
})

// seed 在 props 变化时不主动响应（抽屉通常开关一次就结束）；保留访问
const seedProduct = computed(() => props.seed)

onMounted(async () => {
  loading.value = true
  try {
    const r = await routeTemplatesApi.list()
    templates.value = r.items || []
    if (!templates.value.length) toast('暂无可编排的行程模板', 'err')
  } catch (e) {
    toast('加载失败：' + (e.message || e), 'err')
  } finally {
    loading.value = false
  }
})

function onPick(t) {
  chosenId.value = t.id
  emit('picked', t)
}
function paceLabel(p) { return ({ relaxed: '🛋 悠闲', standard: '⚖ 标准', tight: '⚡ 紧凑' })[p] || p }
</script>

<style scoped>
/* 抽屉内：模板选择 UI（原 PlannerView step1 风格） */
.seed-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 12px 18px; border-radius: var(--r-lg); background: var(--accent-50, #FFF7ED); border: 1px solid #FDBA74; font-size: 13.5px; color: var(--ink-700); margin-bottom: 16px; }
.seed-bar b { color: var(--ink-900); }
.seed-bar small { color: var(--ink-500); flex: 1; min-width: 200px; }

.filter-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
.city-tabs { display: flex; gap: 8px; }
.chip { padding: 7px 16px; border-radius: 999px; border: 1px solid var(--ink-200); background: #fff; color: var(--ink-600); font-size: 13px; cursor: pointer; transition: all .15s; }
.chip.active { background: var(--brand-600); color: #fff; border-color: var(--brand-600); font-weight: 700; }
.link-more { font-size: 13px; color: var(--brand-600); font-weight: 600; }

.tpl-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.tpl-card { padding: 0; overflow: hidden; cursor: pointer; border: 2px solid transparent; display: grid; grid-template-columns: 210px 1fr; min-height: 210px; }
.tpl-card.picked { border-color: var(--brand-500); box-shadow: 0 0 0 3px rgba(59,130,246,.15), var(--shadow-md); }
.tpl-cover { position: relative; display: flex; align-items: center; justify-content: center; }
.tpl-emoji { font-size: 84px; filter: drop-shadow(0 6px 10px rgba(0,0,0,.18)); }
.tpl-days { position: absolute; top: 12px; left: 12px; background: rgba(0,0,0,.5); color: #fff; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; backdrop-filter: blur(6px); }
.tpl-cover .bd { position: absolute; bottom: 10px; left: 10px; background: rgba(0,0,0,.42); color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 4px; backdrop-filter: blur(6px); }
.tpl-body { padding: 18px 18px 16px; display: flex; flex-direction: column; min-width: 0; }
.tpl-theme { font-size: 12px; font-weight: 700; color: var(--brand-600); margin-bottom: 4px; }
.tpl-title { font-size: 18px; font-weight: 800; color: var(--ink-900); line-height: 1.4; margin-bottom: 6px; }
.tpl-meta { display: flex; gap: 5px; font-size: 12px; color: var(--ink-500); flex-wrap: wrap; margin-bottom: 8px; }
.tpl-foot { margin-top: auto; display: flex; justify-content: space-between; align-items: center; }
.tpl-price { display: flex; align-items: baseline; gap: 3px; }
.tpl-price .y { font-size: 13px; color: var(--danger); font-weight: 700; }
.tpl-price b { font-size: 24px; color: var(--danger); font-weight: 900; }
.tpl-price .per { font-size: 11px; color: var(--ink-400); }

.tips { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-top: 22px; padding-top: 16px; border-top: 1px dashed var(--ink-200); }
.tip { padding: 14px 16px; background: var(--ink-50); border-radius: var(--r-lg); border: 1px solid var(--ink-100); }
.tip b { font-size: 13.5px; color: var(--ink-900); }
.tip p { font-size: 12.5px; color: var(--ink-500); margin: 6px 0 0; line-height: 1.7; }

.loading-block { padding: 60px 0; text-align: center; color: var(--ink-400); }
.empty { padding: 60px 20px; text-align: center; }
.empty .icon { font-size: 48px; }

@media (max-width: 960px) {
  .tpl-grid { grid-template-columns: 1fr; }
  .tpl-card { grid-template-columns: 150px 1fr; }
  .tips { grid-template-columns: 1fr; }
}
</style>
