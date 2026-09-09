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
          <form class="plan-form" @submit.prevent="createPlan">
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
                <label>出发日期</label>
                <input v-model="plan.date" class="input" type="date" />
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
            <button class="btn btn-primary btn-lg plan-btn" :disabled="creating || !plan.destination">
              <span v-if="creating" class="spinner" style="width:16px;height:16px;border-width:2.5px"></span>
              {{ creating ? '正在规划…' : '✦ 开始规划我的行程' }}
            </button>
            <p class="pf-tip">约 1-3 分钟生成 · 生成后随时可改 · 可提交企业沉淀为线路方案</p>
          </form>
        </div>
      </div>
    </section>

    <!-- 玩法主题 -->
    <section class="container sec">
      <div class="sec-head">
        <div>
          <div class="sec-title">按玩法挑方案</div>
          <p class="sec-desc">不是按门票分类，而是按你想怎么玩挑</p>
        </div>
      </div>
      <div class="cat-strip">
        <router-link v-for="c in themes" :key="c.name"
                     :to="{ name: 'malls-category', params: { key: c.name } }"
                     class="cat-tile"
                     :style="{ '--cat-c': c.color }">
          <span class="ct-emoji">{{ c.emoji }}</span>
          <span class="ct-label">{{ c.name }}</span>
          <span class="ct-hint">{{ c.desc }} · {{ c.count }} 条</span>
        </router-link>
      </div>
    </section>

    <!-- 精选线路方案 -->
    <section class="container sec">
      <div class="sec-head">
        <div>
          <div class="sec-title">🧭 精选线路方案</div>
          <p class="sec-desc">整体报价按人计，一条线路含每日动线，不用自己拼票</p>
        </div>
        <router-link :to="{ name: 'malls' }" class="more-link">全部方案 →</router-link>
      </div>
      <div class="shop-grid">
        <router-link v-for="p in plans" :key="p.id"
                     :to="{ name: 'malls-product', params: { id: p.id } }"
                     class="shop-card card card-hover">
          <div class="shop-cover" :style="{ background: p.cover.gradient }">
            <span class="shop-emoji">{{ p.cover.emoji }}</span>
            <div class="shop-badges">
              <span v-for="b in p.badges" :key="b" class="bd">{{ b }}</span>
            </div>
            <span class="days-chip">{{ p.days }} 日</span>
          </div>
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
import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { plansApi, planShopApi } from '../../api'
import { toast } from '../../composables/toast'

const router = useRouter()
const kw = ref('')
const plans = ref([])
const themes = ref([])
const cities = ref([])
const creating = ref(false)
const prefsOpen = ref(false)
const plan = reactive({ destination: '', days: 3, budget: 8000, date: '', group: '', interests: [], rhythm: '', sleep: '', note: '' })

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

.cat-strip { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.cat-tile {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: #fff; border: 1px solid var(--ink-200); border-radius: var(--r-md);
  padding: 22px 12px; text-decoration: none !important; text-align: center;
  border-top: 3px solid var(--cat-c, var(--brand-500)); transition: all .15s;
}
.cat-tile:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(15,23,42,.08); border-color: var(--cat-c, var(--brand-500)); }
.ct-emoji { font-size: 32px; margin-bottom: 8px; }
.ct-label { font-weight: 800; font-size: 15px; color: var(--ink-900); }
.ct-hint { font-size: 12px; color: var(--ink-500); margin-top: 4px; }

.shop-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.shop-card { padding: 0; overflow: hidden; text-decoration: none !important; transition: all .18s; }
.shop-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.shop-cover { aspect-ratio: 4/3; display: flex; align-items: center; justify-content: center; position: relative; }
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
  .cat-strip { grid-template-columns: repeat(3, 1fr); }
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
