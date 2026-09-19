# -*- coding: utf-8 -*-
"""方案馆真实分页 + 动线图接入真实地图（跑完即删）"""
import io

# ========== 1. MallsView 分页 ==========
p = 'views/MallsView.vue'
s = io.open(p, encoding='utf-8').read()

def rep(old, new, tag):
    global s
    assert old in s, f'Malls NOT FOUND: {tag}'
    s = s.replace(old, new, 1)

# 分页状态
rep("""const sorters = ['推荐排序', '价格 低到高', '价格 高到低', '最新上架']""" if "const sorters" in s else """const sorts = ['推荐排序', '价格 低到高', '价格 高到低', '最新上架']""",
    """const sorts = ['推荐排序', '价格 低到高', '价格 高到低', '最新上架']

// 真实分页
const currentPage = ref(1)
const pageSize = 9
const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))
const pagedPlans = computed(() => filtered.value.slice((currentPage.value - 1) * pageSize, currentPage.value * pageSize))
function goToPage(n) {
  if (n < 1 || n > totalPages.value) return
  currentPage.value = n
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function prevPage() { goToPage(currentPage.value - 1) }
function nextPage() { goToPage(currentPage.value + 1) }""", 'pagination state')

# filtered 变化时重置页码
rep("""const filtered = computed(() => {""",
    """const filtered = computed(() => {
  currentPage.value = 1""", 'reset page')

# 模板：方案卡 v-for 改用 pagedPlans
rep("""        <article v-for="(p, i) in filtered" :key="p.title" class="plan card card-hover anim-fade-up" :class="`delay-${(i%4)+1}`">""",
    """        <article v-for="(p, i) in pagedPlans" :key="p.title" class="plan card card-hover anim-fade-up" :class="`delay-${(i%4)+1}`">""", 'v-for')

# 分页导航接线
old = """      <!-- 分页 -->
      <nav class="pager mt-7">
        <button class="btn btn-ghost btn-sm" disabled>
          <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m15 6-6 6 6 6"/></svg> 上一页
        </button>
        <div class="page-num">
          <button class="page-btn active">1</button>"""
new = """      <!-- 分页 -->
      <nav v-if="totalPages > 1" class="pager mt-7">
        <button class="btn btn-ghost btn-sm" :disabled="currentPage <= 1" @click="prevPage">
          <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m15 6-6 6 6 6"/></svg> 上一页
        </button>
        <div class="page-num">
          <button v-for="n in totalPages" :key="n" class="page-btn" :class="{ active: n === currentPage }" @click="goToPage(n)">{{ n }}</button>"""
if old in s:
    s = s.replace(old, new, 1)
else:
    # 分页 HTML 可能不同，直接搜索 pager 区域
    import re
    m2 = re.search(r'(<nav class="pager[^"]*">)[\s\S]*?(</nav>)', s)
    if m2:
        pager_new = m2.group(1) + '''
        <button class="btn btn-ghost btn-sm" :disabled="currentPage <= 1" @click="prevPage">← 上一页</button>
        <span class="page-indicator">{{ currentPage }} / {{ totalPages }}</span>
        <button class="btn btn-ghost btn-sm" :disabled="currentPage >= totalPages" @click="nextPage">下一页 →</button>
        ''' + m2.group(2)
        s = s[:m2.index] + pager_new + s[m2.index + len(m2.group(0)):]
        print('pager replaced via regex')
    else:
        print('WARN: pager not found, skipping pager patch')

# 下一页按钮
if '下一页 →' not in s:
    s = s.replace('全部方案 →', '全部方案 →')  # placeholder
# 下一页可能在 pager 后面
old2 = """        <button class="btn btn-ghost btn-sm" disabled>
          <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/></svg> 下一页
        </button>"""
if old2 in s:
    s = s.replace(old2, """        <button class="btn btn-ghost btn-sm" :disabled="currentPage >= totalPages" @click="nextPage">
          下一页 <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/></svg>
        </button>""", 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('MallsView OK')

# ========== 2. TripMapView 替换为真实地图 ==========
p = 'views/toc/TripMapView.vue'
s = io.open(p, encoding='utf-8').read()

# 导入 RealMapView
rep("""import { tripsStore } from '../../stores/trips.js'""",
    """import { tripsStore } from '../../stores/trips.js'
import RealMapView from '../../components/RealMapView.vue'""", 'import RealMap')

# 替换 ECharts 地图容器为真实地图
rep("""      <div v-if="view === 'map'" ref="chartEl" class="map-box"></div>""",
    """      <RealMapView v-if="view === 'map'" :spots="locatable" height="480px" />""", 'map container')

io.open(p, 'w', encoding='utf-8').write(s)
print('TripMapView OK')

# ========== 3. PlanDetailView 地图 tab 替换 ==========
p = 'views/toc/PlanDetailView.vue'
s = io.open(p, encoding='utf-8').read()

rep("""import { plansApi, expApi, ragApi, assistApi, planShopApi } from '../../api/index.js'""",
    """import { plansApi, expApi, ragApi, assistApi, planShopApi } from '../../api/index.js'
import RealMapView from '../../components/RealMapView.vue'""", 'import RealMap')

# 替换地图容器（找到 ref="mapEl" 的 div）
if 'ref="mapEl"' in s:
    old = """      <!-- ⑥ 每日动线 -->
      <section v-else-if="tab === 'map'" class="card tab-card">
        <div ref="mapEl" class="agent-map"></div>"""
    if old in s:
        s = s.replace(old, """      <!-- ⑥ 每日动线 -->
      <section v-else-if="tab === 'map'" class="card tab-card">
        <RealMapView :spots="mapSpots" height="440px" />""", 1)
        # 添加 mapSpots computed
        if 'mapSpots' not in s:
            old2 = """const mapSpots = ref([])"""
            if old2 not in s:
                # 在 trip 定义后添加 mapSpots computed
                anchor = 'const trip = ref(tripById'
                if anchor in s:
                    # trip 是 ref，找到 trip 定义后加
                    s = s.replace(anchor, anchor, 1)  # placeholder
                # 在 renderAgentMap 之前加 computed
                old3 = """function renderAgentMap() {"""
                if old3 in s:
                    s = s.replace(old3, """const mapSpots = computed(() => {
  const out = []
  trip.value.dayPlans.forEach((d, di) => {
    d.items.forEach((it, ii) => {
      if (it.stop.x != null) out.push({ name: it.stop.name, lat: it.stop.y, lng: it.stop.x, day: di + 1, cat: it.stop.cat })
    })
  })
  return out
})
function renderAgentMap() {""", 1)
    else:
        # 已经替换了
        pass
io.open(p, 'w', encoding='utf-8').write(s)
print('PlanDetailView OK')
