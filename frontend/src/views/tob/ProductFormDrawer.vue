<script setup>
import { ref, computed, watch } from 'vue'
import TobIcon from '../../components/TobIcon.vue'

const props = defineProps({
  open: Boolean,
  product: { type: Object, default: null },   // null = 新建
})
const emit = defineEmits(['close', 'save'])

const CATS = ['景点', '餐饮', '住宿', '交通', '体验', '购物', '文化']
const CITIES = ['苏州', '杭州', '大理', '成都', '厦门', '西安']
const SLOTS = [
  { key: 'morning', label: '上午(08:30-11:00)' },
  { key: 'midday', label: '中午(11:30-13:30)' },
  { key: 'afternoon', label: '下午(14:00-17:30)' },
  { key: 'evening', label: '傍晚(17:30-19:00)' },
  { key: 'night', label: '夜间(21:00 后)' },
]

const blank = () => ({
  name: '', category: '景点', city: '苏州',
  price: 0, priceMax: 0, stock: 100,
  dwell: '2h', slot: 'morning', rating: 4.5,
  x: null, y: null, note: '',
  tags: [], listed: true, manual: true,
})

const form = ref(blank())
watch(() => props.open, (v) => {
  if (v) form.value = props.product ? { ...blank(), ...props.product } : blank()
})

const isEdit = computed(() => !!props.product)
const tagInput = ref('')
function addTag() {
  const t = tagInput.value.trim()
  if (t && !form.value.tags.includes(t)) form.value.tags.push(t)
  tagInput.value = ''
}
function removeTag(t) { form.value.tags = form.value.tags.filter(x => x !== t) }

const vErrors = computed(() => {
  const e = []
  if (!form.value.name.trim()) e.push('名称必填')
  if (form.value.priceMax < form.value.price) e.push('价格上限不得低于下限')
  if (form.value.stock < 0) e.push('库存不能为负')
  return e
})

function save() {
  if (vErrors.value.length) return
  emit('save', { ...form.value, id: form.value.id || `SKU-${String(Date.now()).slice(-4)}` })
  emit('close')
}
</script>

