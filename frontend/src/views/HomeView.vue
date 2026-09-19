<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { planShopApi } from '../api/index.js'

const router = useRouter()
const kw = ref('')

// 城市卡：后端方案馆按城市聚合（GET /api/plan-products），失败时回退静态演示数据
const CITY_COVERS = {
  '苏州': '/covers/c1043.jpg', '杭州': '/covers/s_xiamen1.jpg', '大理': '/covers/c1015.jpg',
  '成都': '/covers/c342.jpg', '厦门': '/covers/c154.jpg', '西安': '/covers/s_xian1.jpg',
  '北京': '/covers/s_chengdu1.jpg', '南京': '/covers/s_lake1.jpg',
}
const CITY_DESC = {
  '苏州': '园林与水巷', '杭州': '湖山与人文', '大理': '苍洱与白族',
  '成都': '美食与熊猫', '厦门': '海岛与骑楼', '西安': '长安与古道',
  '北京': '皇城与胡同', '南京': '六朝与烟水',
}
const FALLBACK_CITIES = [
  { name: '苏州', desc: '园林与水巷', n: 12, photo: '/covers/c1043.jpg', pid: 'p101' },
  { name: '杭州', desc: '湖山与人文', n: 18, photo: '/covers/s_xiamen1.jpg', pid: 'p102' },
  { name: '大理', desc: '苍洱与白族', n: 9,  photo: '/covers/c1015.jpg',   pid: 'p103' },
  { name: '成都', desc: '美食与熊猫', n: 14, photo: '/covers/c342.jpg',    pid: 'p104' },
  { name: '厦门', desc: '海岛与骑楼', n: 7,  photo: '/covers/c154.jpg',     pid: 'p105' },
  { name: '西安', desc: '长安与古道', n: 11, photo: '/covers/s_xian1.jpg',  pid: 'p106' },
]
const cities = ref(FALLBACK_CITIES)
const stats = ref([
  { v: '4',     l: '已上线路方案' },
  { v: '6',     l: '素材覆盖分类' },
  { v: '整订',  l: '一价含门票食宿' },
  { v: '90 天', l: '可订团期' },
])
// 「查看示例」指向最近一个已完成任务（无可示例任务时回退规划列表）
const samplePlanHref = ref('/plans')

// 搜索 / 热门词 → 方案馆带关键词（MallsView 读取 kw query）
function goSearch(kw) {
  router.push({ path: '/malls', query: { kw } })
}

onMounted(async () => {
  try {
    const res = await planShopApi.list({ page: 1, page_size: 60 })
    const items = (res && res.items) || []
    if (items.length) {
      const groups = {}
      items.forEach(p => {
        const c = p.city || '其他'
        ;(groups[c] = groups[c] || { count: 0, first: p }).count++
      })
      cities.value = Object.entries(groups).slice(0, 6).map(([city, g]) => ({
        name: city,
        desc: CITY_DESC[city] || (g.first.category ? `${g.first.category}主题` : '精选线路'),
        n: g.count,
        photo: CITY_COVERS[city] || '',
        pid: g.first.id,
        cover: g.first.cover || null,
      }))
      const cats = new Set(items.map(p => p.category).filter(Boolean))
      stats.value = [
        { v: String(items.length), l: '已上线路方案' },
        { v: String(cats.size || 6), l: '素材覆盖分类' },
        { v: '整订',  l: '一价含门票食宿' },
        { v: '90 天', l: '可订团期' },
      ]
    }
  } catch { /* 后端不可用时保留兜底数据 */ }
  try {
    const res = await planShopApi.featured()
    const f = (res && res.items) || []
    if (f.length) samplePlanHref.value = `/malls/product/${f[0].id}`
  } catch { /* keep */ }
})

