# -*- coding: utf-8 -*-
"""闭环前端改造第二批（跑完即删）"""
import io

def patch(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for old, new, tag in pairs:
        assert old in s, f'{path} NOT FOUND: {tag}'
        s = s.replace(old, new, 1)
    io.open(path, 'w', encoding='utf-8').write(s)
    print('patched', path)

# ========== 1. KnowledgeView：引用列 + 素材草稿面板 ==========
patch('views/tob/KnowledgeView.vue', [
    ("""import { assistApi } from '../../api/index.js'""",
     """import { assistApi } from '../../api/index.js'

/* 语料引用统计（job_id 前缀聚合到文档）+ 素材草稿 */
const citeMap = ref({})
const drafts = ref([])
async function loadLoopData() {
  try {
    const c = await assistApi.ragCitations()
    const map = {}
    for (const it of (c.items || [])) map[it.job_id] = it.count
    citeMap.value = map
  } catch { /* staff 才可读 */ }
  try {
    const d = await assistApi.kbDrafts()
    drafts.value = (d.items || []).filter(x => x.status === 'pending')
  } catch { /* ignore */ }
}
async function approveDraft(d) {
  try { await assistApi.kbDraftApprove(d.id); d.status = 'approved'; drafts.value = drafts.value.filter(x => x.id !== d.id) }
  catch (e) { window.alert(e.message || '入库失败') }
}
async function rejectDraft(d) {
  try { await assistApi.kbDraftReject(d.id); drafts.value = drafts.value.filter(x => x.id !== d.id) } catch { /* ignore */ }
}
const docCitations = (doc) => {
  let n = 0
  for (const [jid, c] of Object.entries(citeMap.value)) {
    if (jid.startsWith(`kbdoc_${doc.id}#`)) n += c
  }
  return n
}""", 'loop logic'),
    ("""onMounted(load)""", """onMounted(() => { load(); loadLoopData() })""", 'onMounted'),
    # 文档行：em 后追加引用次数
    ("""              <em class="mono-xs">{{ d.chunks }} 块 · {{ d.chars.toLocaleString() }} 字 · {{ d.mode === 'import' ? '批量导入' : '手工录入' }} · {{ d.created }}</em>""",
     """              <em class="mono-xs">{{ d.chunks }} 块 · {{ d.chars.toLocaleString() }} 字 · {{ d.mode === 'import' ? '批量导入' : '手工录入' }} · {{ d.created }} · <b :class="{ hot: docCitations(d) > 0 }" style="color:#5C7A9D">被引用 {{ docCitations(d) }} 次</b></em>""", 'citation col'),
    # 草稿面板：插在编辑+列表的 kb-grid 前
    ("""    <!-- 编辑 + 列表 -->
    <div class="kb-grid">""",
     """    <!-- 素材草稿（AI 抽取 → 人工确认入库） -->
    <section v-if="drafts.length" class="card draft-panel">
      <div class="pane-title" style="margin-bottom:var(--s-3)">素材草稿 · AI 从文档抽取（确认后入库）</div>
      <div v-for="d in drafts" :key="d.id" class="draft-row">
        <div class="dr-body">
          <b>{{ d.name }}</b>
          <em class="mono-xs">{{ d.city || '城市待定' }} · 票价 {{ d.ticket_price }} 元 · {{ d.open_time || '开放时间待定' }} · 来自「{{ d.doc_title }}」</em>
          <p>{{ d.description }}</p>
        </div>
        <div class="dr-ops">
          <button class="btn btn-primary btn-sm" @click="approveDraft(d)">确认入库</button>
          <button class="btn btn-ghost btn-sm" @click="rejectDraft(d)">忽略</button>
        </div>
      </div>
    </section>

    <!-- 编辑 + 列表 -->
    <div class="kb-grid">""", 'draft panel'),
    # 样式
    (""".batch-note {""",
     """.draft-panel { margin-bottom: var(--s-4); padding: var(--s-5); }
.draft-row { display: flex; gap: var(--s-4); align-items: center; padding: var(--s-3) 0; border-bottom: 1px dashed var(--border-soft); }
.draft-row:last-child { border-bottom: none; }
.dr-body { flex: 1; }
.dr-body b { font-size: var(--fs-sm); }
.dr-body em { display: block; margin: 3px 0; }
.dr-body p { margin: 0; font-size: var(--fs-xs); color: var(--text-2); }
.dr-ops { display: flex; gap: var(--s-2); flex: none; }
.batch-note {""", 'draft styles'),
], )
print('--- KnowledgeView done ---')

# ========== 2. CoverageView：缺口工单面板 ==========
patch('views/tob/CoverageView.vue', [
    ("""import { coverageApi } from '../../api/index.js'""",
     """import { coverageApi } from '../../api/index.js'

/* 语料缺口工单：拒答/空命中 query 聚类（数据智能闭环 环2） */
const gaps = ref([])
const gapsLoaded = ref(false)
async function loadGaps() {
  try {
    const res = await coverageApi ? null : null
  } catch { /* ignore */ }
}""", 'gap stub'),
], )
# 上面的 stub 不好——直接重写这段
s = io.open('views/tob/CoverageView.vue', encoding='utf-8').read()
old = """import { coverageApi } from '../../api/index.js'

/* —— 覆盖率：GET /api/stats/product-coverage(/trend)（结构对齐后端口径；失败回退演示数据） —— */
const overview = ref({"""
new = """import { coverageApi } from '../../api/index.js'
import { assistApi } from '../../api/index.js'

/* 语料缺口工单：拒答/空命中 query 聚类（环2 闭环） */
const gaps = ref([])
async function loadGaps() {
  try {
    const res = await assistApi.ragGaps()
    gaps.value = (res && res.items) || []
  } catch { /* staff 才可读 */ }
}

/* —— 覆盖率：GET /api/stats/product-coverage(/trend)（结构对齐后端口径；失败回退演示数据） —— */
const overview = ref({"""
assert old in s, 'coverage import not found'
s = s.replace(old, new, 1)
old = """onMounted(async () => {
  try {
    const res = await coverageApi.overview()"""
new = """onMounted(async () => {
  loadGaps()
  try {
    const res = await coverageApi.overview()"""
assert old in s, 'coverage onMounted not found'
s = s.replace(old, new, 1)
io.open('views/tob/CoverageView.vue', 'w', encoding='utf-8').write(s)
print('Coverage logic ok')

# 模板：在 page-head 后加缺口工单卡片
s = io.open('views/tob/CoverageView.vue', encoding='utf-8').read()
import re
m = re.search(r'(</div>\s*\n\s*<!-- 趋势折线图 -->|<!-- )', s)
old = """    <!-- 页头 -->
    <div class="page-head">"""
new = """    <!-- 语料缺口工单（环2） -->
    <div v-if="gaps.length" class="card gaps-card">
      <h4 style="margin:0 0 var(--s-3)">📋 语料缺口工单 · {{ gaps.length }} 条（拒答/空命中聚类）</h4>
      <div v-for="g in gaps.slice(0, 8)" :key="g.query" class="gap-row">
        <span class="gap-q">{{ g.query }}</span>
        <span class="tag tag-warn">命中失败 {{ g.count }} 次</span>
        <span class="mono-xs" style="color:var(--text-faint)">{{ g.last_at }}</span>
      </div>
      <p class="gap-tip">建议：为以上高频问题补充对应知识库文档（MD/TXT/CSV/HTML），补充后自动进入召回。</p>
    </div>

    <!-- 页头 -->
    <div class="page-head">"""
assert old in s, 'coverage page-head not found'
s = s.replace(old, new, 1)
old = """onMounted(renderChart)"""
new = """.gaps-card { margin-bottom: var(--s-4); padding: var(--s-5); }
.gap-row { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0; border-bottom: 1px dashed var(--border-soft); }
.gap-q { flex: 1; font-size: var(--fs-sm); }
.gap-tip { margin: var(--s-3) 0 0; font-size: var(--fs-xs); color: var(--text-3); }
onMounted(renderChart)"""
assert old in s
s = s.replace(old, new, 1)
io.open('views/tob/CoverageView.vue', 'w', encoding='utf-8').write(s)
print('Coverage ALL DONE')
