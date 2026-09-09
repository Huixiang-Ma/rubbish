<template>
  <div class="tde">
    <!-- 自包含进度：①逐日编排 → ②确认保存 -->
    <div class="tde-top">
      <div class="tde-prog">
        <span :class="{ on: stage === 1 }">① 逐日编排</span>
        <i>→</i>
        <span :class="{ on: stage === 2 }">② 确认保存</span>
      </div>
      <div class="tde-chip" v-if="ready">
        <span v-if="isEdit">✏️ 正在编辑已有行程书</span>
        <span v-else>✦ 基于模板 {{ draft.template?.title || '' }}</span>
        <em v-if="seedProduct && !isEdit">· 已预置 {{ seedProduct.cover?.emoji }} {{ seedProduct.name }}</em>
      </div>
    </div>

    <!-- 装载中（新建路径需先拉标品目录） -->
    <div v-if="!ready" class="loading-block"><div class="spinner spin"></div>正在装载标品库并排期…</div>

    <!-- ============ Stage 1 逐日编排 ============ -->
    <template v-else-if="stage === 1">
      <div class="edit-head card">
        <div class="eh-info">
          <div class="eh-title">{{ coverEmoji }} {{ draft.meta.title || (draft.template ? draft.template.title + (isEdit ? '' : '（微调版）') : '行程') }}</div>
          <div class="eh-sub">{{ draft.city }} · {{ draft.days.length }} 天 · 共 {{ blockCount }} 个停留
            <span class="eh-tag">模板参考 ¥{{ fmt(baseTotal) }}</span>
            <span v-if="delta !== 0" class="eh-delta" :class="delta > 0 ? 'up' : 'down'">{{ delta > 0 ? '+' : '−' }}{{ fmt(Math.abs(delta)) }}</span>
            <span class="eh-tag eh-live">当前约 ¥{{ fmt(totalCost) }}</span>
          </div>
        </div>
        <div class="eh-actions">
          <button class="btn btn-soft btn-sm" @click="$emit('cancelled')">{{ isEdit ? '← 返回行程书' : '← 换模板' }}</button>
          <button class="btn btn-primary btn-sm" :disabled="!draft.days.length" @click="goStage(2)">编排完成，下一步 →</button>
        </div>
      </div>

      <!-- 模板商品一个都没匹配上 -->
      <div v-if="!draft.days.length" class="empty card big">
        <div class="icon">🧩</div>
        <p>模板中的标品没有匹配到当前标品库，暂时无法编排</p>
        <div class="act">
          <router-link :to="{ name: 'malls' }" class="btn btn-primary">去标品商城看看</router-link>
          <button class="btn btn-soft" @click="$emit('cancelled')">返回重选</button>
        </div>
      </div>

      <div v-else class="edit-layout">
        <!-- 左：天切换 -->
        <aside class="day-nav card">
          <div class="dn-title">行程天</div>
          <button v-for="d in draft.days" :key="d.day" class="day-pill" :class="{ on: dayIdx === d.day - 1 }"
                  @click="dayIdx = d.day - 1">
            <b>第 {{ d.day }} 天</b>
            <small>{{ stopCountOf(d) }} 个停留</small>
          </button>
          <div class="dn-tip">点击任一行时段可换标品；住宿默认排在每天最后（夜宿）。</div>
        </aside>

        <!-- 中：时间轴 -->
        <section class="day-main card">
          <div class="dm-head">
            <div>
              <div class="dm-title">第 {{ dayIdx + 1 }} 天</div>
              <div class="dm-sub">{{ dayTitle(dayIdx) }}</div>
            </div>
            <button class="btn btn-soft btn-sm" @click="openAdd">＋ 加一个停留</button>
          </div>

          <div class="timeline">
            <div v-for="(b, bi) in draft.days[dayIdx].blocks" :key="b.key" class="tl-row">
              <div class="tl-time">
                <span class="t-start">{{ b.start }}</span>
                <span class="t-period">{{ periodLabel(b.period) }}</span>
              </div>
              <div class="tl-line"><i class="tl-dot" :style="{ background: catColor(b.product.category) }"></i></div>
              <div class="tl-body" @click="openSwap(b)">
                <div class="tl-card">
                  <span class="tl-emoji" :style="{ background: b.product.cover?.gradient || 'linear-gradient(135deg,#E2E8F0,#94A3B8)' }">{{ b.product.cover?.emoji || "📍" }}</span>
                  <div class="tl-info">
                    <div class="tl-name">
                      {{ b.product.name }}
                      <span v-if="b.tag" class="tl-tag">{{ b.tag }}</span>
                    </div>
                    <div class="tl-meta">
                      <span class="cat-tag" :style="{ color: catColor(b.product.category) }">{{ b.product.category }}</span>
                      <span v-for="t in (b.product.tags || []).slice(0, 2)" :key="t" class="tl-tags">{{ t }}</span>
                      <span v-if="b.product.level && b.product.level !== '-'" class="tl-level">{{ b.product.level }}</span>
                    </div>
                  </div>
                  <div class="tl-right">
                    <div class="tl-price">{{ priceText(b.product) }}</div>
                    <div class="tl-ops">
                      <button class="op" title="换一个" @click.stop="openSwap(b)">⇄ 换</button>
                      <button class="op danger" title="移除" @click.stop="removeBlock(bi)">✕</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="!draft.days[dayIdx].blocks.length" class="empty mini"><div class="icon">🗓</div><p>这一天还没有安排，点右上角加一个停留</p></div>
        </section>
      </div>
    </template>

    <!-- ============ Stage 2 确认保存 ============ -->
    <template v-else>
      <div class="confirm-grid">
        <div class="card card-pad form-card">
          <div class="c-title">📝 行程书信息</div>
          <div class="field"><label>行程名称 *</label>
            <input v-model.trim="draft.meta.title" class="input" placeholder="例如：和爸妈的苏州园林慢游" /></div>
          <div class="row2">
            <div class="field"><label>出行人数</label>
              <select v-model.number="draft.meta.travelers" class="select">
                <option v-for="n in [1, 2, 3, 4, 5, 6]" :key="n" :value="n">{{ n }} 人</option>
              </select></div>
            <div class="field"><label>预算参考（¥/人）</label>
              <input v-model.number="draft.meta.budget" type="number" min="0" class="input" placeholder="不填则按模板参考价" /></div>
          </div>
          <div class="row2">
            <div class="field"><label>出发日期</label>
              <input v-model="draft.meta.start_date" type="date" class="input" /></div>
            <div class="field"><label>适合谁</label>
              <select v-model="draft.meta.audience" class="select">
                <option value="">默认（模板推荐）</option>
                <option v-for="a in ['亲子家庭', '情侣', '银发爸妈', '朋友结伴', '独自旅行', '商旅轻游']" :key="a" :value="a">{{ a }}</option>
              </select></div>
          </div>
          <div class="field"><label>备注（可选）</label>
            <textarea v-model.trim="draft.meta.note" class="input" rows="2" placeholder="口味偏好 / 出行节奏 / 特殊需求…"></textarea></div>
          <div class="form-err" v-if="!draft.meta.title">请先给行程书起个名字</div>

          <!-- 校验结果：warn 提示 / error 阻塞 -->
          <div v-if="issues.length" class="issue-box" :class="{ bad: errCount > 0 }">
            <div class="issue-tt">
              <b v-if="errCount">⚠️ 有 {{ errCount }} 个问题需要处理后才能保存</b>
              <b v-else>💡 保存前请留意以下建议（不阻塞）</b>
              <router-link v-if="errCount" :to="{ name: 'malls' }" class="link-more">去商城找补 →</router-link>
            </div>
            <ul>
              <li v-for="(it, i) in issues" :key="i" :class="it.level">
                <i v-if="it.level === 'error'">✕</i><i v-else>!</i>{{ it.text }}
              </li>
            </ul>
          </div>
          <div v-else class="issue-ok">✅ 校验通过 —— 标题、住宿与时段均无异常，可以保存了。</div>
        </div>

        <div class="card card-pad sum-card">
          <div class="c-title">📊 行程概览</div>
          <div class="sum-hero" :style="{ background: (curTemplate.cover && curTemplate.cover.gradient) || 'linear-gradient(135deg,#60A5FA,#8B5CF6)' }">
            <span class="sh-emoji">{{ coverEmoji }}</span>
            <b>{{ draft.meta.title || '未命名行程' }}</b>
            <p>{{ draft.city }} · {{ draft.days.length }} 天{{ draft.meta.travelers ? ' · ' + draft.meta.travelers + ' 人' : '' }}</p>
          </div>
          <div class="sum-rows">
            <div class="sr"><span>停留总数</span><b>{{ blockCount }} 个</b></div>
            <div class="sr"><span>覆盖标品</span><b>{{ coveredCats }} 类</b></div>
            <div class="sr"><span>模板参考价</span><b>¥{{ fmt(baseTotal) }}</b></div>
            <div class="sr"><span>调整浮动</span><b :class="delta > 0 ? 'up' : delta < 0 ? 'down' : ''">{{ delta > 0 ? '+' : '' }}{{ delta < 0 ? '−' : '' }}{{ fmt(Math.abs(delta)) }}</b></div>
            <div class="sr total"><span>预计花费</span><b>¥{{ fmt(totalCost) }}</b></div>
          </div>
          <div class="sum-note">价格为模板参考 / 标品“起价”的粗算，仅供预算规划，最终以 SKU 实际结算为准。</div>
        </div>
      </div>

      <div class="confirm-actions">
        <button class="btn btn-ghost" @click="goStage(1)">← 返回编排</button>
        <button class="btn btn-primary btn-lg" :disabled="!canSave" @click="doSave">
          {{ isEdit ? '💾 保存修改' : '💾 保存为我的行程书' }}
        </button>
      </div>
    </template>

    <!-- ============ 换品 / 加品 抽屉 ============ -->
    <div v-if="picker.show" class="overlay" @click.self="picker.show = false">
      <div class="sheet">
        <div class="sh-head">
          <div>
            <b>{{ picker.mode === 'swap' ? '⇄ 换一个标品' : '＋ 添加一个停留' }}</b>
            <p v-if="picker.cur">{{ picker.cur.product.name }} · 当前时段：{{ periodLabel(picker.cur.period) }} {{ picker.cur.start }}</p>
            <p v-else>先从下方选择类型，再从库中挑选</p>
          </div>
          <button class="btn btn-ghost btn-sm" @click="picker.show = false">✕ 关闭</button>
        </div>

        <div class="sh-tabs">
          <button v-for="c in CATS" :key="c.name" class="chip" :class="{ active: picker.cat === c.name }"
                  @click="picker.cat = c.name">{{ c.emoji }} {{ c.name }}</button>
        </div>

        <div class="sh-list">
          <div v-if="!pickerOptions.length" class="empty mini"><div class="icon">🔍</div>
            <p>同城暂无其他「{{ picker.cat }}」标品</p>
            <router-link :to="{ name: 'malls-search', query: { q: picker.cat } }" class="btn btn-soft btn-sm" @click="picker.show = false">去商城搜索 →</router-link>
          </div>
          <div v-for="p in pickerOptions" :key="p.id" class="opt card card-hover"
               :class="{ cur: picker.cur && picker.cur.product.id === p.id }"
               @click="pick(p)">
            <span class="opt-emoji" :style="{ background: p.cover?.gradient || 'linear-gradient(135deg,#E2E8F0,#94A3B8)' }">{{ p.cover?.emoji || "📍" }}</span>
            <div class="opt-info">
              <div class="opt-name">{{ p.name }}<span v-if="picker.cur && picker.cur.product.id === p.id" class="opt-cur">使用中</span></div>
              <div class="opt-meta">{{ p.category }} · {{ p.city }} · ★ {{ p.rating.toFixed(1) }} · 售 {{ fmtSales(p.sales) }}</div>
              <div class="opt-tags"><span v-for="t in (p.tags || []).slice(0, 3)" :key="t">{{ t }}</span></div>
            </div>
            <div class="opt-price">
              <div>{{ priceText(p) }}</div>
              <div v-if="picker.cur && picker.cur.product.id !== p.id" class="opt-diff" :class="(p.price_min || 0) - (picker.cur.product.price_min || 0) > 0 ? 'up' : 'down'">
                {{ diffText(p, picker.cur.product) }}
              </div>
            </div>
          </div>
        </div>
        <div class="sh-foot">选中即替换当前时段，价格浮动会实时计入概览；住宿换白天品会自动挪到晚间，避免时间倒挂。</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useTripDraft, CATS } from '../composables/tripDraft'