const features = [
  { title: '一价全包', body: '门票 / 餐饮 / 住宿 / 大交通一次打包,不再东拼西凑', icon: 'box' },
  { title: '企业核验', body: '所有素材来自景区官方与已认证供应商,不瞎编',     icon: 'shield' },
  { title: '可改可退', body: '整单行程随时调整,出行前 7 天无损改期',           icon: 'cycle' },
]
const steps = [
  { n: '01', t: '选择方案', d: '在方案馆挑一份心仪的线路方案' },
  { n: '02', t: '选定日期', d: '挑选可订团期与出行人数' },
  { n: '03', t: '一键下单', d: '整单支付,无需再补门票' },
  { n: '04', t: '整装出发', d: '到点出发,行程不再变动' },
]
</script>

<template>
  <!-- Hero -->
  <section class="hero">
    <div class="container-wide hero-grid">
      <div class="hero-copy anim-fade-up">
        <span class="eyebrow">线路方案 · 整订出发</span>
        <h1 class="hero-title">
          一份被精心排好的<br />
          <span class="hero-em">旅行方案,只等你出发。</span>
        </h1>
        <p class="hero-sub">
          每一份方案都由目的地文旅把门票、餐饮、住宿按天排好动线、打包报价。
          你只需要选一条 → 选日期与人数 → 整单下单。
        </p>

        <form class="search-bar" @submit.prevent="goSearch(kw)">
          <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
          </svg>
          <input v-model="kw" class="search-input" placeholder="搜索城市 / 主题 / 线路,例如:苏州、园林、亲子" />
          <button class="btn btn-primary-soft" type="submit">找方案</button>
        </form>

        <div class="hot-row">
          <span class="t-3 t-sm">热门:</span>
          <button v-for="q in ['苏州园林三日','成都美食四日','大理苍洱五日','西安亲子三日']" :key="q" class="hot-pill" @click="goSearch(q.slice(0, 2))">{{ q }}</button>
        </div>

        <div class="trust">
          <div class="trust-item">
            <div class="trust-num">4.92</div>
            <div class="trust-l">用户均分</div>
          </div>
          <div class="trust-sep"></div>
          <div class="trust-item">
            <div class="trust-num">12,800+</div>
            <div class="trust-l">完单旅客</div>
          </div>
          <div class="trust-sep"></div>
          <div class="trust-item">
            <div class="trust-num">96.4%</div>
            <div class="trust-l">零投诉率</div>
          </div>
        </div>
      </div>

      <!-- 排版插画(统一实拍图 + 轻遮罩) -->
      <div class="hero-art anim-fade-up delay-2" aria-hidden="false">
        <img class="hero-img" src="/covers/s_food1.jpg" alt="一段旅程" />
        <div class="hero-shade"></div>
        <!-- 浮动 mini 卡 -->
        <div class="floating-card">
          <div class="fc-tag">苏州 · 园林三日</div>
          <div class="fc-title">拙政园 · 平江路 · 山塘街</div>
          <div class="fc-meta">
            <span class="t-faint t-xs">3 天 · 一价全包</span>
            <span class="fc-price">¥1,280</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据条 -->
    <div class="container-wide stats-row">
      <div v-for="s in stats" :key="s.l" class="stat">
        <div class="stat-v">{{ s.v }}</div>
        <div class="stat-l">{{ s.l }}</div>
      </div>
    </div>
  </section>

  <!-- 价值主张 -->
  <section class="section">
    <div class="container-wide">
      <div class="section-head">
        <span class="eyebrow">为什么是这里</span>
        <h2 class="section-title">把繁琐交给文旅,只把轻松留给你。</h2>
      </div>
      <div class="features">
        <div v-for="(f, i) in features" :key="f.title" class="feature card card-hover anim-fade-up" :class="`delay-${i+1}`">
          <div class="feature-ico" aria-hidden="true">
            <svg v-if="f.icon === 'box'" viewBox="0 0 24 24" class="icon icon-xl">
              <path d="M3 7l9-4 9 4v10l-9 4-9-4V7z"/><path d="M3 7l9 4 9-4"/><path d="M12 11v10"/>
            </svg>
            <svg v-else-if="f.icon === 'shield'" viewBox="0 0 24 24" class="icon icon-xl">
              <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/><path d="m9 12 2 2 4-4"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" class="icon icon-xl">
              <path d="M3 12a9 9 0 0 1 15-6.7L21 7"/><path d="M21 3v4h-4"/><path d="M21 12a9 9 0 0 1-15 6.7L3 17"/><path d="M3 21v-4h4"/>
            </svg>
          </div>
          <h3 class="feature-title">{{ f.title }}</h3>
          <p class="feature-body">{{ f.body }}</p>
        </div>
      </div>
    </div>
  </section>

  <!-- 精选方案 -->
  <section class="section section-soft">
    <div class="container-wide">
      <div class="section-head between">
        <div>
          <span class="eyebrow">当季精选</span>
          <h2 class="section-title">六座城市,六种打开方式。</h2>
        </div>
        <RouterLink to="/malls" class="btn btn-text btn-sm">
          查看全部
          <svg class="icon icon-sm" viewBox="0 0 24 24"><path d="m9 6 6 6-6 6"/></svg>
        </RouterLink>
      </div>

      <div class="city-grid">
        <RouterLink
          v-for="(c, i) in cities" :key="c.name"
          :to="`/malls?city=${encodeURIComponent(c.name)}`"
          class="city-card card card-hover anim-fade-up"
          :class="`delay-${i+1}`">
          <div class="city-art">
            <img v-if="c.photo" class="city-img" :src="c.photo" :alt="c.name" loading="lazy" />
            <div v-else class="city-img city-fallback" :style="{ background: (c.cover && c.cover.gradient) || 'linear-gradient(135deg,#A8B7C4,#7B8DA0)' }">
              <span>{{ (c.cover && c.cover.emoji) || '🧭' }}</span>
            </div>
          </div>
          <div class="city-meta">
            <div class="row between">
              <h4 class="city-name">{{ c.name }}</h4>
              <span class="tag tag-accent-2">{{ c.n }} 个方案</span>
            </div>
            <p class="city-desc">{{ c.desc }}</p>
            <div class="row between mt-4">
              <span class="t-3 t-xs">起价 ¥980 / 人</span>
              <span class="btn btn-text btn-sm">查看 →</span>
            </div>
          </div>
        </RouterLink>
      </div>
    </div>
  </section>

  <!-- 流程 -->
  <section class="section">
    <div class="container-wide">
      <div class="section-head">
        <span class="eyebrow">如何出行</span>
        <h2 class="section-title">四步,开始一段旅程。</h2>
      </div>

      <div class="steps">
        <div v-for="(s, i) in steps" :key="s.n" class="step">
          <div class="step-num">{{ s.n }}</div>
          <h4 class="step-title">{{ s.t }}</h4>
          <p class="step-desc">{{ s.d }}</p>
          <div v-if="i < steps.length - 1" class="step-line" aria-hidden="true"></div>
        </div>
      </div>
    </div>
  </section>

  <!-- 底部 CTA -->
  <section class="section">
    <div class="container-wide">
      <div class="cta card">
        <div class="cta-copy">
          <h2 class="cta-title">说一句话,给你排一本。</h2>
          <p class="cta-body">
            没有现成方案?直接告诉 AI 你想去哪、玩几天、有什么偏好,几分钟生成一份专属动线,
            改到满意可一键沉淀为可售方案。
          </p>
        </div>
        <div class="row gap-3">
          <RouterLink to="/planner" class="btn btn-primary btn-lg">开始 AI 规划</RouterLink>
          <RouterLink :to="samplePlanHref" class="btn btn-ghost btn-lg">查看示例</RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* —— Hero —— */
