<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { AGENT_FLOW } from './mock.js'
import { plansApi } from '../../api/index.js'

const router = useRouter()

const plan = reactive({
  origin: '', destination: '', days: 3, budget: 8000,
  date: '', dateReturn: '',
  group: '', interests: [], rhythm: '', sleep: '', note: '',
})
const prefsOpen = ref(false)
const creating = ref(false)
const today = new Date().toISOString().slice(0, 10)

const ORIGIN_CITIES = ['上海', '南京', '杭州', '北京', '苏州', '无锡', '常州', '合肥', '武汉', '广州', '深圳', '成都', '西安', '天津']

const POINTS = [
  { emoji: '🗓', t: '逐日动线', d: '想去哪、玩几天、花多少，说清就开工' },
  { emoji: '📦', t: '素材来自标品库', d: '只用企业已核验的景点、餐饮、住宿素材，不瞎编' },
  { emoji: '✅', t: '可转方案上架', d: '排得好的行程，企业可一键沉淀为可售线路方案' },
  { emoji: '✏️', t: '随时可改', d: '时间、节奏、酒店，喜欢哪页改哪页' },
]

const GROUPS = ['独自旅行', '情侣同行', '亲子同行', '长辈同行', '朋友结伴']
const INTERESTS = ['美食探店', '人文历史', '博物馆艺术', '自然风光', '城市漫步', '亲子同乐', '摄影出片', '夜生活']
const RHYTHMS = ['松弛一点，慢慢逛', '节奏适中就行', '特种兵拉练']
const SLEEPS = ['每天早点出发', '睡到自然醒']

function pickOne(key, value) { plan[key] = plan[key] === value ? '' : value }
function toggleInterest(label) {
  const i = plan.interests.indexOf(label)
  i >= 0 ? plan.interests.splice(i, 1) : plan.interests.push(label)
}

const dateRangeText = computed(() => {
  if (!plan.date) return ''
  const zh = (d) => `${Number(d.slice(5, 7))}月${Number(d.slice(8, 10))}日`
  return plan.dateReturn && plan.dateReturn !== plan.date
    ? `${zh(plan.date)} — ${zh(plan.dateReturn)}`
    : zh(plan.date)
})

// 出发日 ↔ 天数联动
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

// 偏好收起态摘要
const prefsMeta = computed(() => {
  const items = [plan.group, ...plan.interests, plan.rhythm, plan.sleep]
  if (plan.note) items.push('备注要求')
  const dirty = items.length > 0
  return {
    dirty,
    text: dirty
      ? `已选 ${items.slice(0, 3).join('、')}${items.length > 3 ? ` 等 ${items.length} 项` : ''}`
      : '选填 · 全不选也能直接生成',
  }
})

