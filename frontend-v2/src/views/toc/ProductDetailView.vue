<template>
  <div class="container pdp">
    <template v-if="loading">
      <div class="load-wrap"><div class="spinner"></div><p>正在翻开这本行程方案…</p></div>
    </template>

    <template v-else-if="!plan">
      <div class="empty card big">
        <div class="icon">🧭</div>
        <p>没有找到这个方案，它可能已被企业下架。</p>
        <router-link :to="{ name: 'malls' }" class="btn btn-primary">返回方案馆</router-link>
      </div>
    </template>

    <template v-else>
      <div class="crumbs">
        <router-link :to="{ name: 'malls' }">方案馆</router-link>
        <span>›</span>
        <router-link :to="{ name: 'malls-category', params: { key: plan.category } }">{{ plan.category }}</router-link>
        <span>›</span>
        <em>{{ plan.title }}</em>
      </div>

      <section class="hero card">
        <div class="hero-left">
          <div class="h-cover" :style="{ background: plan.cover.gradient }">
            <span class="h-emoji">{{ plan.cover.emoji }}</span>
            <div class="h-badges">
              <span v-for="b in plan.badges" :key="b" class="bd">{{ b }}</span>
            </div>
          </div>
          <div class="h-flow">
            <span class="hf-step"><i>1</i>看动线</span>
            <span class="hf-arrow">→</span>
            <span class="hf-step"><i>2</i>选日期人数</span>
            <span class="hf-arrow">→</span>
            <span class="hf-step on"><i>3</i>整订出发</span>
            <p class="hf-note">一单含全程门票食宿与路线保障，无需再逐项购买</p>
          </div>
        </div>
        <div class="hero-main">
          <div class="hm-tags">
            <span class="tag-cat">{{ plan.category }}</span>
            <span class="tag-city">📍 {{ plan.city }}</span>
            <span class="tag-line">{{ plan.days }} 天{{ plan.days > 1 ? ' · ' + (plan.days - 1) + ' 晚' : '' }}</span>
            <span class="tag-line">{{ plan.pace_zh }}</span>
            <span v-if="plan.season" class="tag-line">🍂 {{ plan.season }}</span>
          </div>
          <h1 class="hm-title">{{ plan.title }}</h1>
          <p class="hm-sub">{{ plan.subtitle }}</p>
          <div class="hm-meta">
            <span class="rating">★ {{ Number(plan.rating).toFixed(1) }}</span>
            <span>{{ plan.poi_count }} 个停留点位</span>
            <span>模板覆盖 {{ plan.badges.length + plan.category.length }} 类素材</span>
            <span>已售 {{ plan.sales }}</span>
          </div>
          <p class="hm-intro">{{ plan.intro }}</p>
          <div class="hm-chips">
            <span class="chip-item">🎫 门票食宿已在报价内</span>
            <span class="chip-item">🗓 {{ plan.available_from }}</span>
            <span class="chip-item">↩️ {{ plan.refund_policy }}</span>
          </div>
        </div>

        <aside class="hero-buy card">
          <div class="price-row">
            <span class="y">¥</span><b class="n">{{ activeSku?.price ?? plan.per_price }}</b>
            <span class="suffix">/ 人 · {{ activeSku?.label || '整订' }}</span>
          </div>
          <s v-if="plan.original_per_price > plan.per_price" class="orig">门市参考 ¥{{ plan.original_per_price }} /人</s>
          <div class="sale-row">
            <span class="stock" :class="{ low: (plan.stock || 0) <= 4 }">⏳ 本团期余 {{ plan.stock || 0 }} 席</span>
            <span class="minp">每单 ≥ {{ plan.min_persons }} 人起订</span>
          </div>

          <div class="buy-field" v-if="skus.length">
            <label>选择种类</label>
            <div class="sku-group">
              <button v-for="s in skus" :key="s.sku_id" type="button"
                      :class="['sku-chip', { on: skuId === s.sku_id }]" @click="skuId = s.sku_id">
                <b>{{ s.label }}</b>
                <em>¥{{ s.price }} · {{ s.spec }}</em>
              </button>
            </div>
            <p class="sku-note" v-if="activeSku?.note">💡 {{ activeSku.note }}</p>
          </div>
          <div class="buy-field">
            <label>出发日期</label>
            <select v-model="date" class="select">
              <option v-for="d in dateOptions" :key="d.value" :value="d.value">
                {{ d.text }}{{ isSoon(d) ? '（余位紧张）' : '' }}
              </option>
            </select>
          </div>
          <div class="buy-field">
            <label>出行人数</label>
            <div class="stepper">
              <button class="step-btn" :disabled="persons <= plan.min_persons" @click="persons--">−</button>
              <div class="num">{{ persons }}</div>
              <button class="step-btn" :disabled="persons >= 12" @click="persons++">＋</button>
              <span class="persons-unit">人</span>
            </div>
          </div>

          <div class="total-row">
            <span>整单合计</span>
            <b>¥{{ total }}</b>
          </div>
          <button class="btn btn-primary btn-lg block" :disabled="buying || !plan.stock"
                  @click="goCheckout">
            <span v-if="buying" class="spinner"></span>
            {{ plan.stock ? '立即整订' : '本团期已满' }}
          </button>
          <div class="buy-actions">
            <button class="btn btn-ghost btn-sm" :class="{ liked: liked }" @click="onLike">
              {{ liked ? '❤️ 已收藏' : '🤍 收藏方案' }}
            </button>
            <button class="btn btn-ghost btn-sm" @click="onShare">🔗 分享方案</button>
          </div>
          <p class="buy-safe">企业直营 · 出行前 1 天可退 · 凭证电子核销</p>
        </aside>
      </section>

      <!-- 含与不含 -->
      <section class="two-col">
        <div class="card pack">
          <div class="pack-title">✅ 一价全包</div>
          <ul class="pack-list">
            <li v-for="(it, i) in plan.include" :key="i"><span class="li-ico">✓</span>{{ it }}</li>
          </ul>
        </div>
        <div class="card pack excl">
          <div class="pack-title">未包含</div>
          <ul class="pack-list dim">
            <li v-for="(it, i) in plan.exclude" :key="i"><span class="li-ico">·</span>{{ it }}</li>
          </ul>
          <p class="excl-note">去程交通可委托企业代订，接单后按需报价</p>
        </div>
      </section>

      <!-- 行程书动线 -->
      <section class="day-book">
        <div class="db-heading">
          <div class="db-title-main">🗺 每日动线 <small>即你下单后会拿到的行程</small></div>
          <p v-if="grounding.total && groundMatched > 0" class="db-rag-line">
            <span class="rag-dot"></span>RAG 知识背书：已为 <b>{{ groundMatched }}/{{ grounding.total }}</b> 个停留点实时核验（来源：标品知识语料）
          </p>
        </div>
        <section v-for="d in plan.itinerary" :key="d.day" class="db-day card">
          <header class="db-head">
            <div class="db-dayno">{{ d.day }}</div>
            <div class="db-titles">
              <div class="db-title">第 {{ d.day }} 天</div>
              <div class="db-sub">{{ dayLine(d) }}</div>
            </div>
            <div class="db-stat">{{ d.blocks.length }} 个停留</div>
          </header>
          <div class="db-body">
            <div v-for="b in d.blocks" :key="b.key" class="db-row">
              <div class="db-time">
                <span class="t">{{ b.start }}</span>
                <span class="p">{{ periodLabel(b.period) }}</span>
              </div>
              <div class="db-line"><i class="dot" :style="{ borderColor: catColor(b.product.category) }"></i></div>
              <div class="db-card is-static">
                <span class="dc-emoji" :style="{ background: (b.product.cover && b.product.cover.gradient) || 'linear-gradient(135deg,#EADFCF,#B8A28C)' }">{{ (b.product.cover && b.product.cover.emoji) || '📍' }}</span>
                <div class="dc-info">
                  <div class="dc-name">{{ b.product.name }}
                    <span v-if="b.tag" class="dc-tag">{{ b.tag }}</span>
                  </div>
                  <div class="dc-meta">
                    <span class="dc-cat" :style="{ color: catColor(b.product.category) }">{{ b.product.category }}</span>
                    <span v-for="t in (b.product.tags || []).slice(0, 3)" :key="t">{{ t }}</span>
                    <span v-if="b.product.level && b.product.level !== '-'">{{ b.product.level }}</span>
                  </div>
                  <div v-if="groundOf(b.product.name)" class="dc-ground">
                    <span class="dg-tag">语料背书</span>
                    <span class="dg-txt">{{ groundOf(b.product.name).snippet }}</span>
                  </div>
                </div>
                <span class="dc-incl" v-if="isFood(b.product)">🍽 含于整订价</span>
                <span class="dc-incl" v-else-if="b.product.category === '住宿'">🛏 {{ b.tag === '退房' ? '退房' : '夜宿含早' }}</span>
                <span class="dc-incl" v-else>🎫 已含票</span>
              </div>
            </div>
          </div>
        </section>
      </section>

      <!-- 推荐同主题 -->
      <section v-if="related.length" class="rel-sec">
        <div class="rel-head">
          <b>同类 / 同城方案</b>
          <router-link :to="{ name: 'malls' }">全部 →</router-link>
        </div>
        <div class="rel-grid">
          <router-link v-for="p in related" :key="p.id"
                       :to="{ name: 'malls-product', params: { id: p.id } }" class="rel-card card">
            <span class="rel-cover" :style="{ background: p.cover.gradient }">{{ p.cover.emoji }}</span>
            <div class="rel-body">
              <div class="rel-name">{{ p.name }}</div>
              <div class="rel-sub">{{ p.days }} 日 · {{ p.category }} · {{ p.city }}</div>
              <div class="rel-price"><b>¥{{ p.per_price }}</b><span>/人</span></div>
            </div>
          </router-link>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { planShopApi, favApi, catalogApi } from '../../api'