.hero { padding-top: var(--s-8); padding-bottom: var(--s-7); }
.hero-grid {
  display: grid; grid-template-columns: 1.1fr .9fr;
  gap: var(--s-8); align-items: center;
}
.hero-title {
  font-size: var(--fs-4xl);
  line-height: 1.1; letter-spacing: -0.025em;
  margin: var(--s-4) 0 var(--s-5);
  font-weight: var(--fw-bold);
}
.hero-em { color: var(--accent-2); font-weight: var(--fw-bold); }
.hero-sub {
  font-size: var(--fs-md); color: var(--text-2); line-height: var(--lh-loose);
  max-width: 540px; margin-bottom: var(--s-6);
}

.search-bar {
  display: flex; align-items: center; gap: var(--s-3);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-pill); padding: var(--s-2) var(--s-2) var(--s-2) var(--s-5);
  max-width: 560px; box-shadow: var(--shadow-xs);
  transition: border-color var(--dur-2) var(--ease), box-shadow var(--dur-2) var(--ease);
}
.search-bar:focus-within { border-color: var(--text-3); box-shadow: var(--shadow-sm); }
.search-bar .icon { color: var(--text-3); }
.search-input {
  flex: 1; height: 44px; padding: 0; border: 0; background: transparent;
  font-size: var(--fs-base); color: var(--text);
}
.search-input:focus { outline: none; }
.search-input::placeholder { color: var(--text-faint); }
.search-bar .btn { height: 44px; border-radius: var(--r-pill); padding: 0 var(--s-6); }

