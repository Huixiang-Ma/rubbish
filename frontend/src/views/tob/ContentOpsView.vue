<script setup>
import { ref, computed } from 'vue'
import TobIcon from '../../components/TobIcon.vue'

/* —— 运营位渠道 —— */
const CHANNELS = [
  { key: 'notice',  label: '首页公告',   desc: '游客端首页顶部滚动公告与横幅' },
  { key: 'wenchuang', label: '文创商城运营位', desc: '方案馆侧栏 · 文创好物推荐位' },
  { key: 'activity', label: '文化活动',   desc: '非遗体验 / 展览演出 活动卡片' },
  { key: 'study',   label: '智慧书房',   desc: '目的地文化书单与阅读点位' },
]
const channel = ref('notice')
const ch = computed(() => CHANNELS.find(c => c.key === channel.value))

/* —— 各渠道运营位内容(mock) —— */
const content = ref({
  notice: [
    { id: 'n1', title: '国庆黄金周 · 苏州园林分时预约已开放', sub: '10-01 至 10-07 场次紧张,建议提前 7 天锁定', emoji: '📢', color: '#6B7A5C', status: 'on',  weight: 98, start: '09-25', end: '10-08', hits: 41203 },
    { id: 'n2', title: '网师园夜花园 10 月加开周二场次', sub: '昆曲实景演出 · 每日限 300 席', emoji: '🌙', color: '#7B8DA0', status: 'on',  weight: 85, start: '10-01', end: '10-31', hits: 12840 },
    { id: 'n3', title: '平江路周末步行街时段调整公告', sub: '周六日 10:00-20:00 机动车禁行', emoji: '🚧', color: '#B08968', status: 'draft', weight: 60, start: '待定', end: '待定', hits: 0 },
  ],
  wenchuang: [
    { id: 'w1', title: '苏扇 · 制扇大师联名款', sub: '檀香扇 · 限量 200 把 · ¥388', emoji: '🪭', color: '#B08968', status: 'on', weight: 92, start: '09-01', end: '11-30', hits: 8621 },
    { id: 'w2', title: '缂丝团扇 DIY 材料包', sub: '含视频教程 · 亲子手工 · ¥128', emoji: '🧵', color: '#8B7A9E', status: 'on', weight: 78, start: '09-10', end: '12-31', hits: 5310 },
    { id: 'w3', title: '平江路盖章护照 · 2026 秋季版', sub: '12 个点位集章兑换文创贴纸', emoji: '📔', color: '#6B9A7E', status: 'off', weight: 40, start: '08-01', end: '09-01', hits: 3012 },
  ],
  activity: [
    { id: 'a1', title: '昆曲雅集 · 全本《牡丹亭》选段', sub: '10-15 19:30 · 中国昆曲剧院 · ¥180 起', emoji: '🎭', color: '#8B7A9E', status: 'on', weight: 95, start: '10-01', end: '10-15', hits: 7420 },
    { id: 'a2', title: '苏绣非遗工坊 · 双面绣体验课', sub: '每周六 14:00 · 镇湖绣品街 · ¥260', emoji: '🪡', color: '#C1857E', status: 'on', weight: 82, start: '09-05', end: '12-27', hits: 4180 },
    { id: 'a3', title: '古城墙夜跑 · 环护城河 8km', sub: '10-20 19:00 · 阊门集合 · 免费', emoji: '🏃', color: '#6B7A5C', status: 'draft', weight: 55, start: '待定', end: '待定', hits: 0 },
  ],
  study: [
    { id: 's1', title: '《苏州园林》书单 · 读懂造园八法', sub: '12 本精选 · 含童寯《江南园林志》', emoji: '📚', color: '#6B7A5C', status: 'on', weight: 88, start: '长期', end: '长期', hits: 9840 },
    { id: 's2', title: '古城阅读地图 · 8 家独立书店打卡', sub: '含慢书房、文学山房旧书店', emoji: '🗺', color: '#7B8DA0', status: 'on', weight: 72, start: '长期', end: '长期', hits: 6512 },
  ],
})
const rows = computed(() => content.value[channel.value])