import { toast } from '../../composables/toast'

const route = useRoute()
const router = useRouter()
const plan = ref(null)
const related = ref([])
const loading = ref(true)
const liked = ref(false)
const buying = ref(false)
const persons = ref(2)
const date = ref('')
const skuId = ref('')
// RAG 语料背书（B 档）：每站知识原文来自标品知识语料实时检索，后端不可用则整块隐藏
const grounding = ref({ items: [], total: 0 })
const groundMatched = computed(() => grounding.value.items.filter(i => i.matched).length)
function groundOf(name) {
  return grounding.value.items.find(i => i.matched && i.term === name)
}
async function loadGrounding() {
  if (!plan.value) return
  const names = []
  const seen = new Set()
  for (const d of plan.value.itinerary || []) {
    for (const b of d.blocks || []) {
      const n = b.product && b.product.name
      if (n && !seen.has(n)) { seen.add(n); names.push(n) }
    }
  }
  if (!names.length) return
  try {
    const r = await catalogApi.ground(names)
    grounding.value = { items: (r && r.items) || [], total: (r && r.total) || 0 }
  } catch (e) {
    console.warn('[catalog] 语料背书暂不可用，隐藏知识区块:', e.message || e)
    grounding.value = { items: [], total: 0 }
  }
}

const PERIODS = { morning: '上午', midday: '午餐', afternoon: '下午', evening: '晚间', night: '夜宿' }
const CATS = [
  { name: '景点', color: '#0EA5E9' }, { name: '餐饮', color: '#F59E0B' },
  { name: '住宿', color: '#8B5CF6' }, { name: '交通', color: '#10B981' },
  { name: '购物', color: '#EC4899' }, { name: '文化', color: '#6366F1' },
]
const DAY_MARKS = ['', '一', '二', '三', '四', '五', '六', '日']