<template>
  <div v-if="open" class="drawer-mask" @click.self="emit('close')">
    <div class="drawer">
      <header class="dw-head">
        <div>
          <h3>{{ isEdit ? '编辑标品素材' : '新建标品素材' }}</h3>
          <p>{{ isEdit ? `正在编辑 ${product.name}(${product.id})` : '新建后默认「自建」素材,可被方案引用' }}</p>
        </div>
        <button class="dw-close" @click="emit('close')"><TobIcon name="x" :size="14" /></button>
      </header>

      <div class="dw-body">
        <!-- 基础信息 -->
        <section class="dw-sec">
          <h4>基础信息</h4>
          <div class="grid-2">
            <label class="f"><span>名称 *</span><input v-model="form.name" placeholder="如:拙政园" /></label>
            <label class="f"><span>分类 *</span>
              <select v-model="form.category"><option v-for="c in CATS" :key="c">{{ c }}</option></select>
            </label>
            <label class="f"><span>城市 *</span>
              <select v-model="form.city"><option v-for="c in CITIES" :key="c">{{ c }}</option></select>
            </label>
            <label class="f"><span>参考评分</span><input v-model.number="form.rating" type="number" step="0.1" min="0" max="5" /></label>
          </div>
        </section>

        <!-- 价格与库存 -->
        <section class="dw-sec">
          <h4>价格与余量</h4>
          <div class="grid-3">
            <label class="f"><span>价格下限(¥) *</span><input v-model.number="form.price" type="number" min="0" /></label>
            <label class="f"><span>价格上限(¥)</span><input v-model.number="form.priceMax" type="number" min="0" /></label>
            <label class="f"><span>参考余量</span><input v-model.number="form.stock" type="number" min="0" /></label>
          </div>
        </section>

        <!-- 时段 -->
        <section class="dw-sec">
          <h4>编排属性(供智能体排程引用)</h4>
          <div class="grid-2">
            <label class="f"><span>建议游玩时长</span><input v-model="form.dwell" placeholder="如 2.5h" /></label>
            <label class="f"><span>建议时段</span>
              <select v-model="form.slot"><option v-for="s in SLOTS" :key="s.key" :value="s.key">{{ s.label }}</option></select>
            </label>
            <label class="f"><span>经度(可选)</span><input v-model="form.x" placeholder="120.62" /></label>
            <label class="f"><span>纬度(可选)</span><input v-model="form.y" placeholder="31.32" /></label>
          </div>
          <p class="hint">填入坐标后,该标品将出现在行程动线图与 24h 时间线中。</p>
        </section>

        <!-- 标签 -->
        <section class="dw-sec">
          <h4>标签</h4>
          <div class="tag-row">
            <span v-for="t in form.tags" :key="t" class="tag">{{ t }}<button @click="removeTag(t)">✕</button></span>
            <input v-model="tagInput" placeholder="输入后回车" @keyup.enter="addTag" />
          </div>
        </section>

        <!-- 备注 -->
        <section class="dw-sec">
          <h4>运营备注(内部)</h4>
          <textarea v-model="form.note" rows="3" placeholder="预约限制、旺季提示、对接人等,仅运营侧可见"></textarea>
        </section>

        <label class="dw-switch">
          <input v-model="form.listed" type="checkbox" />
          <span>立即上架(允许新方案引用)</span>
        </label>
      </div>

      <footer class="dw-foot">
        <p v-if="vErrors.length" class="verr">⚠ {{ vErrors.join(' · ') }}</p>
        <div class="dw-btns">
          <button class="btn btn-ghost btn-sm" @click="emit('close')">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="!!vErrors.length" @click="save">
            {{ isEdit ? '保存修改' : '创建素材' }}
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.drawer-mask {
  position: fixed; inset: 0; z-index: 120;
  background: rgba(31,29,26,.32);
  display: flex; justify-content: flex-end;
}
.drawer {
  width: min(560px, 94vw); height: 100%;
  background: var(--surface);
  display: flex; flex-direction: column;
  box-shadow: var(--shadow-lg);
  animation: slideIn .24s var(--ease);
}
@keyframes slideIn { from { transform: translateX(24px); opacity: 0 } to { transform: none; opacity: 1 } }

.dw-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: var(--s-5) var(--s-6);
  border-bottom: 1px solid var(--border-soft);
}
.dw-head h3 { font-size: var(--fs-md); }
.dw-head p { font-size: var(--fs-xs); color: var(--text-3); margin-top: 4px; }
.dw-close { border: none; background: var(--surface-2); border-radius: var(--r); width: 30px; height: 30px; cursor: pointer; color: var(--text-3); display: inline-flex; align-items: center; justify-content: center; }

.dw-body { flex: 1; overflow-y: auto; padding: var(--s-5) var(--s-6); }
.dw-sec { margin-bottom: var(--s-5); }
.dw-sec h4 { font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--text-3); text-transform: uppercase; letter-spacing: .08em; margin-bottom: var(--s-3); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-3); }
.f { display: flex; flex-direction: column; gap: 5px; margin-bottom: var(--s-2); }
.f span { font-size: var(--fs-xs); color: var(--text-2); font-weight: var(--fw-medium); }
.hint { font-size: var(--fs-xs); color: var(--text-faint); margin-top: var(--s-2); }

.tag-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.tag-row input { width: 130px; flex: none; }
.tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: var(--fs-xs); color: var(--accent);
  background: var(--accent-soft); padding: 3px 8px; border-radius: var(--r-pill);
}
.tag button { border: none; background: none; color: inherit; cursor: pointer; font-size: 10px; padding: 0; opacity: .7; }

textarea { resize: vertical; }

.dw-switch { display: flex; align-items: center; gap: 8px; font-size: var(--fs-sm); color: var(--text-2); cursor: pointer; }

.dw-foot {
  border-top: 1px solid var(--border-soft);
  padding: var(--s-4) var(--s-6);
  display: flex; align-items: center; gap: var(--s-3);
  background: var(--surface);
}
.verr { font-size: var(--fs-xs); color: var(--danger); margin-right: auto; }
.dw-btns { margin-left: auto; display: flex; gap: var(--s-2); }
</style>
