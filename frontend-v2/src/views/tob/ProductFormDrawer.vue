<template>
  <div class="pf-mask" @click.self="$emit('close')">
    <div class="pf-sheet">
      <div class="pf-head">
        <div>
          <h3 class="pf-title">{{ product ? '编辑标品' : '新建标品' }}</h3>
          <p class="pf-sub">{{ product ? `ID: ${product.id} · 保存后游客端商城实时同步` : '为游客端商城上架一个新的「行程积木」标品' }}</p>
        </div>
        <button class="pf-x" @click="$emit('close')">✕</button>
      </div>

      <div class="pf-body">
        <!-- 基础信息 -->
        <div class="pf-sec">
          <div class="pf-sec-title">基础信息</div>
          <div class="pf-grid2">
            <label class="pf-field"><span>标品名称 *</span>
              <input v-model.trim="form.name" placeholder="如：狮子林门票（含讲解）" />
            </label>
            <label class="pf-field"><span>分类 *</span>
              <select v-model="form.category" @change="autoCover">
                <option v-for="c in CAT_META" :key="c.key" :value="c.name">{{ c.emoji }} {{ c.name }}</option>
              </select>
            </label>
            <label class="pf-field"><span>城市/区域 *</span>
              <input v-model.trim="form.city" list="pf-cities" placeholder="如：苏州" />
            </label>
            <datalist id="pf-cities">
              <option v-for="c in cityOptions" :key="c" :value="c" />
            </datalist>
            <label class="pf-field"><span>等级 / 档位</span>
              <input v-model.trim="form.level" placeholder="如：5A / 老字号 / 园林酒店 / 高铁" />
            </label>
            <label class="pf-field"><span>开放/营业时间</span>
              <input v-model.trim="form.open" placeholder="如：08:00-17:00 / 全天" />
            </label>
            <label class="pf-field"><span>建议游览时长</span>
              <input v-model.trim="form.typical_dwell" placeholder="如：2.5h / 8h(住宿)" />
            </label>
            <label class="pf-field"><span>最佳入程时段</span>
              <select v-model="form.best_slot">
                <option value="morning">上午</option>
                <option value="midday">中午</option>
                <option value="afternoon">下午</option>
                <option value="evening">傍晚/夜间</option>
              </select>
            </label>
          </div>

          <label class="pf-field"><span>一句话介绍</span>
            <textarea v-model.trim="form.description" rows="2" placeholder="给游客端商品详情页看的描述" />
          </label>

          <div class="pf-grid2">
            <label class="pf-field"><span>标签（逗号分隔）</span>
              <input v-model.trim="form.tagsText" placeholder="如：园林, 世界遗产, 免预约" />
            </label>
            <label class="pf-field"><span>服务角标（逗号分隔）</span>
              <input v-model.trim="form.badgesText" placeholder="如：电子票, 随买随用" />
            </label>
          </div>
        </div>

        <!-- 封面 -->
        <div class="pf-sec">
          <div class="pf-sec-title">展示封面</div>
          <div class="pf-cover-row">
            <div class="pf-cover-preview" :style="{ background: form.gradient }">
              <span>{{ form.emoji || '🏷' }}</span>
            </div>
            <div class="pf-cover-controls">
              <label class="pf-field inline"><span>图标</span>
                <input v-model.trim="form.emoji" maxlength="4" placeholder="选个 emoji" style="width:110px" />
              </label>
              <div class="pf-grads">
                <button v-for="g in GRADIENTS" :key="g.css" :style="{ background: g.css }"
                        :class="{ on: form.gradient === g.css }" @click="form.gradient = g.css"
                        :title="g.name" />
              </div>
            </div>
          </div>
        </div>

        <!-- SKU 与库存价格 -->
        <div class="pf-sec">
          <div class="pf-sec-title">
            规格 · 库存 · 价格
            <button class="pf-add-sku" @click="addSku">＋ 添加规格</button>
          </div>
          <table class="pf-sku-table">
            <thead>
              <tr><th>规格名</th><th>售价(¥)</th><th>划线价(¥)</th><th>库存</th><th>单人限购</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="(s, i) in form.skus" :key="i">
                <td><input v-model.trim="s.label" placeholder="成人票" /></td>
                <td><input type="number" v-model.number="s.price" min="0" /></td>
                <td><input type="number" v-model.number="s.original_price" min="0" placeholder="选填" /></td>
                <td><input type="number" v-model.number="s.stock" min="0" /></td>
                <td><input type="number" v-model.number="s.limit_per_user" min="1" max="99" /></td>
                <td><button class="pf-del-sku" :disabled="form.skus.length <= 1" @click="form.skus.splice(i, 1)">✕</button></td>
              </tr>
            </tbody>
          </table>
          <p class="pf-sku-tip">售价可填 0 表示「免费」；划线价不填则默认与售价一致。库存是下单可售量，游客端支付后自动扣减。</p>
        </div>

        <!-- 服务 -->
        <div class="pf-sec">
          <div class="pf-sec-title">服务政策</div>
          <div class="pf-grid2">
            <label class="pf-field"><span>退改政策</span>
              <select v-model="form.refund">
                <option>未使用随时退</option>
                <option>未使用 23:59 前退</option>
                <option>未使用 2h 前退</option>
                <option>预约制，不支持退款</option>
              </select>
            </label>
            <label class="pf-field"><span>核销方式</span>
              <input v-model.trim="form.pickup" placeholder="如：刷身份证入园 / 到店出示券码" />
            </label>
            <label class="pf-field"><span>供应商</span>
              <input v-model.trim="form.vendor" placeholder="如：苏州文旅 / 自营供应商" />
            </label>
            <label class="pf-field"><span>品牌</span>
              <input v-model.trim="form.brand" placeholder="如：迹程甄选" />
            </label>
          </div>
        </div>
      </div>

      <div class="pf-foot">
        <div class="pf-foot-state">
          <label class="pf-switch"><input type="checkbox" v-model="form.listed" />
            <span class="pf-slider" />{{ form.listed ? '在架（游客端可见可售）' : '下架（仅工作台可见）' }}</label>
        </div>
        <div class="pf-foot-actions">
          <button class="btn-ghost" @click="$emit('close')">取消</button>
          <button class="btn-primary" @click="save">保存标品</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  product: { type: Object, default: null },
})
const emit = defineEmits(['close', 'save'])