import { toast } from '../composables/toast'

const props = defineProps({
  /** 新建：模板对象 */
  template: { type: Object, default: null },
  /** 编辑：已保存行程书（优先于 template） */
  trip: { type: Object, default: null },
  /** 新建：预置种子标品 */
  seed: { type: Object, default: null },
})
const emit = defineEmits(['saved', 'cancelled'])

const D = useTripDraft()
const { draft, picker, dayIdx, stage, ready, isEdit, seedProduct } = D

const baseTotal = D.baseTotal
const delta = D.delta
const blockCount = D.blockCount
const coveredCats = D.coveredCats
const totalCost = D.totalCost
const issues = D.issues
const errCount = D.errCount
const canSave = D.canSave
const pickerOptions = D.pickerOptions
const curTemplate = D.curTemplate

const coverEmoji = computed(() => {
  const cv = curTemplate.value && curTemplate.value.cover
  return (cv && cv.emoji) || '🧩'
})

function goStage(n) { D.goStage(n) }
function openSwap(b) { D.openSwap(b) }
function openAdd() { D.openAdd() }
function pick(p) { D.pick(p) }
function removeBlock(bi) { D.removeBlock(bi) }
function stopCountOf(d) { return D.stopCountOf(d) }
function dayTitle(i) { return D.dayTitle(i) }
function fmt(n) { return D.fmt(n) }
function fmtSales(n) { return D.fmtSales(n) }
function periodLabel(k) { return D.periodLabel(k) }
function catColor(c) { return D.catColor(c) }
function priceText(p) { return D.priceText(p) }
function diffText(n, o) { return D.diffText(n, o) }