// 提交：POST /api/plans 创建任务 → 跳转到规划中的任务详情（失败时给出错误提示）
const errMsg = ref('')
async function onPlanSubmit() {
  if (!plan.destination || creating.value) return
  creating.value = true
  errMsg.value = ''
  // 「和谁一起去」→ 出行人数映射（后端 travelers 用于预算分项换算）
  const PEOPLE_MAP = { '独自旅行': 1, '情侣同行': 2, '亲子同行': 3, '长辈同行': 3, '朋友结伴': 4 }
  const constraints = [plan.rhythm, plan.sleep, plan.note].filter(Boolean)
  try {
    const res = await plansApi.create({
      destination: plan.destination,
      days: plan.days,
      budget: Number(plan.budget) || 0,
      travelers: PEOPLE_MAP[plan.group] || 2,
      origin: plan.origin || undefined,
      departure_date: plan.date || undefined,
      return_date: plan.dateReturn || undefined,
      preferences: [...plan.interests],
      constraints,
    })
    router.push(`/plan/${res.job_id}`)
  } catch (e) {
    errMsg.value = e.message || '创建任务失败,请稍后再试'
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="planner">
    <div class="container-wide">

      <header class="page-head">
        <div>
          <span class="eyebrow">✦ 平台主功能 · AI 行程规划</span>
          <h1 class="page-title">没有现成方案？<br />说句话，现场给你排一本。</h1>
          <p class="page-sub">
            10 个智能体协作：调研目的地 → 排逐日动线 → 测预算 → 合规校验 → 双辩博弈 → 节奏调优，
            约 1-3 分钟生成一份可编辑、可下单的行程书。
          </p>
        </div>
      </header>

      <!-- 主体：左卖点 + 右表单 -->
      <section class="plan-card card">
        <div class="plan-copy">
          <ul class="points">
            <li v-for="p in POINTS" :key="p.t" class="point">
              <span class="pt-ico">{{ p.emoji }}</span>
              <div>
                <b>{{ p.t }}</b>
                <p>{{ p.d }}</p>
              </div>
            </li>
          </ul>

          <!-- 10-Agent 流水线预览 -->
          <div class="agent-strip">
            <div class="as-title">生成过程中，10 个智能体将接力完成：</div>
            <div class="as-flow">
              <span v-for="(a, i) in AGENT_FLOW" :key="a.key" class="as-node">
                <i class="as-dot">{{ i + 1 }}</i>{{ a.label }}
              </span>
            </div>
          </div>
        </div>

        <form class="plan-form" @submit.prevent="onPlanSubmit">
          <div class="pf-field">
            <label>出发地 <b>*</b></label>
            <input v-model.trim="plan.origin" class="input" required placeholder="如：上海 / 南京（用于大交通规划）" maxlength="20" list="origin-list" />
            <datalist id="origin-list">
              <option v-for="c in ORIGIN_CITIES" :key="c" :value="c" />
            </datalist>
          </div>

          <div class="pf-field">
            <label>目的地 <b>*</b></label>
            <input v-model.trim="plan.destination" class="input" required placeholder="如：苏州 / 北京 / 杭州" maxlength="20" />
          </div>

          <div class="pf-grid">
            <div class="pf-field">
              <label>天数</label>
              <select v-model.number="plan.days" class="input" @change="fixReturn">
                <option v-for="d in 14" :key="d" :value="d">{{ d }} 天</option>
              </select>
            </div>
            <div class="pf-field">
              <label>预算（元）</label>
              <input v-model.number="plan.budget" class="input" type="number" min="0" step="100" placeholder="8000" />
            </div>
            <div class="pf-field">
              <label>出行日期</label>
              <div class="date-pair">
                <input v-model="plan.date" class="input" type="date" :min="today" @change="fixReturn" />
                <input v-model="plan.dateReturn" class="input" type="date" :min="plan.date || today" title="返程日期" />
              </div>
              <p v-if="dateRangeText" class="date-hint">{{ dateRangeText }} · 共 {{ plan.days }} 天</p>
            </div>
          </div>

          <!-- 偏好设置（可收纳） -->
          <div class="pf-prefs">
            <button type="button" class="prefs-head" :aria-expanded="prefsOpen" @click="prefsOpen = !prefsOpen">
              <span class="prefs-title">偏好设置</span>
              <span class="prefs-summary" :class="{ set: prefsMeta.dirty }">{{ prefsMeta.text }}</span>
              <svg class="prefs-chev" :class="{ open: prefsOpen }" width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            <div v-show="prefsOpen" class="prefs-body">
              <div class="pf-field">
                <label>和谁一起去</label>
                <div class="chip-group">
                  <button v-for="g in GROUPS" :key="g" type="button" class="chip" :class="{ on: plan.group === g }" @click="pickOne('group', g)">{{ g }}</button>
                </div>
              </div>
              <div class="pf-field">
                <label>想玩什么 <span class="opt-hint">可多选</span></label>
                <div class="chip-group">
                  <button v-for="it in INTERESTS" :key="it" type="button" class="chip" :class="{ on: plan.interests.includes(it) }" @click="toggleInterest(it)">{{ it }}</button>
                </div>
              </div>
              <div class="pf-field">
                <label>行程节奏</label>
                <div class="chip-group">
                  <button v-for="r in RHYTHMS" :key="r" type="button" class="chip" :class="{ on: plan.rhythm === r }" @click="pickOne('rhythm', r)">{{ r }}</button>
                </div>
              </div>
              <div class="pf-field">
                <label>作息习惯</label>
                <div class="chip-group">
                  <button v-for="s in SLEEPS" :key="s" type="button" class="chip" :class="{ on: plan.sleep === s }" @click="pickOne('sleep', s)">{{ s }}</button>
                </div>
              </div>
              <div class="pf-field">
                <label>其它要求 <span class="opt-hint">预算分配 / 忌口等</span></label>
                <input v-model.trim="plan.note" class="input" maxlength="60" placeholder="如：当地美食与中餐结合 · 人均预算 1 万" />
              </div>
            </div>
          </div>

          <div class="pf-actions">
            <RouterLink to="/manual" class="btn btn-ghost manual-btn">🧩 手动组装行程书</RouterLink>
            <button type="submit" class="btn btn-primary btn-lg submit-btn" :disabled="creating || !plan.destination">
              <span v-if="creating" class="spinner"></span>
              {{ creating ? '正在创建任务…' : '✦ 开始规划我的行程' }}
            </button>
          </div>
          <p v-if="errMsg" class="pf-tip pf-err">⚠ {{ errMsg }}</p>
          <p class="pf-tip">约 1-3 分钟生成 · 生成后随时可改 · 可提交企业沉淀为线路方案</p>
        </form>
      </section>

    </div>
  </div>
</template>

<style scoped>
.planner { padding: var(--s-7) 0 var(--s-9); display: flex; flex-direction: column; gap: var(--s-6); }

.page-head { max-width: 720px; }
.page-title { font-size: var(--fs-3xl); font-weight: var(--fw-bold); letter-spacing: -0.02em; margin-top: var(--s-3); line-height: 1.2; }
.page-sub { color: var(--text-2); margin-top: var(--s-3); font-size: var(--fs-sm); line-height: var(--lh-loose); }

/* 主体卡 */
.plan-card {
  display: grid; grid-template-columns: 1.05fr .95fr; gap: var(--s-8);
  padding: var(--s-7); border-top: 3px solid var(--accent);
}

/* 左侧卖点 */
.points { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--s-4); }
.point { display: flex; gap: var(--s-3); align-items: flex-start; }
.pt-ico {
  width: 38px; height: 38px; flex: none; border-radius: var(--r);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; background: var(--accent-soft); border: 1px solid var(--border-soft);
}
.point b { font-size: var(--fs-sm); font-weight: var(--fw-semi); }
.point p { font-size: var(--fs-xs); color: var(--text-3); margin: 2px 0 0; line-height: 1.5; }

.agent-strip { margin-top: var(--s-6); padding-top: var(--s-5); border-top: 1px dashed var(--border-soft); }
.as-title { font-size: var(--fs-xs); font-weight: var(--fw-medium); color: var(--text-3); margin-bottom: var(--s-3); }
.as-flow { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.as-node {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: var(--fs-xs); color: var(--text-2); font-weight: var(--fw-medium);
  background: var(--surface); border: 1px solid var(--border-soft);
  padding: 4px var(--s-3); border-radius: var(--r-pill);
}
.as-dot {
  font-style: normal; width: 16px; height: 16px; border-radius: 50%;
  background: var(--accent); color: #fff; font-size: 10px; font-weight: var(--fw-bold);
  display: inline-flex; align-items: center; justify-content: center;
}

/* 右侧表单 */
.plan-form {
  display: flex; flex-direction: column; gap: var(--s-3);
  background: linear-gradient(180deg, var(--bg-soft), var(--surface));
  border: 1px solid var(--border-soft); border-radius: var(--r-md); padding: var(--s-6);
}
.pf-field { display: flex; flex-direction: column; gap: 6px; }
.pf-field label { font-size: var(--fs-xs); font-weight: var(--fw-semi); color: var(--text-2); }
.pf-field label b { color: var(--danger); }
.input {
  height: 42px; padding: 0 var(--s-3);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r); font-size: var(--fs-sm); color: var(--text);
  transition: border-color var(--dur-1) var(--ease), box-shadow var(--dur-1) var(--ease);
}
.input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.pf-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-3); }
.date-pair { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.date-hint { font-size: 11px; color: var(--text-faint); margin: 0; }

/* 偏好折叠 */
.pf-prefs { border-top: 1px dashed var(--border-soft); padding-top: var(--s-3); }
.prefs-head {
  all: unset; box-sizing: border-box; display: flex; align-items: center; gap: var(--s-2);
  width: 100%; cursor: pointer;
}
.prefs-head:hover .prefs-title { color: var(--accent); }
.prefs-title { font-size: var(--fs-xs); font-weight: var(--fw-semi); white-space: nowrap; }
.prefs-summary {
  flex: 1; min-width: 0; font-size: 11px; color: var(--text-faint);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: left;
}
.prefs-summary.set { color: var(--accent); }
.prefs-chev { flex: none; color: var(--text-faint); transition: transform .25s ease; }
.prefs-chev.open { transform: rotate(180deg); }
.prefs-body { display: flex; flex-direction: column; gap: var(--s-3); padding-top: var(--s-3); }
.opt-hint { font-weight: var(--fw-normal); color: var(--text-faint); font-size: 11px; }

.chip-group { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  padding: 5px var(--s-3); border-radius: var(--r-pill);
  background: var(--surface); border: 1px solid var(--border);
  font-size: var(--fs-xs); color: var(--text-2); cursor: pointer;
  transition: all var(--dur-1) var(--ease);
}
.chip:hover { border-color: var(--accent); color: var(--accent); }
.chip.on { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: var(--fw-medium); }

/* 动作 */
.pf-actions { display: flex; gap: var(--s-3); margin-top: var(--s-1); }
.manual-btn { flex: none; }
.submit-btn { flex: 1; }
.spinner {
  width: 16px; height: 16px; border-radius: 50%;
  border: 2.5px solid rgba(255,255,255,.35); border-top-color: #fff;
  animation: spin .8s linear infinite; display: inline-block; margin-right: 6px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.pf-tip { font-size: 11px; color: var(--text-faint); text-align: center; margin: 0; }
.pf-err { color: #B0685C; font-weight: var(--fw-medium); }

@media (max-width: 900px) {
  .plan-card { grid-template-columns: 1fr; gap: var(--s-6); padding: var(--s-5); }
  .pf-grid { grid-template-columns: 1fr; }
  .pf-actions { flex-direction: column; }
}
</style>