const dateOptions = computed(() => {
  const out = []
  const today = new Date()
  const soonDays = [2, 4, 8]
  for (let i = 1; i <= 30; i++) {
    const d = new Date(today.getTime() + i * 86400000)
    const w = DAY_MARKS[d.getDay()]
    out.push({
      value: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
      text: `${i === 1 ? '明天' : i === 2 ? '后天' : d.getMonth() + 1 + '月' + d.getDate() + '日'}（周${w}）`,
      soon: soonDays.includes(i),
    })
  }
  return out
})
const skus = computed(() => plan.value?.skus || [])
const activeSku = computed(() => skus.value.find(x => x.sku_id === skuId.value) || skus.value[0] || null)
const total = computed(() => plan.value ? (activeSku.value?.price ?? plan.value.per_price) * persons.value : 0)

function periodLabel(k) { return PERIODS[k] || k }
function catColor(name) {
  const c = CATS.find(x => x.name === name)
  return c ? c.color : '#94A3B8'
}
function isFood(p) { return p.category === '餐饮' }
function dayLine(d) {
  const parts = d.blocks.map(b => b.product.name)
  return parts.slice(0, 3).join(' → ') + (parts.length > 3 ? ` 等 ${d.blocks.length} 站` : '')
}
function isSoon(d) { return d.soon }