/* 导出排期表：当前频道内容 → JSON 下载 */
function exportSchedule() {
  const blob = new Blob([JSON.stringify({ channel: channel.value, items: rows.value }, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `content-${channel.value}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

const statusMeta = {
  on:    { label: '上线中', cls: 'pill-on pill-dot' },
  off:   { label: '已下线', cls: 'pill-off pill-dot' },
  draft: { label: '草稿',   cls: 'pill-draft' },
}
function toggle(row) {
  row.status = row.status === 'on' ? 'off' : 'on'
}

/* —— 可视化编辑器 —— */
const editing = ref(null)   // null 关闭;{} 新建
function openEditor(row) { editing.value = { ...row } }
function openCreate() { editing.value = { id: null, title: '', sub: '', emoji: '📣', color: '#6B7A5C', status: 'draft', weight: 50, start: '', end: '' } }
function saveEdit() {
  const list = content.value[channel.value]
  const i = list.findIndex(r => r.id === editing.value.id)
  if (i >= 0) list[i] = { ...editing.value }
  else list.push({ ...editing.value, id: channel.value[0] + Date.now(), hits: 0 })
  editing.value = null
}
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">运营管理</div>
        <h1 class="page-title">内容管理 · 运营位</h1>
        <p class="page-desc">
          管理游客端四处内容运营位:<b>首页公告 / 文创商城 / 文化活动 / 智慧书房</b>。
          所有内容支持<b>可视化编辑</b>、排期上下线与权重排序,变更实时生效至游客端。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm"><TobIcon name="download" :size="14" />导出排期表</button>
        <button class="btn btn-primary btn-sm" @click="openCreate"><TobIcon name="plus" :size="14" />新建内容</button>
      </div>
    </div>

    <!-- 渠道切换 -->
    <nav class="ch-tabs">
      <button v-for="c in CHANNELS" :key="c.key" :class="{ on: channel === c.key }" @click="channel = c.key">
        <b>{{ c.label }}</b><i>{{ content[c.key].length }} 条 · {{ content[c.key].filter(r => r.status === 'on').length }} 在线</i>
      </button>
    </nav>
    <p class="ch-desc">{{ ch.desc }}</p>

    <!-- 内容卡片列表 -->
    <div class="ops-grid">
      <div v-for="r in rows" :key="r.id" class="card ops-card">
        <div class="oc-cover" :style="{ background: r.color + '18' }">
          <span class="oc-emoji" :style="{ color: r.color }">{{ r.emoji }}</span>
          <span class="pill" :class="statusMeta[r.status].cls">{{ statusMeta[r.status].label }}</span>
        </div>
        <div class="oc-body">
          <b class="oc-title">{{ r.title }}</b>
          <span class="oc-sub">{{ r.sub }}</span>
          <div class="oc-meta">
            <span>排期 {{ r.start }} ~ {{ r.end }}</span>
            <span>权重 {{ r.weight }}</span>
            <span>曝光 {{ r.hits.toLocaleString() }}</span>
          </div>
          <div class="oc-ops">
            <button class="op" @click="openEditor(r)">编辑</button>
            <button class="op" @click="toggle(r)">{{ r.status === 'on' ? '下线' : '上线' }}</button>
            <button class="op">查看数据</button>
          </div>
        </div>
        <!-- 权重条 -->
        <div class="oc-weight"><i :style="{ width: r.weight + '%', background: r.color }"></i></div>
      </div>
    </div>

    <!-- 可视化编辑器 -->
    <div v-if="editing" class="dw-mask" @click.self="editing = null">
      <div class="dw card">
        <header class="dw-head">
          <h3>{{ editing.id ? '编辑运营内容' : '新建运营内容' }} · {{ ch.label }}</h3>
          <button class="dw-x" @click="editing = null"><TobIcon name="x" :size="13" /></button>
        </header>

        <div class="dw-body">
          <!-- 实时预览 -->
          <div class="preview">
            <span class="pv-label">游客端实时预览</span>
            <div class="pv-card" :style="{ background: editing.color + '16', borderColor: editing.color + '55' }">
              <span class="pv-emoji" :style="{ color: editing.color }">{{ editing.emoji }}</span>
              <div>
                <b>{{ editing.title || '(标题预览)' }}</b>
                <span>{{ editing.sub || '(副标题预览)' }}</span>
              </div>
            </div>
          </div>

          <div class="form-grid">
            <label class="f full"><span>标题</span><input v-model="editing.title" placeholder="一句话说清价值" /></label>
            <label class="f full"><span>副标题</span><input v-model="editing.sub" placeholder="补充信息 / 价格 / 时间" /></label>
            <label class="f"><span>图标(emoji)</span><input v-model="editing.emoji" maxlength="4" /></label>
            <label class="f"><span>主题色</span>
              <div class="colors">
                <button v-for="c in ['#6B7A5C', '#B08968', '#7B8DA0', '#8B7A9E', '#C1857E', '#6B9A7E']" :key="c"
                        :style="{ background: c }" :class="{ on: editing.color === c }" @click="editing.color = c" />
              </div>
            </label>
            <label class="f"><span>上线日期</span><input v-model="editing.start" placeholder="09-25" /></label>
            <label class="f"><span>下线日期</span><input v-model="editing.end" placeholder="10-08" /></label>
            <label class="f full"><span>曝光权重 {{ editing.weight }}</span>
              <input v-model.number="editing.weight" type="range" min="0" max="100" />
            </label>
            <label class="f full ck-row">
              <input v-model="editing.status" type="checkbox" :true-value="'on'" :false-value="'draft'" />
              <span>保存后立即上线(否则存为草稿)</span>
            </label>
          </div>
        </div>

        <footer class="dw-foot">
          <button class="btn btn-ghost btn-sm" @click="editing = null">取消</button>
          <button class="btn btn-primary btn-sm" @click="saveEdit">保存并生效</button>
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ch-tabs { display: flex; gap: var(--s-3); flex-wrap: wrap; margin-bottom: var(--s-2); }
.ch-tabs button {
  border: 1px solid var(--border-soft); background: var(--surface);
  border-radius: var(--r-md); padding: var(--s-3) var(--s-4);
  display: flex; flex-direction: column; gap: 3px; cursor: pointer; text-align: left;
  transition: all var(--dur-1) var(--ease); min-width: 170px;
}
.ch-tabs button.on { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(107,122,92,.1); }
.ch-tabs b { font-size: var(--fs-sm); color: var(--text); }
.ch-tabs i { font-style: normal; font-size: var(--fs-xs); color: var(--text-faint); }
.ch-desc { font-size: var(--fs-xs); color: var(--text-3); margin-bottom: var(--s-4); }

.ops-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: var(--s-4); }
.ops-card { overflow: hidden; display: flex; flex-direction: column; }
.oc-cover { display: flex; align-items: flex-start; justify-content: space-between; padding: var(--s-5); }
.oc-emoji { font-size: 30px; }
.oc-body { padding: 0 var(--s-5) var(--s-4); flex: 1; display: flex; flex-direction: column; gap: 6px; }
.oc-title { font-size: var(--fs-sm); }
.oc-sub { font-size: var(--fs-xs); color: var(--text-3); }
.oc-meta { display: flex; gap: var(--s-3); font-size: 11px; color: var(--text-faint); margin: var(--s-2) 0; }
.oc-ops { display: flex; gap: var(--s-2); margin-top: auto; }
.op { border: none; background: none; font-size: var(--fs-xs); color: var(--accent); cursor: pointer; padding: 2px 0; }
.op:hover { text-decoration: underline; }
.oc-weight { height: 3px; background: var(--surface-2); }
.oc-weight i { display: block; height: 100%; }

.pill-draft { background: var(--surface-2); color: var(--text-faint); font-size: var(--fs-xs); padding: 2px 10px; border-radius: var(--r-pill); font-weight: var(--fw-medium); }

/* 编辑器 */
.dw-mask { position: fixed; inset: 0; background: rgba(31,29,26,.32); z-index: 120; display: flex; align-items: center; justify-content: center; }
.dw { width: min(560px, 94vw); max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; }
.dw-head { display: flex; justify-content: space-between; align-items: center; padding: var(--s-4) var(--s-5); border-bottom: 1px solid var(--border-soft); }
.dw-head h3 { font-size: var(--fs-md); }
.dw-x { border: none; background: var(--surface-2); width: 28px; height: 28px; border-radius: var(--r); cursor: pointer; color: var(--text-3); display: inline-flex; align-items: center; justify-content: center; }
.dw-body { padding: var(--s-5); overflow-y: auto; }
.dw-foot { display: flex; justify-content: flex-end; gap: var(--s-2); padding: var(--s-4) var(--s-5); border-top: 1px solid var(--border-soft); }

.preview { margin-bottom: var(--s-5); }
.pv-label { font-size: var(--fs-xs); color: var(--text-faint); display: block; margin-bottom: var(--s-2); }
.pv-card { display: flex; gap: var(--s-3); align-items: center; padding: var(--s-4); border: 1px solid; border-radius: var(--r-md); }
.pv-emoji { font-size: 24px; }
.pv-card b { font-size: var(--fs-sm); display: block; }
.pv-card span { font-size: var(--fs-xs); color: var(--text-3); }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
.f { display: flex; flex-direction: column; gap: 5px; }
.f span { font-size: var(--fs-xs); color: var(--text-2); font-weight: var(--fw-medium); }
.full { grid-column: 1 / -1; }
.colors { display: flex; gap: 6px; }
.colors button { width: 24px; height: 24px; border-radius: 50%; border: 2px solid var(--surface); cursor: pointer; }
.colors button.on { border-color: var(--text); box-shadow: 0 0 0 2px var(--surface), 0 0 0 4px var(--border); }
.ck-row { flex-direction: row; align-items: center; gap: 8px; cursor: pointer; }
.ck-row span { font-weight: var(--fw-regular); }
input[type="range"] { accent-color: var(--accent); }
</style>