.hot-row { display: flex; gap: var(--s-2); margin-top: var(--s-3); flex-wrap: wrap; align-items: center; }
.hot-pill {
  padding: var(--s-2) var(--s-3); border-radius: var(--r-pill);
  font-size: var(--fs-xs); color: var(--text-2); background: transparent;
  border: 1px solid transparent;
  transition: all var(--dur-1) var(--ease);
}
.hot-pill:hover { background: var(--surface); border-color: var(--border); color: var(--text); }

.trust {
  display: flex; align-items: center; gap: var(--s-5);
  margin-top: var(--s-7);
}
.trust-num { font-size: var(--fs-xl); font-weight: var(--fw-semi); color: var(--text); letter-spacing: -0.01em; }
.trust-l { font-size: var(--fs-xs); color: var(--text-3); margin-top: 2px; }
.trust-sep { width: 1px; height: 28px; background: var(--border); }

/* —— Hero Art —— */
.hero-art {
  position: relative;
  border-radius: var(--r-xl);
  overflow: hidden;
  box-shadow: var(--shadow);
  aspect-ratio: 4/3;
}
.hero-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.hero-shade {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(180deg, rgba(250,249,246,.10) 0%, rgba(250,249,246,0) 40%, rgba(31,29,26,.18) 100%);
}
.floating-card {
  position: absolute; right: var(--s-5); bottom: var(--s-5);
  background: rgba(255,255,255,.92); border: 1px solid var(--border);
  backdrop-filter: blur(6px);
  border-radius: var(--r); padding: var(--s-3) var(--s-4);
  box-shadow: var(--shadow);
  width: 220px;
  animation: floaty 6s ease-in-out infinite;
}
.fc-tag { font-size: var(--fs-xs); color: var(--accent); font-weight: var(--fw-medium); margin-bottom: var(--s-1); }
.fc-title { font-size: var(--fs-sm); color: var(--text); font-weight: var(--fw-medium); margin-bottom: var(--s-2); }
.fc-meta { display: flex; justify-content: space-between; align-items: center; }
.fc-price { font-size: var(--fs-md); font-weight: var(--fw-semi); color: var(--accent-2); }
@keyframes floaty {
  0%,100% { transform: translateY(0); }
  50%     { transform: translateY(-4px); }
}

/* —— 数据条 —— */
.stats-row {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: var(--s-5); padding: var(--s-6) var(--s-5);
  margin-top: var(--s-8);
  border-top: 1px solid var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}
.stat { text-align: left; }
.stat-v { font-size: var(--fs-2xl); font-weight: var(--fw-bold); color: var(--text); letter-spacing: -0.02em; }
.stat-l { font-size: var(--fs-sm); color: var(--text-3); margin-top: var(--s-1); }