async function load() {
  loading.value = true
  plan.value = null
  try {
    const id = route.params.id
    const r = await planShopApi.detail(id)
    plan.value = r.plan
    related.value = r.related || []
    persons.value = Math.max(r.plan.min_persons || 2, 2)
    skuId.value = (r.plan.skus || []).find(x => x.default)?.sku_id || (r.plan.skus || [])[0]?.sku_id || ''
    if (!date.value) date.value = dateOptions.value[2]?.value || ''
    if (plan.value.stock === 0) toast('该方案本期已满，可换个出发日', 'warn')
    if (plan.value) loadGrounding()
  } catch (e) {
    plan.value = null
  } finally {
    loading.value = false
  }
}

async function syncLike() {
  try {
    const r = await favApi.list()
    const ids = (r.items || []).map(x => x.id)
    liked.value = ids.includes(plan.value.id)
  } catch (e) { /* 忽略 */ }
}
async function onLike() {
  if (!plan.value) return
  const r = await favApi.toggle(plan.value.id)
  liked.value = r.liked
  toast(r.liked ? '已收藏到我的收藏' : '已取消收藏', 'ok')
}
function onShare() {
  const url = location.origin + location.pathname + '#/malls/product/' + plan.value.id
  if (navigator.clipboard) navigator.clipboard.writeText(url).catch(() => {})
  toast('链接已复制，可分享给同伴', 'ok')
}
function goCheckout() {
  if (!date.value) { toast('请先选择出发日期', 'warn'); return }
  if ((plan.value.stock || 0) <= 0) { toast('该团期已满', 'warn'); return }
  router.push({ name: 'malls-checkout', query: { product: plan.value.id, persons: persons.value, date: date.value, sku: activeSku.value?.sku_id || '' } })
}

onMounted(() => {
  load().then(() => { if (plan.value) syncLike() })
})
</script>

<style scoped>
.pdp { padding: 22px 0 46px; }
.load-wrap { text-align: center; padding: 90px 0; color: var(--ink-500); }
.load-wrap .spinner { margin: 0 auto 14px; }
.crumbs { display: flex; gap: 8px; align-items: center; font-size: 13px; color: var(--ink-400); margin-bottom: 16px; }
.crumbs a { color: var(--brand-600); text-decoration: none !important; }
.crumbs em { font-style: normal; color: var(--ink-600); }