const CAT_META = [
  { key: 'sight', name: '景点', emoji: '🏛' },
  { key: 'food', name: '餐饮', emoji: '🍜' },
  { key: 'hotel', name: '住宿', emoji: '🏨' },
  { key: 'transit', name: '交通', emoji: '🚄' },
  { key: 'shop', name: '购物', emoji: '🛍' },
  { key: 'culture', name: '文化', emoji: '📚' },
]
const GRADIENTS = [
  { css: 'linear-gradient(135deg,#60A5FA 0%,#A78BFA 100%)', name: '湖蓝紫' },
  { css: 'linear-gradient(135deg,#FCD34D 0%,#F472B6 100%)', name: '暖橙粉' },
  { css: 'linear-gradient(135deg,#34D399 0%,#0EA5E9 100%)', name: '青碧' },
  { css: 'linear-gradient(135deg,#A78BFA 0%,#EC4899 100%)', name: '紫藤' },
  { css: 'linear-gradient(135deg,#F97316 0%,#F43F5E 100%)', name: '日落' },
  { css: 'linear-gradient(135deg,#6366F1 0%,#38BDF8 100%)', name: '靛蓝' },
]
const CAT_GRADIENT = {
  景点: 'linear-gradient(135deg,#60A5FA 0%,#A78BFA 100%)',
  餐饮: 'linear-gradient(135deg,#FCD34D 0%,#F472B6 100%)',
  住宿: 'linear-gradient(135deg,#A78BFA 0%,#EC4899 100%)',
  交通: 'linear-gradient(135deg,#34D399 0%,#0EA5E9 100%)',
  购物: 'linear-gradient(135deg,#F97316 0%,#F43F5E 100%)',
  文化: 'linear-gradient(135deg,#6366F1 0%,#38BDF8 100%)',
}