function doSave() {
  if (!canSave.value) {
    if (!draft.meta.title) toast('请先填写行程名称', 'err')
    else if (D.errCount.value) toast(`仍有 ${D.errCount.value} 个校验问题未处理`, 'err')
    return
  }
  const trip = D.saveTrip()
  toast(isEdit.value ? '行程书已更新' : '行程书已保存', 'ok')
  emit('saved', trip)
}

onMounted(async () => {
  if (props.trip) {
    D.openEdit(props.trip)
  } else if (props.template) {
    await D.openCreate(props.template, props.seed)
  } else {
    // 手动行程规划：草稿已由 ManualComposerView.applyComposerResult 装配，保持共享单例即可
    ready.value = true
  }
})
</script>

<style scoped>
.tde { width: 100%; }
.loading-block { padding: 80px 0; text-align: center; color: var(--ink-400); }
.act { display: flex; gap: 10px; justify-content: center; margin-top: 18px; }
.empty.mini { padding: 34px 10px; text-align: center; }
.empty.big { padding: 80px 20px; text-align: center; }

/* 顶部进度 */
.tde-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.tde-prog { display: flex; align-items: center; gap: 10px; }
.tde-prog span { font-size: 13px; font-weight: 700; color: var(--ink-400); padding: 5px 14px; border-radius: 999px; background: var(--ink-100); }
.tde-prog span.on { background: var(--brand-600); color: #fff; }
.tde-prog i { color: var(--ink-300); font-style: normal; }
.tde-chip { font-size: 12.5px; color: var(--ink-500); }
.tde-chip em { color: var(--accent-600); font-style: normal; font-weight: 600; }

/* stage1 顶条 */
.edit-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; padding: 16px 22px; margin-bottom: 16px; }
.eh-title { font-size: 17px; font-weight: 800; color: var(--ink-900); }
.eh-sub { font-size: 13px; color: var(--ink-500); margin-top: 5px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.eh-tag { background: var(--ink-100); padding: 2px 10px; border-radius: 999px; font-size: 12px; color: var(--ink-600); }
.eh-tag.eh-live { background: var(--brand-50); color: var(--brand-700); font-weight: 700; }
.eh-delta { font-weight: 800; font-size: 13px; }
.eh-delta.up { color: var(--danger); }
.eh-delta.down { color: var(--ok); }
.eh-actions { display: flex; gap: 8px; }

.edit-layout { display: grid; grid-template-columns: 190px 1fr; gap: 16px; align-items: start; }
.day-nav { padding: 16px 14px; position: sticky; top: 84px; }
.dn-title { font-size: 12px; color: var(--ink-400); font-weight: 700; margin-bottom: 10px; letter-spacing: .06em; }
.day-pill { display: block; width: 100%; text-align: left; padding: 10px 12px; border-radius: 10px; border: 1px solid transparent; background: transparent; cursor: pointer; margin-bottom: 6px; }
.day-pill:hover { background: var(--ink-50); }
.day-pill.on { background: var(--brand-50); border-color: var(--brand-200); }
.day-pill b { display: block; font-size: 14px; color: var(--ink-900); }
.day-pill small { font-size: 11.5px; color: var(--ink-400); }
.dn-tip { font-size: 11.5px; color: var(--ink-400); margin-top: 10px; padding: 8px; background: var(--ink-50); border-radius: 8px; line-height: 1.6; }

.day-main { padding: 18px 22px; }
.dm-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.dm-title { font-size: 20px; font-weight: 900; color: var(--ink-900); }
.dm-sub { font-size: 13px; color: var(--ink-500); margin-top: 3px; }

.timeline { margin-top: 14px; }
.tl-row { display: grid; grid-template-columns: 74px 24px 1fr; gap: 4px; }
.tl-time { padding-top: 8px; text-align: right; display: flex; flex-direction: column; align-items: flex-end; }
.t-start { font-family: var(--mono); font-size: 13px; font-weight: 700; color: var(--ink-700); }
.t-period { font-size: 11px; color: var(--ink-400); }
.tl-line { position: relative; display: flex; justify-content: center; }
.tl-line::after { content: ''; position: absolute; top: 18px; bottom: -6px; width: 2px; background: var(--ink-200); }
.tl-row:last-child .tl-line::after { display: none; }
.tl-dot { width: 13px; height: 13px; border-radius: 50%; margin-top: 14px; background: var(--ink-300); border: 3px solid #fff; box-shadow: 0 0 0 1.5px var(--ink-300); z-index: 1; }
.tl-body { padding: 4px 0 4px 2px; }
.tl-card { display: grid; grid-template-columns: 46px 1fr auto; gap: 12px; align-items: center; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--ink-200); background: #fff; cursor: pointer; transition: all .14s; }
.tl-card:hover { border-color: var(--brand-400); box-shadow: var(--shadow-sm); }
.tl-emoji { width: 46px; height: 46px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
.tl-name { font-weight: 700; font-size: 14.5px; color: var(--ink-900); display: flex; align-items: center; gap: 8px; }
.tl-tag { font-size: 11px; background: var(--brand-50); color: var(--brand-700); border: 1px solid var(--brand-200); padding: 1px 7px; border-radius: 999px; font-weight: 600; }
.tl-meta { display: flex; gap: 6px; align-items: center; margin-top: 3px; flex-wrap: wrap; }
.cat-tag { font-size: 11.5px; font-weight: 800; }
.tl-tags { font-size: 11.5px; color: var(--ink-500); background: var(--ink-50); padding: 1px 8px; border-radius: 4px; }
.tl-level { font-size: 11px; color: var(--accent-600); font-weight: 700; }
.tl-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.tl-price { font-size: 15px; font-weight: 800; color: var(--danger); }
.tl-ops { display: flex; gap: 6px; }
.op { border: 1px solid var(--ink-200); background: #fff; color: var(--ink-600); font-size: 12px; padding: 3px 10px; border-radius: 7px; cursor: pointer; }
.op:hover { border-color: var(--brand-400); color: var(--brand-600); }
.op.danger:hover { border-color: var(--danger); color: var(--danger); }

/* stage2 */
.confirm-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 18px; align-items: start; }
.c-title { font-size: 17px; font-weight: 800; color: var(--ink-900); margin-bottom: 18px; }
.field { margin-bottom: 14px; }
.field label { display: block; font-size: 12.5px; font-weight: 700; color: var(--ink-600); margin-bottom: 6px; }
.input, .select, textarea.input { width: 100%; padding: 10px 13px; border-radius: var(--r-md); border: 1px solid var(--ink-200); background: #fff; font-size: 14px; outline: none; box-sizing: border-box; }
.input:focus { border-color: var(--brand-500); box-shadow: 0 0 0 3px rgba(59,130,246,.12); }
textarea.input { resize: vertical; font-family: inherit; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-err { color: var(--danger); font-size: 12.5px; margin-top: 2px; }

.issue-box { margin-top: 6px; padding: 12px 14px; border-radius: var(--r-md); border: 1px solid var(--ink-200); background: var(--ink-50); }
.issue-box.bad { background: #FEF2F2; border-color: #FECACA; }
.issue-tt { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.issue-tt b { font-size: 13px; color: var(--ink-800); }
.issue-box.bad .issue-tt b { color: var(--danger); }
.issue-tt .link-more { font-size: 12px; }
.issue-box ul { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 5px; }
.issue-box li { display: flex; gap: 7px; align-items: flex-start; font-size: 12.5px; line-height: 1.55; color: var(--ink-600); }
.issue-box li.error { color: var(--danger); font-weight: 600; }
.issue-box li i { flex: none; width: 16px; height: 16px; margin-top: 1px; border-radius: 50%; font-style: normal; font-size: 10px; font-weight: 900; display: inline-flex; align-items: center; justify-content: center; background: var(--ink-200); color: var(--ink-600); }
.issue-box li.error i { background: var(--danger); color: #fff; }
.issue-ok { margin-top: 6px; font-size: 12.5px; color: var(--ok); font-weight: 700; padding: 10px 14px; background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: var(--r-md); }

.sum-card { position: sticky; top: 84px; }
.sum-hero { border-radius: var(--r-lg); padding: 22px; color: #fff; display: flex; flex-direction: column; align-items: center; text-align: center; margin-bottom: 18px; }
.sh-emoji { font-size: 44px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.2)); margin-bottom: 6px; }
.sum-hero b { font-size: 16px; }
.sum-hero p { margin: 4px 0 0; font-size: 12.5px; opacity: .9; }
.sum-rows { display: flex; flex-direction: column; }
.sr { display: flex; justify-content: space-between; padding: 11px 2px; border-bottom: 1px dashed var(--ink-200); font-size: 13.5px; color: var(--ink-600); }
.sr b { color: var(--ink-900); }
.sr.total { border-bottom: none; padding-top: 14px; }
.sr.total b { font-size: 19px; color: var(--danger); }
.sr .up { color: var(--danger); }
.sr .down { color: var(--ok); }
.sum-note { font-size: 11.5px; color: var(--ink-400); margin-top: 10px; line-height: 1.7; }
.confirm-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 22px; }

/* picker overlay */
.overlay { position: fixed; inset: 0; background: rgba(15,23,42,.45); backdrop-filter: blur(3px); z-index: 120; display: flex; justify-content: flex-end; }
.sheet { width: min(560px, 100vw); height: 100%; background: var(--ink-50); box-shadow: -18px 0 50px rgba(0,0,0,.18); display: flex; flex-direction: column; }
.sh-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 20px 22px 12px; }
.sh-head b { font-size: 18px; color: var(--ink-900); }
.sh-head p { margin: 5px 0 0; font-size: 12.5px; color: var(--ink-500); }
.sh-tabs { display: flex; gap: 6px; padding: 4px 22px 12px; flex-wrap: wrap; }
.sh-tabs .chip { font-size: 12px; padding: 5px 12px; }
.chip { padding: 7px 16px; border-radius: 999px; border: 1px solid var(--ink-200); background: #fff; color: var(--ink-600); font-size: 13px; cursor: pointer; transition: all .15s; }
.chip.active { background: var(--brand-600); color: #fff; border-color: var(--brand-600); font-weight: 700; }
.sh-list { flex: 1; overflow-y: auto; padding: 4px 22px 16px; display: flex; flex-direction: column; gap: 8px; }
.opt { display: grid; grid-template-columns: 44px 1fr auto; gap: 12px; align-items: center; padding: 10px 12px; cursor: pointer; border: 2px solid transparent; }
.opt:hover { border-color: var(--brand-300); }
.opt.cur { border-color: var(--ok); background: #F0FDF4; }
.opt-emoji { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.opt-name { font-weight: 700; font-size: 14px; color: var(--ink-900); display: flex; align-items: center; gap: 6px; }
.opt-cur { font-size: 10.5px; color: var(--ok); background: #DCFCE7; padding: 1px 7px; border-radius: 999px; font-weight: 700; }
.opt-meta { font-size: 11.5px; color: var(--ink-500); margin-top: 2px; }
.opt-tags { display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }
.opt-tags span { font-size: 10.5px; color: var(--ink-400); background: var(--ink-100); padding: 0 6px; border-radius: 3px; }
.opt-price { text-align: right; font-size: 14px; font-weight: 800; color: var(--ink-900); }
.opt-diff { font-size: 11.5px; font-weight: 700; margin-top: 2px; }
.opt-diff.up { color: var(--danger); }
.opt-diff.down { color: var(--ok); }
.sh-foot { padding: 12px 22px; font-size: 11.5px; color: var(--ink-400); background: #fff; border-top: 1px solid var(--ink-100); }

.link-more { font-size: 13px; color: var(--brand-600); font-weight: 600; }

@media (max-width: 960px) {
  .edit-layout { grid-template-columns: 1fr; }
  .day-nav { position: static; display: flex; gap: 8px; overflow-x: auto; }
  .day-pill { width: auto; white-space: nowrap; }
  .confirm-grid { grid-template-columns: 1fr; }
  .sum-card { position: static; }
}
</style>
