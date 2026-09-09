<template>
  <div class="home">
    <!-- Hero：把"标品"翻译成游客听得懂的话 -->
    <section class="hero">
      <div class="container hero-inner">
        <div class="hero-left">
          <span class="hero-tag">🚩 线路方案整订 · 一价全包 · 不用自己凑门票</span>
          <h1 class="hero-title">
            企业排好的行程，<br />
            <span class="grad">你只管选一条，直接出发。</span>
          </h1>
          <p class="hero-sub">
            每一份「线路方案」都由目的地文旅把门票、餐饮、住宿按天排好动线、打包报价。
            你选方案 → 选出行日与人数 → 整单下单，不再一张张买门票和车票。
          </p>
          <div class="search-bar card">
            <span class="s-icon">🔍</span>
            <input v-model="kw" class="s-input" placeholder="搜索城市 / 主题 / 线路，例如：苏州、园林、亲子" @keydown.enter="goSearch" />
            <button class="btn btn-primary" @click="goSearch">找方案</button>
          </div>
          <div class="hot-search">
            <span>热门：</span>
            <button v-for="q in HOT_KW" :key="q" class="hs-chip" @click="kw = q; goSearch()">{{ q }}</button>
          </div>
        </div>
        <div class="hero-right">
          <div class="hero-stat">
            <div class="st-num">4</div>
            <div class="st-label">已上线路方案</div>
          </div>
          <div class="hero-stat">
            <div class="st-num">6</div>
            <div class="st-label">素材覆盖分类</div>
          </div>
          <div class="hero-stat">
            <div class="st-num">整订</div>
            <div class="st-label">一价含门票食宿</div>
          </div>
          <div class="hero-stat">
            <div class="st-num">90 天</div>
            <div class="st-label">可订团期</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 行程规划：平台主功能 -->
    <section class="plan-band">
      <div class="container">
        <div class="plan-card card">
          <div class="plan-copy">
            <div class="plan-eyebrow">✦ 平台主功能 · 文旅行程规划</div>
            <h2>没有现成方案？<br />说句话，现场给你排一本</h2>
            <ul class="plan-points">
              <li><span class="pp-ico">🗓</span><div><b>逐日动线</b><p>想去哪、玩几天、花多少，说清就开工</p></div></li>
              <li><span class="pp-ico">📦</span><div><b>素材来自标品库</b><p>只用企业已核验的景点、餐饮、住宿素材，不瞎编</p></div></li>
              <li><span class="pp-ico">✅</span><div><b>可转方案上架</b><p>排得好的行程，企业可一键沉淀为可售线路方案</p></div></li>
              <li><span class="pp-ico">✏️</span><div><b>随时可改</b><p>时间、节奏、酒店，喜欢哪页改哪页</p></div></li>
            </ul>
          </div>
          <form class="plan-form" @submit.prevent="onPlanSubmit">
            <div class="pf-field pf-full">
              <label>出发地 <b>*</b></label>
              <input v-model.trim="plan.origin" class="input" required placeholder="如：上海 / 南京（用于大交通规划）" maxlength="20" list="origin-list" />
              <datalist id="origin-list">
                <option v-for="c in ORIGIN_CITIES" :key="c" :value="c" />
              </datalist>
            </div>
            <div class="pf-field pf-full">
              <label>目的地 <b>*</b></label>
              <input v-model.trim="plan.destination" class="input" required placeholder="如：苏州 / 北京 / 杭州" maxlength="20" />
            </div>
            <div class="pf-grid">
              <div class="pf-field">
                <label>天数</label>
                <select v-model.number="plan.days" class="select">
                  <option v-for="d in 14" :key="d" :value="d">{{ d }} 天</option>
                </select>
              </div>
              <div class="pf-field">
                <label>预算（元）</label>
                <input v-model.number="plan.budget" class="input" type="number" min="0" step="100" placeholder="8000" />
              </div>
              <div class="pf-field">
                <label>出行日期</label>
                <button type="button" class="date-text" @click="dateOpen = true">
                  {{ dateRangeText || '选择出发 / 返程日期' }} <span class="dt-edit">{{ dateRangeText ? '修改' : '' }}</span>
                </button>
              </div>
            </div>

            <!-- 偏好设置（携程 AI 行程式问卷）：可收纳，默认收起；展开再点选，收起时显示已选摘要 -->
            <div class="pf-prefs">
              <button type="button" class="pf-prefs-head" :aria-expanded="prefsOpen" @click="prefsOpen = !prefsOpen">
                <span class="pf-prefs-title">偏好设置</span>
                <span class="pf-prefs-summary" :class="{ set: prefsMeta.dirty }">{{ prefsMeta.text }}</span>
                <svg class="pf-chev" :class="{ open: prefsOpen }" width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
              <div v-show="prefsOpen" class="pf-prefs-body">
                <div class="pf-field">
                  <label>和谁一起去</label>
                  <div class="chip-group">
                    <button type="button" v-for="g in GROUPS" :key="g.label" class="chip"
                            :class="{ active: plan.group === g.label }" @click="pickOne(plan, 'group', g.label)">{{ g.label }}</button>
                  </div>
                </div>
                <div class="pf-field">
                  <label>想玩什么 <span class="pf-opt-hint">可多选</span></label>
                  <div class="chip-group">
                    <button type="button" v-for="it in INTERESTS" :key="it.label" class="chip"
                            :class="{ active: plan.interests.includes(it.label) }" @click="toggleInterest(it.label)">{{ it.label }}</button>
                  </div>
                </div>
                <div class="pf-field">
                  <label>行程节奏</label>
                  <div class="chip-group">
                    <button type="button" v-for="r in RHYTHMS" :key="r.label" class="chip"
                            :class="{ active: plan.rhythm === r.label }" @click="pickOne(plan, 'rhythm', r.label)">{{ r.label }}</button>
                  </div>
                </div>
                <div class="pf-field">
                  <label>作息习惯</label>
                  <div class="chip-group">
                    <button type="button" v-for="s in SLEEPS" :key="s.label" class="chip"
                            :class="{ active: plan.sleep === s.label }" @click="pickOne(plan, 'sleep', s.label)">{{ s.label }}</button>
                  </div>
                </div>
                <div class="pf-field">
                  <label>其它要求 <span class="pf-opt-hint">预算分配 / 忌口等</span></label>
                  <input v-model.trim="plan.note" class="input" maxlength="60" placeholder="如：当地美食与中餐结合 · 人均预算 1 万" />
                </div>
              </div>
            </div>
            <div class="pf-actions">
              <button type="button" class="btn btn-ghost manual-btn" @click="goManual">
                🧩 手动行程规划 <small>从标品库自己拼</small>
              </button>
              <button class="btn btn-primary btn-lg plan-btn" :disabled="creating || !plan.destination" @click="onPlanSubmit">
                <span v-if="creating" class="spinner" style="width:16px;height:16px;border-width:2.5px"></span>
                {{ creating ? '正在规划…' : '✦ 开始规划我的行程' }}
              </button>
            </div>
            <p class="pf-tip">约 1-3 分钟生成 · 生成后随时可改 · 可提交企业沉淀为线路方案</p>
          </form>

          <!-- 日期选择弹窗：出发日期 + 返程日期 -->
          <Teleport to="body">
            <div v-if="dateOpen" class="date-mask" @click.self="dateOpen = false">
              <div class="date-pop card">
                <div class="dp-head">
                  <b>选择出行日期</b>
                  <button type="button" class="dp-x" @click="dateOpen = false">×</button>
                </div>
                <div class="dp-body">
                  <label class="dp-field">
                    <span>出发日期</span>
                    <input v-model="plan.date" class="input" type="date" :min="today" @change="fixReturn" />
                  </label>
                  <label class="dp-field">
                    <span>返程日期</span>
                    <input v-model="plan.dateReturn" class="input" type="date" :min="plan.date || today" />
                  </label>
                  <p class="dp-hint">返程日期 = 出发日期 + 天数 - 1（可手动调整；调整后天数自动同步）</p>
                </div>
                <div class="dp-foot">
                  <button type="button" class="btn btn-ghost" @click="plan.date = ''; plan.dateReturn = ''; dateOpen = false">清除</button>
                  <button type="button" class="btn btn-primary" @click="applyDates">确定</button>
                </div>
              </div>
            </div>
          </Teleport>
        </div>
      </div>
    </section>

    <!-- 玩法 × 方案（电商式分类橱窗：玩法 tab 即类目，方案卡直达详情） -->
    <section class="container sec">
      <div class="sec-head">
        <div>
          <div class="sec-title">🧭 挑方案：按玩法选类目</div>
          <p class="sec-desc">选一个玩法（类目），下方直接给出该类目在售方案——与「线路方案」馆同一份库存</p>
        </div>
        <router-link :to="{ name: 'malls' }" class="more-link">进线路方案馆 →</router-link>
      </div>
      <div class="cat-tabs">
        <button v-for="c in themes" :key="c.name"
                :class="['cat-tab', { on: shopCat === c.name }]"
                :style="{ '--cat-c': c.color }"
                @click="shopCat = c.name; filterShopByCat()">
          <span class="ct-emoji">{{ c.emoji }}</span>
          <span class="ct-label">{{ c.name }}</span>
          <i class="ct-cnt">{{ c.count }}</i>
        </button>
      </div>
      <p class="shop-sub">{{ shopCat ? `「${shopCat}」在售方案` : '全部在售方案' }} · 按人计价一价全包</p>
      <div class="shop-grid">
        <router-link v-for="p in shopPlans" :key="p.id"
                     :to="{ name: 'malls-product', params: { id: p.id } }"
                     class="shop-card card card-hover">
          <PhotoCover :cover="p.cover" :photos="p.photos || []" auto>
            <div class="shop-badges">
              <span v-for="b in p.badges" :key="b" class="bd">{{ b }}</span>
            </div>
            <span class="days-chip">{{ p.days }} 日</span>
          </PhotoCover>
          <div class="shop-body">
            <div class="shop-cat">{{ p.category }} · {{ p.city }}</div>
            <div class="shop-name">{{ p.name }}</div>
            <div class="shop-meta">
              <span class="rating">★ {{ p.rating.toFixed(1) }}</span>
              <span>售 {{ formatSales(p.sales) }}</span>
              <span>{{ p.poi_count }} 点位 · {{ p.pace_zh }}</span>
            </div>
            <div class="shop-price">
              <span class="y">¥</span><b>{{ p.per_price }}</b><span class="suffix"> /人 整订</span>
              <s v-if="p.original_per_price > p.per_price" class="p-orig">¥{{ p.original_per_price }}</s>
            </div>
          </div>
        </router-link>
      </div>
    </section>

    <!-- 城市 -->
    <section class="container sec">
      <div class="sec-head">
        <div>
          <div class="sec-title">🏙 从城市出发</div>
          <p class="sec-desc">挑目的地，看本地已排好的线路</p>
        </div>
      </div>
      <div class="city-row">
        <router-link v-for="c in cities" :key="c.name"
                     :to="{ name: 'malls-search', query: { city: c.name } }"
                     class="city-tile"
                     :style="{ background: cityGradient(c.name) }">
          <span class="city-emoji">🏯</span>
          <div class="city-meta">
            <div class="city-name">{{ c.name }}</div>
            <div class="city-hint">{{ c.count }} 条线路方案</div>
          </div>
          <span class="city-arrow">→</span>
        </router-link>
      </div>
    </section>

    <!-- 整订保障 -->
    <section class="container sec">
      <div class="sec-head">
        <div>
          <div class="sec-title">🛡 为什么敢整订</div>
          <p class="sec-desc">方案背后是素材库 → 编排 → 报价的全链路保障</p>
        </div>
      </div>
      <div class="assure-grid">
        <div v-for="a in ASSURE" :key="a.title" class="assure-card card">
          <div class="as-emoji">{{ a.emoji }}</div>
          <div class="as-title">{{ a.title }}</div>
          <p class="as-desc">{{ a.desc }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { plansApi, planShopApi, svcApi } from '../../api'
import { useAuthStore } from '../../stores/auth'
import { toast } from '../../composables/toast'
import PhotoCover from '../../components/PhotoCover.vue'

const route = useRoute()
const auth = useAuthStore()
const kw = ref('')
const plans = ref([])
const themes = ref([])
const cities = ref([])
const creating = ref(false)
const prefsOpen = ref(false)
const dateOpen = ref(false)
const plan = reactive({ destination: '', origin: '', days: 3, budget: 8000, date: '', dateReturn: '', group: '', interests: [], rhythm: '', sleep: '', note: '' })

const ORIGIN_CITIES = ['上海', '南京', '杭州', '北京', '苏州', '无锡', '常州', '合肥', '武汉', '广州', '深圳', '成都', '西安', '天津']

// 玩法类目选择的方案过滤（电商式：tab=类目，卡片=该类目在售方案）
const shopCat = ref('')
const shopPlans = computed(() => (shopCat.value ? plans.value.filter(p => p.category === shopCat.value) : plans.value))

function filterShopByCat() { /* 响应式 computed 已联动，这里只留 tab 切换语义 */ }
const today = new Date().toISOString().slice(0, 10)

// 日期按钮文案
const dateRangeText = computed(() => {
  if (!plan.date) return ''
  const zh = (d) => `${Number(d.slice(5, 7))}月${Number(d.slice(8, 10))}日`
  return plan.dateReturn && plan.dateReturn !== plan.date
    ? `${zh(plan.date)} — ${zh(plan.dateReturn)}`
    : zh(plan.date)
})

// 出发日 → 天数联动：返程日变化时自动同步天数；天数变化时自动推返程日
function fixReturn() {
  if (!plan.date) { plan.dateReturn = ''; return }
  const ms = new Date(plan.date).getTime() + (plan.days - 1) * 86400000
  const auto = new Date(ms).toISOString().slice(0, 10)
  if (!plan.dateReturn || new Date(plan.dateReturn) < new Date(plan.date)) plan.dateReturn = auto
}
function syncDays() {
  if (plan.date && plan.dateReturn) {
    const diff = Math.round((new Date(plan.dateReturn) - new Date(plan.date)) / 86400000) + 1
    if (diff >= 1 && diff <= 14) plan.days = diff
  }
}
watch(() => plan.dateReturn, syncDays)
function applyDates() { fixReturn(); syncDays(); dateOpen.value = false }

// 需求1：未登录点击"开始规划" → 弹登录注册弹窗（登录成功由 TocLayout 处理回跳）
function onPlanSubmit() {
  if (!auth.isLogged) {
    router.replace({ query: { ...route.query, login: 1, next: route.fullPath } })
    return
  }
  createPlan()
}
function goManual() {
  if (!auth.isLogged) {
    router.replace({ query: { ...route.query, login: 1, next: '/manual' } })
    return
  }
  router.push({ name: 'manual-composer' })
}

// 收起态摘要：选了哪些选项一目了然；全不选时提示可跳过
const prefsMeta = computed(() => {
  const items = [plan.group, ...plan.interests, plan.rhythm, plan.sleep]
  if (plan.note) items.push('备注要求')
  const dirty = items.length > 0
  const text = dirty
    ? `已选 ${items.slice(0, 3).join('、')}${items.length > 3 ? ` 等 ${items.length} 项` : ''}`
    : '选填 · 全不选也能直接生成'
  return { dirty, text }
})

async function createPlan() {
  if (!plan.destination || creating.value) return
  creating.value = true
  try {
    const group = GROUPS.find((g) => g.label === plan.group)
    // 兴趣选项 → 偏好词；节奏/作息/备注 → 结构化约束，交给 Intake 解析成 pacing 与 parsed_flags
    const prefs = plan.interests.map((label) => (INTERESTS.find((i) => i.label === label) || {}).tag || label)
    const constraints = []
    if (group) {
      if (group.slow) constraints.push('不要太赶')
      if (group.prefs) prefs.push(...group.prefs)
    }
    const rhythmTag = plan.rhythm && RHYTHMS.find((r) => r.label === plan.rhythm)?.tag
    if (rhythmTag) constraints.push(rhythmTag)
    if (plan.sleep && SLEEPS.find((s) => s.label === plan.sleep)?.late) constraints.push('晚起，不赶早')
    if (plan.note) constraints.push(plan.note)

    const payload = {
      destination: plan.destination,
      days: plan.days || 3,
      budget: Number(plan.budget || 0),
      travelers: group ? group.travelers : 2,
    }
    if (plan.origin) payload.origin = plan.origin
    if (plan.date) payload.departure_date = plan.date
    if (prefs.length) payload.preferences = [...new Set(prefs)]
    if (constraints.length) payload.constraints = [...new Set(constraints)]
    const r = await plansApi.create(payload)
    toast('行程任务已创建，正在为你规划', 'ok')
    router.push({ name: 'plan-detail', params: { jobId: r.job_id } })
  } catch (e) {
    toast('创建失败：' + (e.message || e), 'err')
  } finally {
    creating.value = false
  }
}

const HOT_KW = ['苏州', '北京', '园林古建', '亲子', '文化漫游']

// 携程 AI 行程式偏好问卷：选项文案贴近用户习惯，tag 对齐景点素材库/管线解析关键词
const GROUPS = [
  { label: '独自旅行', travelers: 1 },
  { label: '情侣同行', travelers: 2 },
  { label: '亲子同行', travelers: 3, prefs: ['亲子'] },
  { label: '长辈同行', travelers: 3, slow: true },
  { label: '朋友结伴', travelers: 4 },
]
const INTERESTS = [
  { label: '美食探店', tag: '美食' },
  { label: '人文历史', tag: '历史' },
  { label: '博物馆艺术', tag: '博物馆' },
  { label: '自然风光', tag: '自然' },
  { label: '城市漫步', tag: '城市漫步' },
  { label: '亲子同乐', tag: '亲子' },
  { label: '摄影出片', tag: '摄影' },
  { label: '夜生活', tag: '夜游' },
]
const RHYTHMS = [
  { label: '松弛一点，慢慢逛', tag: '不要太赶' },
  { label: '节奏适中就行' },
  { label: '特种兵拉练' },
]
const SLEEPS = [
  { label: '每天早点出发' },
  { label: '睡到自然醒', late: true },
]

function pickOne(scope, key, value) {
  scope[key] = scope[key] === value ? '' : value
}
function toggleInterest(label) {
  const i = plan.interests.indexOf(label)
  i >= 0 ? plan.interests.splice(i, 1) : plan.interests.push(label)
}

const ASSURE = [
  { emoji: '🏭', title: '素材库严选', desc: '方案里的每个点位都来自企业已核验的标品素材：营业时间、票价、建议时长真实在库' },
  { emoji: '🛤', title: '动线已排好', desc: '每日去哪儿、几点到、玩多久都由编排器算好，不绕路不空档' },
  { emoji: '💰', title: '整体报价', desc: '门票、餐饮、住宿打包成"人均价"，下单前就知道这一趟花多少' },
  { emoji: '↩️', title: '可退可改', desc: '出行前 1 天 18:00 前可全额退，行程内点位也可再调整' },
]

function formatSales(n) { return n >= 10000 ? (n / 10000).toFixed(1) + 'w' : String(n) }
function goSearch() {
  const q = kw.value.trim()
  router.push({ name: 'malls-search', query: q ? { q } : {} })
}

const CITY_GRADIENTS = {
  苏州: 'linear-gradient(135deg,#FDE7D2,#C2683A)', 北京: 'linear-gradient(135deg,#F3D5CE,#B03A48)',
  上海: 'linear-gradient(135deg,#D4E5F7,#3B82F6)', 西安: 'linear-gradient(135deg,#E8D9B7,#8B5A2B)',
  成都: 'linear-gradient(135deg,#D7F0DD,#2F9E68)', 杭州: 'linear-gradient(135deg,#D6EFEC,#0E8C86)',
}
function cityGradient(name) { return CITY_GRADIENTS[name] || 'linear-gradient(135deg,#E2E8F0,#94A3B8)' }

async function load() {
  try {
    const [feat, cat] = await Promise.allSettled([planShopApi.featured(), planShopApi.categories()])
    if (feat.status === 'fulfilled') plans.value = (feat.value.items || []).slice(0, 8)
    if (cat.status === 'fulfilled') {
      themes.value = cat.value.themes || []
      cities.value = cat.value.cities || []
    }
  } catch (e) { /* 静默 */ }
  loadPhotos()
}

// 需求5：精选方案卡片拉景点实拍图（高德 POI 图），每 3.5s 轮换
async function loadPhotos() {
  for (const p of plans.value.slice(0, 6)) {
    try {
      const spots = (p.product_ids || []).length ? '' : ''
      const r = await svcApi.planPhotos(p.city, p.photo_spots || spots)
      if (r.photos && r.photos.length) p.photos = r.photos
    } catch { /* 无图保持 emoji 封面 */ }
  }
  // 轮换由 PhotoCover 组件自驱动（auto）
}

onMounted(load)
</script>

<style scoped>
.home { padding-bottom: 40px; }
.hero {
  padding: 60px 0 46px;
  background:
    radial-gradient(700px 320px at 78% 12%, rgba(224,138,60,.10), transparent 60%),
    radial-gradient(900px 420px at 8% -8%, rgba(59,130,246,.08), transparent 55%);
}
.hero-inner { display: grid; grid-template-columns: 1.4fr 1fr; gap: 40px; align-items: center; }
.hero-tag {
  display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600;
  color: var(--accent-700); background: var(--accent-50, #FFFBEB); border: 1px solid var(--accent-500);
  padding: 6px 14px; border-radius: 999px; margin-bottom: 18px;
}
.hero-title { font-size: clamp(32px, 4.8vw, 50px); font-weight: 900; line-height: 1.22; letter-spacing: -.03em; color: var(--ink-900); margin: 0; }
.hero-title .grad {
  background: linear-gradient(100deg, var(--accent-600), var(--brand-600));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { margin: 16px 0 24px; font-size: 16px; color: var(--ink-500); max-width: 580px; line-height: 1.7; }
.search-bar {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 10px 10px 18px; max-width: 620px; box-shadow: 0 8px 28px rgba(15,23,42,.08);
}
.s-icon { font-size: 18px; color: var(--ink-400); }
.s-input { flex: 1; border: none; outline: none; background: transparent; font-size: 15px; color: var(--ink-900); padding: 10px 0; }
.s-input::placeholder { color: var(--ink-400); }
.hot-search { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; font-size: 13px; color: var(--ink-500); }
.hs-chip {
  background: #fff; border: 1px solid var(--ink-200); padding: 4px 12px; border-radius: 999px;
  font-size: 12.5px; color: var(--ink-700); cursor: pointer; transition: all .14s;
}
.hs-chip:hover { border-color: var(--brand-500); color: var(--brand-700); }
.hero-right { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.hero-stat {
  background: #fff; border-radius: var(--r-md); padding: 22px 18px;
  box-shadow: 0 4px 18px rgba(15,23,42,.05); border: 1px solid var(--ink-100);
}
.st-num { font-size: 26px; font-weight: 900; color: var(--ink-900); letter-spacing: -.02em; }
.st-label { font-size: 12.5px; color: var(--ink-500); margin-top: 4px; }

.plan-band {
  margin-top: 56px;
  background:
    radial-gradient(700px 300px at 10% 0%, rgba(224,138,60,.12), transparent 60%),
    radial-gradient(900px 340px at 100% 100%, rgba(37,99,235,.08), transparent 55%);
  padding: 34px 0;
}
.plan-card {
  display: grid; grid-template-columns: 1.1fr .9fr; gap: 40px; padding: 40px 44px;
  box-shadow: 0 10px 40px rgba(15,23,42,.10); border-top: 4px solid var(--brand-500);
}
.plan-eyebrow {
  display: inline-flex; padding: 5px 13px; border-radius: 999px; font-size: 12.5px; font-weight: 700;
  color: var(--brand-700); background: var(--brand-50); border: 1px solid var(--brand-200); margin-bottom: 14px;
}
.plan-copy h2 { font-size: clamp(24px, 3vw, 32px); font-weight: 900; line-height: 1.3; letter-spacing: -.02em; color: var(--ink-900); margin: 0 0 22px; }
.plan-points { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.plan-points li { display: flex; gap: 12px; align-items: flex-start; }
.pp-ico { width: 38px; height: 38px; flex: none; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; background: var(--ink-50); border: 1px solid var(--ink-200); }
.plan-points b { font-size: 14.5px; color: var(--ink-900); }
.plan-points p { font-size: 12.5px; color: var(--ink-500); margin: 2px 0 0; line-height: 1.5; }
.plan-form {
  display: flex; flex-direction: column; gap: 12px;
  background: linear-gradient(180deg, var(--ink-50), #fff); border: 1px solid var(--ink-200);
  border-radius: var(--r-lg); padding: 24px;
}
.pf-full { width: 100%; }
.pf-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.pf-field { display: flex; flex-direction: column; gap: 6px; }
.pf-field label { font-size: 13px; font-weight: 700; color: var(--ink-700); }
.pf-field label b { color: var(--danger); }
.plan-btn { width: 100%; margin-top: 6px; }
.pf-tip { font-size: 12px; color: var(--ink-400); text-align: center; margin: 2px 0 0; }

/* 出行日期按钮 + 弹窗 */
.date-text {
  border: none; background: none; padding: 2px 0; cursor: pointer; text-align: left;
  font-size: 14px; font-weight: 700; color: var(--brand-600);
}
.date-text:hover { text-decoration: underline; }
.date-text .dt-edit {
  font-size: 11px; font-weight: 600; color: #fff; background: var(--brand-500);
  border-radius: 999px; padding: 1px 8px; margin-left: 4px;
}
.pf-actions { display: flex; gap: 12px; align-items: stretch; margin-top: 6px; }
.pf-actions .manual-btn { flex: none; display: flex; flex-direction: column; align-items: flex-start; gap: 0; font-weight: 700; }
.pf-actions .manual-btn small { font-weight: 400; font-size: 11px; color: var(--ink-400); }
.pf-actions .plan-btn { flex: 1; }
.date-mask { position: fixed; inset: 0; background: rgba(15,23,42,.45); backdrop-filter: blur(3px); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.date-pop { width: min(360px, 100%); padding: 20px 22px; }
.dp-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.dp-head b { font-size: 15.5px; }
.dp-x { border: none; background: none; font-size: 22px; color: var(--ink-400); cursor: pointer; line-height: 1; }
.dp-body { display: flex; flex-direction: column; gap: 12px; }
.dp-field { display: flex; flex-direction: column; gap: 5px; }
.dp-field span { font-size: 13px; font-weight: 700; color: var(--ink-700); }
.dp-hint { font-size: 11.5px; color: var(--ink-400); margin: 0; }
.dp-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }

/* 精选卡片景点图轮换 */
.shop-cover { aspect-ratio: 4/3; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
.shop-photo { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; animation: photoIn .5s ease; }
@keyframes photoIn { from { opacity: 0; transform: scale(1.04); } to { opacity: 1; transform: scale(1); } }
.photo-dots { position: absolute; bottom: 8px; left: 0; right: 0; display: flex; justify-content: center; gap: 5px; z-index: 2; }
.photo-dots i { width: 6px; height: 6px; border-radius: 999px; background: rgba(255,255,255,.55); transition: all .25s; }
.photo-dots i.on { background: #fff; width: 14px; }
.shop-cover .shop-badges, .shop-cover .days-chip { z-index: 2; }
.pf-prefs {
  display: flex; flex-direction: column;
  border-top: 1px dashed var(--ink-200); padding-top: 12px; margin-top: 2px;
}
.pf-prefs-head {
  all: unset; box-sizing: border-box; display: flex; align-items: center; gap: 8px;
  width: 100%; cursor: pointer; color: inherit;
}
.pf-prefs-head:hover .pf-prefs-title { color: var(--brand-600); }
.pf-prefs-head:focus-visible { outline: 2px solid var(--brand-400); outline-offset: 2px; border-radius: 6px; }
.pf-prefs-title { font-size: 13px; font-weight: 800; color: var(--ink-900); white-space: nowrap; }
.pf-prefs-summary {
  flex: 1; min-width: 0; font-size: 11.5px; color: var(--ink-400); text-align: left;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pf-prefs-summary.set { color: var(--brand-600); }
.pf-chev { flex: none; color: var(--ink-400); transition: transform .25s ease; }
.pf-chev.open { transform: rotate(180deg); }
.pf-prefs-body { display: flex; flex-direction: column; gap: 12px; padding-top: 12px; }
.pf-opt-hint { font-weight: 500; color: var(--ink-400); font-size: 11px; }
.pf-prefs .chip { font-size: 12.5px; padding: 5px 12px; }

.sec { margin-top: 56px; }
.sec-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 18px; flex-wrap: wrap; }
.sec-title { font-size: 22px; font-weight: 900; color: var(--ink-900); letter-spacing: -.01em; }
.sec-desc { font-size: 13.5px; color: var(--ink-500); margin-top: 4px; }
.more-link { font-size: 14px; color: var(--brand-600); font-weight: 700; text-decoration: none !important; }
.more-link:hover { color: var(--brand-700); }

.cat-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.cat-tab {
  display: inline-flex; align-items: center; gap: 7px; cursor: pointer;
  background: #fff; border: 1.5px solid var(--ink-200); border-radius: 999px;
  padding: 9px 18px; font-size: 14px; font-weight: 700; color: var(--ink-700); transition: all .15s;
  border-bottom-color: var(--cat-c, var(--brand-500));
}
.cat-tab:hover { border-color: var(--cat-c, var(--brand-500)); color: var(--ink-900); transform: translateY(-1px); }
.cat-tab.on { background: var(--cat-c, var(--brand-600)); border-color: var(--cat-c, var(--brand-600)); color: #fff; }
.cat-tab .ct-emoji { font-size: 17px; }
.cat-tab .ct-cnt {
  font-style: normal; font-size: 11px; font-weight: 800; background: rgba(15,23,42,.08);
  border-radius: 999px; padding: 1px 7px;
}
.cat-tab.on .ct-cnt { background: rgba(255,255,255,.25); }
.shop-sub { font-size: 13px; color: var(--ink-500); margin: 0 0 12px; font-weight: 600; }
.ct-label { font-weight: 800; font-size: 14px; }

.shop-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.shop-card { padding: 0; overflow: hidden; text-decoration: none !important; transition: all .18s; }
.shop-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.shop-emoji { font-size: 70px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.18)); }
.shop-badges { position: absolute; left: 10px; top: 10px; display: flex; gap: 4px; flex-wrap: wrap; }
.shop-badges .bd { background: rgba(0,0,0,.45); color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 4px; backdrop-filter: blur(6px); }
.days-chip { position: absolute; right: 10px; top: 10px; background: rgba(255,255,255,.92); color: var(--ink-900); font-size: 11.5px; font-weight: 800; padding: 2px 9px; border-radius: 999px; }
.shop-body { padding: 14px 16px 16px; }
.shop-cat { font-size: 11.5px; color: var(--ink-400); }
.shop-name { font-weight: 700; font-size: 14.5px; color: var(--ink-900); margin: 4px 0 6px; min-height: 2.6em; line-height: 1.35; }
.shop-meta { display: flex; flex-wrap: wrap; gap: 10px; font-size: 12px; color: var(--ink-500); }
.shop-meta .rating { color: var(--accent-600); font-weight: 700; }
.shop-price { display: flex; align-items: baseline; gap: 4px; margin-top: 8px; flex-wrap: wrap; }
.shop-price .y { font-size: 13px; color: var(--danger); font-weight: 700; }
.shop-price b { font-size: 22px; color: var(--danger); font-weight: 900; }
.shop-price .suffix { font-size: 12px; color: var(--ink-500); }
.p-orig { font-size: 12px; color: var(--ink-400); font-weight: 500; }

.city-row { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.city-tile {
  display: flex; align-items: center; gap: 12px; padding: 18px 16px; border-radius: var(--r-md); color: #fff;
  text-decoration: none !important; position: relative; overflow: hidden; transition: all .15s;
}
.city-tile:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(15,23,42,.18); }
.city-emoji { font-size: 30px; filter: drop-shadow(0 2px 6px rgba(0,0,0,.18)); }
.city-name { font-weight: 800; font-size: 16px; letter-spacing: -.01em; }
.city-hint { font-size: 11.5px; opacity: .85; margin-top: 2px; }
.city-arrow { position: absolute; right: 14px; top: 50%; transform: translateY(-50%); font-size: 18px; opacity: .7; }

.assure-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.assure-card { padding: 22px 24px; }
.as-emoji { font-size: 28px; margin-bottom: 8px; }
.as-title { font-weight: 800; font-size: 15.5px; color: var(--ink-900); }
.as-desc { font-size: 13px; color: var(--ink-500); margin-top: 6px; line-height: 1.7; }

@media (max-width: 980px) {
  .hero-inner { grid-template-columns: 1fr; }
  .hero-right { grid-template-columns: repeat(4, 1fr); }

  .shop-grid { grid-template-columns: repeat(2, 1fr); }
  .city-row { grid-template-columns: repeat(3, 1fr); }
  .assure-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .plan-card { grid-template-columns: 1fr; gap: 28px; padding: 30px 24px; }
  .pf-grid { grid-template-columns: 1fr; }
}
@media (max-width: 540px) {
  .hero-right { grid-template-columns: repeat(2, 1fr); }
  .cat-strip { grid-template-columns: repeat(2, 1fr); }
  .shop-grid { grid-template-columns: 1fr; }
  .city-row { grid-template-columns: repeat(2, 1fr); }
  .assure-grid { grid-template-columns: 1fr; }
}
</style>
