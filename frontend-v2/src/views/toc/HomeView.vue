<template>
  <div>
    <!-- Hero -->
    <section class="hero">
      <div class="container">
        <div class="hero-badge rise">🤖 10 个智能体 · 全程可审计 · 状态可恢复</div>
        <h1 class="hero-title rise">把一场旅行，<br />交给一群<span class="grad">会吵架的智能体</span></h1>
        <p class="hero-sub rise">一句话说出你的需求，智能体流水线自动调研、规划、核算、互怼、验收，
          最终交付一本含<b>逐日行程 · 费用账本 · 决策辩论 · 翻车预演</b>的完整行程书。</p>

        <!-- 创建行程表单 -->
        <div class="create-card card rise" style="animation-delay:.1s">
          <form @submit.prevent="submit">
            <div class="grid">
              <div class="field">
                <label>目的地 *</label>
                <input v-model.trim="form.destination" class="input" placeholder="如：北京市" required maxlength="20" />
              </div>
              <div class="field">
                <label>出发地</label>
                <input v-model.trim="form.origin" class="input" placeholder="如：上海（不填不计大交通）" maxlength="20" />
              </div>
              <div class="field">
                <label>天数</label>
                <select v-model.number="form.days" class="select">
                  <option v-for="d in 14" :key="d" :value="d">{{ d }} 天</option>
                </select>
              </div>
              <div class="field">
                <label>预算（元）*</label>
                <input v-model.number="form.budget" type="number" class="input" min="0" step="100" required placeholder="8000" />
              </div>
              <div class="field">
                <label>出行人数</label>
                <select v-model.number="form.travelers" class="select">
                  <option v-for="t in 20" :key="t" :value="t">{{ t }} 人</option>
                </select>
              </div>
              <div class="field">
                <label>出发日期</label>
                <input v-model="form.departure_date" type="date" class="input" />
              </div>
            </div>

            <div class="field" style="margin-top:16px">
              <label>心情关键词 <span class="hint">填写后生成「心情剧本」章节</span></label>
              <div class="chip-group">
                <button type="button" v-for="m in MOODS" :key="m" class="chip" :class="{ active: form.mood.includes(m) }" @click="toggleMood(m)">{{ m }}</button>
              </div>
            </div>

            <div class="field" style="margin-top:14px">
              <label>偏好标签</label>
              <div class="chip-group">
                <button type="button" v-for="p in PREFS" :key="p" class="chip" :class="{ active: form.preferences.includes(p) }" @click="toggleList(form.preferences, p)">{{ p }}</button>
              </div>
            </div>

            <div class="field" style="margin-top:14px">
              <label>约束条件 <span class="hint">硬性要求，智能体必须遵守</span></label>
              <div class="chip-group">
                <button type="button" v-for="c in CONS" :key="c" class="chip" :class="{ active: form.constraints.includes(c) }" @click="toggleList(form.constraints, c)">{{ c }}</button>
              </div>
            </div>

            <div style="display:flex;align-items:center;gap:14px;margin-top:22px;flex-wrap:wrap">
              <button class="btn btn-primary btn-lg" :disabled="creating || !form.destination || form.budget === ''">
                <span v-if="creating" class="spinner" style="width:16px;height:16px;border-width:2.5px"></span>
                {{ creating ? '智能体集结中…' : '✦ 生成我的行程书' }}
              </button>
              <span class="hint-s">约 1-3 秒完成 · 超预算会挂起等你审批</span>
            </div>
          </form>
        </div>
      </div>
    </section>

    <!-- 问问 AI 导游（RAG 快捷入口） -->
    <section class="container sec" id="ask-rag">
      <div class="sec-title">问问 AI 导游</div>
      <p class="sec-desc">
        基于景点/线路知识库的问答：先向量检索 → 再 LLM 有据生成 → 距离过大则拒答（不编造）。
        <router-link :to="{ name: 'plan-detail', params: { jobId: 'demo' } }" style="font-size:12px; margin-left:6px">全程体验见「行程书 · AI 导游问答」</router-link>
      </p>

      <!-- 标品分类导航：点击填入并触发提问 -->
      <div class="cat-grid">
        <button v-for="c in PRODUCT_CATS" :key="c.key" type="button" class="cat-card"
                :style="{ '--cat-c': c.color }"
                @click="askByCategory(c)">
          <span class="cat-icon">{{ c.icon }}</span>
          <span class="cat-label">{{ c.label }}</span>
          <span class="cat-q">"{{ c.sample }}"</span>
        </button>
      </div>

      <div class="card rag-home-card">
        <RagPanel mode="sync" :show-mode="false" :reset-able="true"
                  hint="拙政园门票淡旺季分别多少？"
                  placeholder="例：拙政园门票、北京 3 天亲子行程怎么排、苏州雨天备选有哪些？" />
        <div class="rag-shortcuts">
          <span>试试：</span>
          <button v-for="q in RAG_QUICK" :key="q" type="button" class="chip chip-outline" @click="fillRag(q)">{{ q }}</button>
        </div>
      </div>
    </section>

    <!-- 智能体流水线 -->
    <section class="container sec">
      <div class="sec-title">智能体流水线</div>
      <p class="sec-desc">toC 全链路 10 节点：每一站都有独立职责，每个决策都有审计记录</p>
      <div class="agents-row">
        <div v-for="(a, i) in AGENTS" :key="a.name" class="agent-card card card-hover" :style="{ animationDelay: `${i * 0.05}s` }">
          <div class="agent-emoji">{{ a.emoji }}</div>
          <div class="agent-name">{{ a.name }}</div>
          <div class="agent-role">{{ a.role }}</div>
        </div>
      </div>
    </section>

    <!-- 行程书七章 -->
    <section class="container sec">
      <div class="sec-title">一册行程书 · 七章</div>
      <p class="sec-desc">不是一页冷冰冰的列表，而是一本可读、可查账、可回溯的旅行文档</p>
      <div class="chapters">
        <div v-for="(c, i) in CHAPTERS" :key="c.title" class="chapter card card-hover">
          <div class="ch-num">{{ String(i + 1).padStart(2, '0') }}</div>
          <div class="ch-title">{{ c.title }}</div>
          <p class="ch-desc">{{ c.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 特色体验 -->
    <section class="container sec">
      <div class="sec-title">不止规划，还有灵魂</div>
      <p class="sec-desc">围绕行程书的体验层：辩论直播、名导陪聊、虚拟游客踩点、反事实推演</p>
      <div class="features">
        <div v-for="f in FEATURES" :key="f.title" class="feature card card-hover">
          <div class="ft-emoji">{{ f.emoji }}</div>
          <div>
            <div class="ft-title">{{ f.title }}</div>
            <p class="ft-desc">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { plansApi } from '../../api'
import { toast } from '../../composables/toast'
import RagPanel from '../../components/RagPanel.vue'
import { PRODUCT_CATEGORIES } from '../../lib/productParser'

const router = useRouter()
const creating = ref(false)

const MOODS = ['治愈', '亲子', '文艺', '探险', '躺平', '怀旧']
const PREFS = ['亲子', '博物馆', '美食', '小众', '摄影', '夜生活', '自然风光', '历史古迹']
const CONS = ['不去人多的地方', '不吃辣', '需要无障碍', '带老人', '雨天备选', '晚上不安排']

const AGENTS = [
  { emoji: '📋', name: 'Intake', role: '需求受理与注入拦截' },
  { emoji: '🔍', name: 'Researcher', role: '目的地资料调研' },
  { emoji: '🧭', name: 'Planner', role: '路线骨架规划' },
  { emoji: '🗓', name: 'Itinerary', role: '逐日行程编排' },
  { emoji: '💰', name: 'Budget', role: '预算核算' },
  { emoji: '✅', name: 'Validator', role: '可行性验收' },
  { emoji: '舆情', name: 'Sentiment', role: '口碑与避坑扫描' },
  { emoji: '⚔️', name: 'Debate', role: '规划方 vs 游客方辩论' },
  { emoji: '🎭', name: 'Mood', role: '心情剧本生成' },
  { emoji: '📕', name: 'Reporter', role: '行程书成稿' },
]

const CHAPTERS = [
  { title: '总览摘要', desc: '需求逐条回放、住宿推荐与整体节奏一览' },
  { title: '逐日行程', desc: '按时间排序的景点动线、通勤方式与四餐推荐' },
  { title: '费用账本', desc: '门票、交通、住宿逐项核算，预算红线预警' },
  { title: '辩论实录', desc: '每个关键决策的正反双方观点与裁决理由' },
  { title: '心情剧本', desc: '把情绪需求翻译成具体场景的沉浸式剧本' },
  { title: '翻车预演', desc: 'B 计划：天气、排队、闭馆的应急预案' },
  { title: '出行清单', desc: '证件、装备、预约事项的出发前 checklist' },
]

const FEATURES = [
  { emoji: '🔴', title: '辩论直播', desc: 'SSE 实时观看规划方与游客方互怼，还能投票站队' },
  { emoji: '🎓', title: '名导团', desc: '杜甫、马可·波罗等虚拟名导点评行程，可追问细节' },
  { emoji: '👥', title: '虚拟游客踩点', desc: 'swarm 模拟不同人设提前"走"一遍行程并给反馈' },
  { emoji: '🔮', title: '反事实推演', desc: '如果当初选了另一条路线会怎样？后悔药对照卡' },
]

const RAG_QUICK = [
  '拙政园门票淡旺季分别多少？',
  '苏州适合雨天游览的景点有哪些？',
  '北京 3 天亲子行程预算 8000 怎么安排？',
  '故宫周边 500 米内酒店推荐',
]

// 6 大标品分类（与 productParser 一致），点击直接发起该类问题
const PRODUCT_CATS = PRODUCT_CATEGORIES.filter(c => c.key !== 'other').map(c => ({
  ...c,
  color: ({ sight: '#6366f1', food: '#f97316', hotel: '#0ea5e9', transit: '#22c55e', shop: '#ec4899', culture: '#a78bfa' })[c.key],
  sample: ({
    sight:  '推荐北京必去的 5 个国家级景点',
    food:    '北京最地道的烤鸭店在哪儿？',
    hotel:   '故宫周边 500 米内有性价比的酒店吗？',
    transit: '首都机场到国贸最快的交通方式？',
    shop:    '北京哪里买老字号伴手礼最全？',
    culture: '故宫的历史背景与必看典故',
  })[c.key],
}))

const form = reactive({
  destination: '', origin: '', days: 3, budget: 8000, travelers: 2,
  departure_date: '', mood: [], preferences: [], constraints: [],
})

function toggleMood(m) { toggleList(form.mood, m) }
function toggleList(list, v) {
  const i = list.indexOf(v)
  i >= 0 ? list.splice(i, 1) : list.push(v)
}
function fillRag(q) {
  // 直接找到 panel 内的 textarea 填入
  const ta = document.querySelector('.rag-home-card textarea')
  if (!ta) return
  // 用 vue 的 v-model 触发：构造一个 input event
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set
  setter.call(ta, q)
  ta.dispatchEvent(new Event('input', { bubbles: true }))
  ta.focus()
}

function askByCategory(c) {
  // 填入该分类示例问题并直接点提交按钮（绕过手动点击）
  fillRag(c.sample)
  const btn = document.querySelector('.rag-home-card .btn-primary')
  if (btn) setTimeout(() => btn.click(), 30)
}

async function submit() {
  if (!form.destination || form.budget === '' || form.budget == null) return
  creating.value = true
  try {
    const payload = {
      destination: form.destination,
      days: form.days,
      budget: Number(form.budget),
      travelers: form.travelers,
    }
    if (form.origin) payload.origin = form.origin
    if (form.departure_date) payload.departure_date = form.departure_date
    if (form.mood.length) payload.mood = form.mood.join(',')
    if (form.preferences.length) payload.preferences = form.preferences
    if (form.constraints.length) payload.constraints = form.constraints

    const r = await plansApi.create(payload)
    toast('任务已创建，智能体开工！', 'ok')
    router.push({ name: 'plan-detail', params: { jobId: r.job_id } })
  } catch (e) {
    toast(`创建失败：${e.message}`, 'err')
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.hero {
  padding: 72px 0 56px;
  background:
    radial-gradient(700px 320px at 78% 8%, rgba(245,158,11,.10), transparent 60%),
    radial-gradient(900px 420px at 12% -5%, rgba(37,99,235,.09), transparent 55%);
}
.hero-badge {
  display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600;
  color: var(--brand-700); background: var(--brand-50); border: 1px solid var(--brand-200);
  padding: 7px 16px; border-radius: 999px; margin-bottom: 22px;
}
.hero-title { font-size: clamp(34px, 5.4vw, 54px); font-weight: 900; line-height: 1.22; letter-spacing: -.03em; color: var(--ink-900); }
.hero-title .grad {
  background: linear-gradient(100deg, var(--brand-600), var(--accent-500));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { margin: 18px 0 34px; font-size: 16.5px; color: var(--ink-500); max-width: 640px; }
.hero-sub b { color: var(--ink-900); }

.create-card { padding: 28px 30px; max-width: 880px; box-shadow: var(--shadow-md); }
.create-card .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px 16px; }
.hint-s { font-size: 13px; color: var(--ink-400); }

.sec { margin-top: 72px; }
.agents-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 13px; }
.agent-card { padding: 18px 15px; text-align: center; animation: rise .5s var(--ease) both; }
.agent-emoji { font-size: 26px; margin-bottom: 8px; }
.agent-name { font-weight: 800; font-size: 14.5px; color: var(--ink-900); }
.agent-role { font-size: 12px; color: var(--ink-500); margin-top: 4px; line-height: 1.5; }

.chapters { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; }
.chapter { padding: 22px 24px; position: relative; overflow: hidden; }
.ch-num { font-size: 40px; font-weight: 900; color: var(--brand-100); position: absolute; right: 16px; top: 6px; letter-spacing: -.04em; }
.ch-title { font-weight: 800; font-size: 16px; color: var(--ink-900); margin-bottom: 6px; }
.ch-desc { font-size: 13px; color: var(--ink-500); line-height: 1.7; }

.features { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.feature { padding: 22px 24px; display: flex; gap: 16px; }
.ft-emoji { font-size: 30px; flex: none; }
.ft-title { font-weight: 800; font-size: 15.5px; color: var(--ink-900); }
.ft-desc { font-size: 13.5px; color: var(--ink-500); margin-top: 5px; line-height: 1.7; }

.cat-grid {
  display: grid; grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px; margin-bottom: 16px;
}
.cat-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: #fff; border: 1px solid var(--line, #e5e7eb); border-radius: 12px;
  padding: 16px 8px; cursor: pointer; transition: all .2s;
  border-top: 3px solid var(--cat-c, var(--brand-500));
  text-align: center;
}
.cat-card:hover {
  transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,.06);
  background: color-mix(in srgb, var(--cat-c) 5%, #fff);
}
.cat-icon { font-size: 28px; margin-bottom: 4px; }
.cat-label { font-weight: 700; font-size: 14px; color: var(--ink-900); }
.cat-q { font-size: 11.5px; color: var(--ink-500); margin-top: 4px; line-height: 1.4; }
@media (max-width: 900px) {
  .cat-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 540px) {
  .cat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* RAG 快捷问答卡 */
.rag-home-card { padding: 22px 24px; max-width: 920px; }
.rag-shortcuts { margin-top: 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; color: var(--ink-500); }
.rag-shortcuts .chip-outline {
  background: transparent; border: 1px solid var(--brand-200); color: var(--brand-700);
  padding: 4px 12px; border-radius: 999px; font-size: 12.5px; cursor: pointer; transition: all .15s;
}
.rag-shortcuts .chip-outline:hover { background: var(--brand-50); border-color: var(--brand-500); }
</style>