/* —— Section —— */
.section { padding: var(--s-9) 0; }
.section-soft { background: var(--bg-soft); }
.section-head { margin-bottom: var(--s-7); }
.section-head.between { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--s-5); }
.section-title {
  font-size: var(--fs-3xl); font-weight: var(--fw-bold);
  letter-spacing: -0.02em; margin-top: var(--s-3);
  max-width: 720px;
}

/* —— Features —— */
.features {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-5);
}
.feature { padding: var(--s-6); }
.feature-ico {
  width: 48px; height: 48px; border-radius: var(--r);
  background: var(--accent-soft); color: var(--accent);
  display: inline-flex; align-items: center; justify-content: center;
  margin-bottom: var(--s-5);
}
.feature-title { font-size: var(--fs-lg); margin-bottom: var(--s-2); }
.feature-body { color: var(--text-2); line-height: var(--lh-base); }

/* —— 城市卡片 —— */
.city-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-5);
}
.city-card { padding: 0; overflow: hidden; cursor: pointer; display: block; text-decoration: none; color: inherit; transition: transform var(--dur-3) var(--ease), box-shadow var(--dur-3) var(--ease); }
.city-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.city-art {
  aspect-ratio: 16/9;
  overflow: hidden;
}
.city-img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .7s var(--ease); }
.city-fallback { display: flex; align-items: center; justify-content: center; font-size: 42px; }
.city-card:hover .city-img { transform: scale(1.05); }
.city-meta { padding: var(--s-4) var(--s-5) var(--s-5); }
.city-name { font-size: var(--fs-lg); font-weight: var(--fw-semi); }
.city-desc { font-size: var(--fs-sm); color: var(--text-2); margin-top: var(--s-2); }

/* —— 步骤 —— */
.steps {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--s-5);
  position: relative;
}
.step {
  padding: var(--s-5); border: 1px solid var(--border-soft);
  background: var(--surface); border-radius: var(--r-md);
  position: relative;
  transition: border-color var(--dur-2) var(--ease), box-shadow var(--dur-2) var(--ease);
}
.step:hover { border-color: var(--border); box-shadow: var(--shadow-sm); }
.step-num {
  font-size: var(--fs-xs); font-weight: var(--fw-medium);
  color: var(--accent); letter-spacing: 0.15em;
  margin-bottom: var(--s-3);
}
.step-title { font-size: var(--fs-md); margin-bottom: var(--s-2); }
.step-desc { font-size: var(--fs-sm); color: var(--text-2); }
.step-line {
  position: absolute; top: var(--s-7); right: calc(-1 * var(--s-5));
  width: var(--s-5); height: 1px;
  background: linear-gradient(90deg, var(--border) 50%, transparent 0);
  background-size: 6px 1px;
}

/* —— CTA —— */
.cta {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--s-7); padding: var(--s-7) var(--s-7);
  background: var(--surface);
  border-color: var(--border);
  box-shadow: var(--shadow);
}
.cta-title { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.015em; margin-bottom: var(--s-3); }
.cta-body { color: var(--text-2); line-height: var(--lh-loose); max-width: 540px; }

/* —— 响应式 —— */
@media (max-width: 1000px) {
  .hero-grid { grid-template-columns: 1fr; gap: var(--s-7); }
  .hero-art { order: -1; }
  .features { grid-template-columns: 1fr; }
  .city-grid { grid-template-columns: repeat(2, 1fr); }
  .steps { grid-template-columns: repeat(2, 1fr); }
  .step-line { display: none; }
  .stats-row { grid-template-columns: repeat(2, 1fr); gap: var(--s-4); }
  .cta { flex-direction: column; align-items: flex-start; padding: var(--s-6); }
}
@media (max-width: 640px) {
  .hero-title { font-size: var(--fs-3xl); }
  .city-grid { grid-template-columns: 1fr; }
  .steps { grid-template-columns: 1fr; }
  .stats-row { grid-template-columns: 1fr 1fr; }
  .floating-card { display: none; }
}
</style>