function fresh() {
  return {
    name: '', category: '景点', city: '', level: '', open: '09:00-17:00',
    typical_dwell: '2h', best_slot: 'morning', description: '',
    tagsText: '', badgesText: '', emoji: '🏛', gradient: CAT_GRADIENT['景点'],
    vendor: '', brand: '', refund: '未使用随时退', pickup: '出示电子凭证',
    listed: true,
    skus: [
      { label: '成人', spec: '成人票', price: 80, original_price: 90, stock: 2000, limit_per_user: 9 },
    ],
  }
}
function fillFrom(p) {
  return {
    name: p.name, category: p.category, city: p.city, level: p.level, open: p.open,
    typical_dwell: p.typical_dwell, best_slot: p.best_slot, description: p.description || '',
    tagsText: (p.tags || []).join(', '),
    badgesText: (p.badges || []).join(', '),
    emoji: p.cover?.emoji || '🏷', gradient: p.cover?.gradient || CAT_GRADIENT[p.category] || GRADIENTS[0].css,
    vendor: p.vendor || '', brand: p.brand || '', refund: p.refund || '未使用随时退',
    pickup: p.pickup || '出示电子凭证', listed: p.listed !== false,
    skus: (p.skus || []).map(s => ({
      label: s.label || s.spec, spec: s.spec || s.label || '默认规格',
      price: Number(s.price) || 0,
      original_price: s.original_price != null ? Number(s.original_price) : 0,
      stock: Number(s.stock) || 0,
      limit_per_user: s.limit_per_user || 9,
    })),
  }
}

const form = reactive(fresh())
const CITY_OPTIONS = ['苏州', '北京', '上海', '杭州', '南京', '西安', '成都', '苏州→上海', '上海→苏州', '杭州→乌镇', '南京→苏州']
const cityOptions = CITY_OPTIONS

watch(() => props.product, (p) => {
  Object.assign(form, p ? fillFrom(p) : fresh())
}, { immediate: true })

function autoCover() {
  if (props.product) return
  const meta = CAT_META.find(c => c.name === form.category)
  if (meta && !form.emoji) form.emoji = meta.emoji
  form.gradient = CAT_GRADIENT[form.category] || GRADIENTS[0].css
  if (!form.emoji) form.emoji = meta.emoji
}
function addSku() {
  form.skus.push({ label: '', spec: '默认规格', price: 0, original_price: 0, stock: 0, limit_per_user: 9 })
}
function save() {
  if (!form.name.trim()) return alert('请填写标品名称')
  if (!form.city.trim()) return alert('请填写城市/区域')
  if (!form.skus.length) return alert('至少需要一条规格')
  const skus = form.skus.map(s => ({
    spec: s.spec || s.label || '默认规格',
    label: s.label || s.spec || '默认',
    price: Math.max(0, Number(s.price) || 0),
    original_price: s.original_price > s.price ? Number(s.original_price) : Number(s.price),
    stock: Math.max(0, Number(s.stock) || 0),
    limit_per_user: Math.max(1, Number(s.limit_per_user) || 9),
  }))
  const payload = {
    name: form.name.trim(),
    category: form.category,
    city: form.city.trim(),
    level: form.level || '-',
    open: form.open,
    typical_dwell: form.typical_dwell,
    best_slot: form.best_slot,
    description: form.description.trim(),
    tags: form.tagsText.split(/[,，]/).map(t => t.trim()).filter(Boolean),
    badges: form.badgesText.split(/[,，]/).map(t => t.trim()).filter(Boolean),
    cover: { emoji: form.emoji || '🏷', gradient: form.gradient, caption: form.name },
    skus,
    refund: form.refund,
    pickup: form.pickup,
    vendor: form.vendor || '自营供应商',
    brand: form.brand || form.name,
    listed: !!form.listed,
  }
  emit('save', { payload, editing: !!props.product })
}
</script>