.hero { display: grid; grid-template-columns: 300px 1fr 320px; gap: 26px; padding: 26px; align-items: start; }
.hero-left { display: flex; flex-direction: column; gap: 14px; }
.h-cover { aspect-ratio: 4/3.4; border-radius: 14px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
.h-emoji { font-size: 110px; filter: drop-shadow(0 8px 12px rgba(0,0,0,.18)); }
.h-badges { position: absolute; left: 10px; top: 10px; display: flex; gap: 4px; flex-wrap: wrap; }
.h-badges .bd { background: rgba(255,255,255,.92); color: var(--brand-800); font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; }
.h-flow { border: 1px dashed var(--ink-300); border-radius: 10px; padding: 10px 12px; background: var(--ink-50); }
.hf-step { display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--ink-500); font-weight: 600; }
.hf-step i { width: 16px; height: 16px; border-radius: 50%; background: #fff; border: 1px solid var(--ink-300); font-style: normal; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; color: var(--ink-500); }
.hf-step.on { color: var(--brand-700); }
.hf-step.on i { background: var(--brand-600); color: #fff; border-color: var(--brand-600); }
.hf-arrow { color: var(--ink-300); margin: 0 3px; font-size: 12px; }
.hf-note { margin: 8px 0 0; font-size: 11px; color: var(--ink-400); line-height: 1.5; }

.hm-tags { display: flex; gap: 7px; flex-wrap: wrap; }
.tag-cat { background: var(--brand-600); color: #fff; font-weight: 700; font-size: 11.5px; padding: 3px 9px; border-radius: 4px; }
.tag-city, .tag-line { background: var(--ink-100); color: var(--ink-700); font-size: 11.5px; padding: 3px 9px; border-radius: 4px; font-weight: 600; }
.hm-title { font-size: 26px; font-weight: 900; margin: 14px 0 4px; color: var(--ink-900); letter-spacing: -.02em; line-height: 1.3; }
.hm-sub { font-size: 14px; color: var(--ink-500); margin: 0; }
.hm-meta { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12.5px; color: var(--ink-500); margin-top: 12px; }
.hm-meta .rating { color: var(--accent-600); font-weight: 800; }
.hm-intro { font-size: 13.5px; color: var(--ink-600); line-height: 1.8; margin: 14px 0 10px; }
.hm-chips { display: flex; flex-direction: column; gap: 5px; }
.chip-item { font-size: 12.5px; color: var(--ink-600); }

.hero-buy { padding: 18px 18px 16px; box-shadow: 0 10px 30px rgba(15,23,42,.10); position: sticky; top: 96px; }
.price-row { display: flex; align-items: baseline; gap: 2px; }
.price-row .y { color: var(--danger); font-weight: 800; font-size: 16px; }
.price-row .n { font-size: 32px; font-weight: 900; color: var(--danger); letter-spacing: -.02em; }
.price-row .suffix { font-size: 12px; color: var(--ink-500); }
.orig { font-size: 12px; color: var(--ink-400); }
.sale-row { display: flex; justify-content: space-between; font-size: 11.5px; margin-top: 8px; }
.stock { color: var(--ok-700, #15803D); font-weight: 700; }
.stock.low { color: var(--danger); }
.minp { color: var(--ink-400); }
.sku-group { display: flex; flex-wrap: wrap; gap: 7px; }
.sku-chip {
  border: 1.5px solid var(--ink-200); background: #fff; border-radius: 11px;
  padding: 7px 11px; cursor: pointer; text-align: left; transition: all .14s; min-width: 46%;
  flex: 1 1 46%;
}
.sku-chip:hover { border-color: var(--brand-500); }
.sku-chip.on { border-color: var(--brand-600); background: var(--brand-50, #EFF6FF); box-shadow: 0 0 0 2px rgba(37,99,235,.12); }
.sku-chip b { display: block; font-size: 12.5px; color: var(--ink-900); }
.sku-chip em { font-style: normal; font-size: 11px; color: var(--ink-500); }
.sku-note { font-size: 11.5px; color: var(--ink-400); margin: 6px 0 0; }
.buy-field { margin-top: 14px; }
.buy-field label { font-size: 12px; font-weight: 700; color: var(--ink-600); display: block; margin-bottom: 6px; }
.stepper { display: flex; align-items: center; gap: 6px; }
.step-btn { width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--ink-300); background: #fff; color: var(--ink-800); font-size: 16px; cursor: pointer; }
.step-btn:disabled { opacity: .4; cursor: not-allowed; }
.stepper .num { min-width: 34px; text-align: center; font-weight: 800; font-size: 16px; }
.persons-unit { font-size: 12px; color: var(--ink-400); margin-left: 4px; }
.total-row { display: flex; justify-content: space-between; align-items: baseline; margin: 16px 0 8px; font-size: 13px; color: var(--ink-700); border-top: 1px dashed var(--ink-200); padding-top: 12px; }
.total-row b { font-size: 24px; color: var(--danger); font-weight: 900; }
.block { width: 100%; }
.buy-actions { display: flex; gap: 8px; margin-top: 10px; }
.buy-actions .btn { flex: 1; }
.liked { border-color: var(--danger) !important; color: var(--danger) !important; }
.buy-safe { font-size: 11.5px; color: var(--ink-400); text-align: center; margin: 10px 0 0; }

.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 16px; }
.pack { padding: 20px 24px; }
.pack.excl { background: var(--ink-50); }
.pack-title { font-weight: 800; font-size: 15px; color: var(--ink-900); margin-bottom: 12px; }
.pack-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.pack-list li { font-size: 13px; color: var(--ink-700); display: flex; gap: 8px; align-items: flex-start; }
.pack-list.dim li { color: var(--ink-400); }
.li-ico { color: var(--ok-700, #15803D); font-weight: 900; }
.pack-list.dim .li-ico { color: var(--ink-300); }
.excl-note { font-size: 12px; color: var(--ink-400); margin: 10px 0 0; }

.day-book { margin-top: 30px; }
.db-heading { font-size: 19px; font-weight: 900; color: var(--ink-900); margin-bottom: 14px; }
.db-heading small { font-size: 12.5px; font-weight: 500; color: var(--ink-400); margin-left: 8px; }
.db-rag-line { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--ink-500); margin: 8px 0 0; }
.db-rag-line b { color: var(--brand-700); font-weight: 800; }
.rag-dot { width: 8px; height: 8px; border-radius: 50%; background: linear-gradient(135deg, #34D399, #0EA5E9); flex: none; }
.db-day { margin-bottom: 14px; padding: 18px 22px; }
.db-head { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
.db-dayno { width: 36px; height: 36px; border-radius: 10px; background: var(--brand-600); color: #fff; font-weight: 900; display: flex; align-items: center; justify-content: center; font-size: 17px; }
.db-title { font-weight: 800; font-size: 15px; color: var(--ink-900); }
.db-sub { font-size: 12.5px; color: var(--ink-500); margin-top: 2px; }
.db-stat { margin-left: auto; font-size: 12px; color: var(--ink-400); background: var(--ink-100); padding: 4px 10px; border-radius: 999px; }
.db-row { display: flex; align-items: stretch; gap: 10px; }
.db-time { width: 66px; flex: none; text-align: right; padding-top: 12px; }
.db-time .t { font-size: 13px; font-weight: 800; color: var(--ink-800); display: block; }
.db-time .p { font-size: 11px; color: var(--ink-400); display: block; margin-top: 2px; }
.db-line { width: 14px; display: flex; justify-content: center; position: relative; }
.db-line::before { content: ''; width: 2px; background: var(--ink-200); position: absolute; top: 0; bottom: 0; }
.db-row:first-child .db-line::before { top: 26px; }
.db-row:last-child .db-line::before { bottom: auto; height: 26px; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #fff; border: 2.5px solid var(--ink-300); position: relative; top: 26px; z-index: 1; }
.db-card { flex: 1; display: flex; align-items: center; gap: 12px; margin: 6px 0; border-radius: 10px; }
.dc-emoji { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; }
.dc-name { font-size: 14px; font-weight: 700; color: var(--ink-900); display: flex; align-items: center; gap: 6px; }
.dc-tag { font-size: 10px; background: var(--brand-100); color: var(--brand-800); padding: 1px 6px; border-radius: 3px; font-weight: 600; }
.dc-meta { display: flex; gap: 10px; font-size: 11.5px; color: var(--ink-400); margin-top: 3px; }
.dc-cat { font-weight: 700; }
.dc-incl { margin-left: auto; font-size: 11px; font-weight: 700; color: var(--ok-700, #15803D); white-space: nowrap; }
.dc-info { flex: 1; min-width: 0; }
.dc-ground { display: flex; align-items: flex-start; gap: 7px; margin-top: 7px; padding-top: 7px; border-top: 1px dashed var(--ink-200); font-size: 11.5px; line-height: 1.6; color: var(--ink-500); }
.dg-tag { flex: none; font-size: 10.5px; font-weight: 700; color: #0369A1; background: linear-gradient(135deg, rgba(16,185,129,.16), rgba(14,165,233,.14)); padding: 2px 7px; border-radius: 999px; margin-top: 1px; }
.dg-txt { min-width: 0; }

.rel-sec { margin-top: 34px; }
.rel-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.rel-head b { font-size: 17px; color: var(--ink-900); }
.rel-head a { font-size: 13px; color: var(--brand-600); text-decoration: none !important; }
.rel-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.rel-card { display: flex; gap: 12px; align-items: center; padding: 12px; text-decoration: none !important; transition: all .15s; }
.rel-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.rel-cover { width: 74px; height: 58px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 30px; flex: none; }
.rel-name { font-size: 13.5px; font-weight: 700; color: var(--ink-900); }
.rel-sub { font-size: 11.5px; color: var(--ink-400); margin-top: 3px; }
.rel-price b { color: var(--danger); font-size: 16px; font-weight: 900; }
.rel-price span { font-size: 11px; color: var(--ink-400); }

@media (max-width: 1080px) {
  .hero { grid-template-columns: 220px 1fr; }
  .hero-buy { grid-column: 1 / -1; position: static; }
}
@media (max-width: 760px) {
  .hero { grid-template-columns: 1fr; }
  .two-col, .rel-grid { grid-template-columns: 1fr; }
  .db-stat { display: none; }
}
</style>