<style scoped>
.pf-mask {
  position: fixed; inset: 0; z-index: 300; background: rgba(2, 6, 23, .6); backdrop-filter: blur(2px);
  display: flex; justify-content: flex-end;
}
.pf-sheet {
  width: 760px; max-width: 96vw; height: 100vh; background: var(--bg-panel); border-left: 1px solid var(--line);
  display: flex; flex-direction: column; box-shadow: -20px 0 60px rgba(0, 0, 0, .4);
}
.pf-head { padding: 18px 24px; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; }
.pf-title { margin: 0; font-size: 18px; color: var(--text); }
.pf-sub { margin: 4px 0 0; color: var(--text-faint); font-size: 12.5px; }
.pf-x { background: var(--bg-raised); border: 1px solid var(--line); color: var(--text-dim); border-radius: 8px; width: 30px; height: 30px; cursor: pointer; }
.pf-body { flex: 1; overflow-y: auto; padding: 18px 24px 24px; display: flex; flex-direction: column; gap: 16px; }
.pf-sec { background: var(--bg-raised); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; display: flex; flex-direction: column; gap: 12px; }
.pf-sec-title { font-size: 14px; font-weight: 800; color: var(--text); display: flex; align-items: center; gap: 8px; }
.pf-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pf-field { display: flex; flex-direction: column; gap: 6px; }
.pf-field.inline { flex-direction: row; align-items: center; gap: 10px; }
.pf-field > span { font-size: 12px; color: var(--text-dim); font-weight: 600; }
.pf-field input, .pf-field textarea, .pf-field select {
  background: var(--bg-panel); border: 1px solid var(--line); color: var(--text);
  border-radius: 9px; padding: 8px 11px; font-size: 13px; font-family: inherit;
}
.pf-field textarea { resize: vertical; min-height: 52px; }
.pf-field input:focus, .pf-field textarea:focus, .pf-field select:focus { outline: none; border-color: var(--brand-dim); }

.pf-cover-row { display: flex; gap: 16px; align-items: center; }
.pf-cover-preview {
  width: 76px; height: 76px; border-radius: 14px; display: flex; align-items: center;
  justify-content: center; font-size: 38px; flex: none; box-shadow: 0 6px 18px rgba(0, 0, 0, .3);
}
.pf-cover-controls { display: flex; flex-direction: column; gap: 10px; }
.pf-grads { display: flex; gap: 8px; }
.pf-grads button { width: 30px; height: 30px; border-radius: 8px; border: 2px solid transparent; cursor: pointer; opacity: .85; }
.pf-grads button.on { border-color: #fff; opacity: 1; box-shadow: 0 0 0 2px var(--brand-dim); }

.pf-sku-table { width: 100%; border-collapse: collapse; }
.pf-sku-table th { text-align: left; font-size: 12px; color: var(--text-faint); padding: 6px 4px; border-bottom: 1px solid var(--line); }
.pf-sku-table td { padding: 5px 4px; }
.pf-sku-table input {
  width: 100%; background: var(--bg-panel); border: 1px solid var(--line); color: var(--text);
  padding: 7px 9px; border-radius: 8px; font-size: 13px;
}
.pf-sku-table input[type=number] { width: 84px; }
.pf-del-sku { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 14px; }
.pf-del-sku:disabled { opacity: .3; cursor: not-allowed; }
.pf-add-sku { margin-left: auto; background: none; border: 1px solid var(--brand-dim); color: var(--brand); border-radius: 8px; padding: 4px 12px; cursor: pointer; font-size: 12.5px; font-family: inherit; }
.pf-sku-tip { font-size: 12px; color: var(--text-faint); margin: 0; }

.pf-foot { padding: 14px 24px; border-top: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.pf-switch { display: flex; align-items: center; gap: 8px; color: var(--text-dim); font-size: 13px; cursor: pointer; }
.pf-switch input { display: none; }
.pf-slider {
  width: 40px; height: 22px; border-radius: 999px; background: var(--bg-hover); position: relative; transition: background .15s;
}
.pf-slider::after {
  content: ''; position: absolute; width: 16px; height: 16px; border-radius: 50%; top: 3px; left: 3px;
  background: var(--text-dim); transition: all .15s;
}
.pf-switch input:checked + .pf-slider { background: var(--brand-dim); }
.pf-switch input:checked + .pf-slider::after { left: 21px; background: #fff; }
.pf-foot-actions { display: flex; gap: 10px; }
.pf-foot-actions button { border-radius: 10px; padding: 9px 22px; font-size: 14px; font-weight: 600; border: none; cursor: pointer; font-family: inherit; }
.btn-ghost { background: var(--bg-raised); color: var(--text-dim); border: 1px solid var(--line) !important; }
.btn-primary { background: linear-gradient(135deg, var(--brand-dim), var(--brand)); color: #04121F; font-weight: 800; }
</style>
