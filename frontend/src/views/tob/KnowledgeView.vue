<script setup>
import { ref, computed, onMounted } from 'vue'
import { assistApi } from '../../api/index.js'

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

async function approveAllDrafts() {
  const pending = [...drafts.value]
  let ok = 0
  for (const d of pending) {
    try { await assistApi.kbDraftApprove(d.id); ok++ } catch { /* 单条失败跳过 */ }
  }
  drafts.value = drafts.value.filter(x => x.status === 'pending' && !pending.includes(x))
  load()
  if (ok) window.alert(`已批量入库 ${ok} 条素材（自动挂载语料）`)
}
const docCitations = (doc) => {
  let n = 0
  for (const [jid, c] of Object.entries(citeMap.value)) {
    if (jid.startsWith(`kbdoc_${doc.id}#`)) n += c
  }
  return n
}

/* —— 知识库文档：GET/POST/DELETE /api/kb/docs（真实台账 + 语义层摄入；失败回退演示数据） —— */
const FALLBACK_DOCS = [
  { id: 'kb_001', title: '苏州园林游览注意事项', tags: ['苏州', '注意事项'], chunks: 14, chars: 3820, mode: 'manual', created: '2026-09-08' },
  { id: 'kb_002', title: '杭州雨天备选动线指南', tags: ['杭州', '雨天'], chunks: 9, chars: 2410, mode: 'manual', created: '2026-09-07' },
]
const docs = ref(FALLBACK_DOCS)
const kbTotal = ref(null)
const apiDown = ref(false)

async function load() {
  try {
    const res = await assistApi.kbList()
    if (res && Array.isArray(res.docs)) {
      docs.value = res.docs.map(d => ({
        id: d.id, title: d.title, tags: d.tags || [],
        chunks: d.chunks || 0, chars: d.chars || 0, mode: d.mode || 'manual',
        created: (d.created_at || '').slice(0, 10),
      }))
      kbTotal.value = res.chunks
    }
  } catch { apiDown.value = true }
}
async function delDoc(d) {
  if (!window.confirm(`确认删除文档「${d.title}」及其语料?`)) return
  try { await assistApi.kbDelete(d.id) } catch (e) { window.alert(e.message || '删除失败'); return }
  docs.value = docs.value.filter(x => x.id !== d.id)
}
onMounted(() => { load(); loadLoopData() })

const totalChunks = computed(() => docs.value.reduce((s, d) => s + d.chunks, 0))

/* —— 上传区 —— */
const ALL_EXTS = ['md','markdown','txt','csv','html','htm','pdf','doc','docx','xls','xlsx']
const EXT_LABEL = {
  md: 'Markdown', markdown: 'Markdown', txt: '纯文本', csv: 'CSV',
  html: 'HTML', htm: 'HTML', pdf: 'PDF',
  doc: 'Word', docx: 'Word', xls: 'Excel', xlsx: 'Excel',
}
const SOURCE_LABEL = { file: '文件', folder: '文件夹', drop: '拖拽' }
const SOURCE_ICON  = { file: '📄', folder: '🗂', drop: '🪣' }

const dragOver = ref(false)
const batchNote = ref(null)
const pending = ref([])
const fileInput = ref(null)
const folderInput = ref(null)

const stats = computed(() => ({
  total:    pending.value.length,
  done:     pending.value.filter(p => p.status === 'done').length,
  exists:   pending.value.filter(p => p.status === 'exists').length,
  uploading:pending.value.filter(p => p.status === 'uploading').length,
  pending:  pending.value.filter(p => p.status === 'pending').length,
}))

function fmtSize(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}
function extOf(name) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i + 1).toLowerCase() : ''
}
function labelOf(name) { return EXT_LABEL[extOf(name)] || (extOf(name).toUpperCase() || '文件') }
function isSupported(name) { return ALL_EXTS.includes(extOf(name)) }

function queueIcon(name) {
  const e = extOf(name)
  if (e === 'md' || e === 'markdown') return '📝'
  if (e === 'txt') return '📃'
  if (e === 'csv') return '📊'
  if (e === 'html' || e === 'htm') return '🌐'
  if (e === 'pdf') return '📕'
  if (e === 'doc' || e === 'docx') return '📘'
  if (e === 'xls' || e === 'xlsx') return '📗'
  return '📄'
}

/* 把文件塞进队列(自动启动入库流水线)
 * items: [{ file, path }]，path 为文件夹相对路径（根目录时等于文件名）
 * 文件夹/拖拽模式：只入队可解析的文本类型，其余跳过（数量在完成提示里说明），避免整夹上传刷一屏报错
 */
function enqueue(items, source) {
  const list = Array.from(items || []).filter(x => x && x.file && x.file.name && !x.file.name.startsWith('.'))
  if (!list.length) return []
  const folderMode = source === 'folder' || source === 'drop'
  // 文件夹过滤按"可解析全集"（客户端直读文本 + 服务端解析的 pdf/docx），pump 内再分流
  const PARSEABLE = new Set([...TEXT_EXTS, ...FILE_PARSE_EXTS])
  const created = []
  let skipped = 0
  list.forEach(({ file: f, path }, i) => {
    const relPath = path || f.webkitRelativePath || f.name
    const supported = isSupported(f.name)
    if (folderMode && !PARSEABLE.has(relPath.split('.').pop().toLowerCase())) { skipped++; return }
    const exists = isDuplicateTitle(relPath)
    const item = {
      id: `p_${Date.now()}_${i}_${Math.random().toString(36).slice(2, 6)}`,
      name: relPath,
      size: f.size || 0,
      source,
      supported,
      _file: f,
      progress: 0,
      status: exists ? 'exists' : (supported ? 'pending' : 'error'),
      errorMsg: supported ? '' : '暂不支持的文件类型',
    }
    pending.value.push(item)
    created.push(item)
  })
  if (created.length) pump()
  if (skipped) {
    if (!created.length) {
      // 整夹没有一个可解析文件：常驻警告，别让用户以为"点了没反应"
      batchNote.value = {
        kind: 'warn',
        text: '文件夹里的 ' + skipped + ' 个文件都不支持在线解析（当前支持 MD / TXT / CSV / HTML / PDF / DOCX）。Excel 与旧版 .doc 请先转换格式后再上传。',
      }
    } else {
      batchNote.value = { kind: 'info', text: '已跳过 ' + skipped + ' 个不支持在线解析的文件（支持 MD / TXT / CSV / HTML / PDF / DOCX）' }
      const stamp = skipped
      setTimeout(() => { if (batchNote.value && batchNote.value.text.includes(String(stamp))) batchNote.value = null }, 6000)
    }
  }
  return created
}

/* 串行摄入流水线：文本类文件读内容走 POST /api/kb/docs 真实入库；其余类型提示转换 */
const TEXT_EXTS = ['md', 'markdown', 'txt', 'csv', 'html', 'htm']
// 服务端可解析的二进制文档（走 /api/kb/docs/file 文件直传）
const FILE_PARSE_EXTS = ['pdf', 'docx']
// HTML → 纯文本：去 script/style 等不可见节点，块级标签转段落换行，避免标签污染语料
function htmlToText(raw) {
  const doc = new DOMParser().parseFromString(raw, 'text/html')
  doc.querySelectorAll('script, style, noscript, iframe, svg, template').forEach(el => el.remove())
  const BLOCK = 'p,div,section,article,li,tr,h1,h2,h3,h4,h5,h6,br,pre,blockquote,header,footer,main,nav,ul,ol,dl,dt,dd,figcaption,td,th'
  doc.querySelectorAll(BLOCK).forEach(el => el.insertAdjacentText('afterend', '\n'))
  const text = ((doc.body && (doc.body.textContent || '')) || '')
    .replace(/[ \t\u00a0]+/g, ' ')
    .replace(/\n\s*\n\s*/g, '\n\n')
    .trim()
  return text || raw.replace(/<[^>]+>/g, ' ')
}

// 文档标题口径：与后端 kb_create 一致（相对路径去扩展名，截 40 字）
function titleOf(name) {
  return String(name || '').replace(/\.[^.]+$/, '').slice(0, 40)
}
// 重复文档：知识库里已有同名标题（含本次上传刚入库的），标记"已存入"并跳过重复摄入
function isDuplicateTitle(name) {
  const t = titleOf(name)
  return docs.value.some(d => d.title === t)
}
let pumping = false
function pump() {
  if (pumping) return
  pumping = true
  const next = async () => {
    const job = pending.value.find(p => p.status === 'pending')
    if (!job) { pumping = false; return }
    if (isDuplicateTitle(job.name)) {
      job.progress = 100
      job.status = 'exists'
      setTimeout(next, 120)
      return
    }
    job.status = 'uploading'
    const file = job._file
    const ext = extOf(job.name)
    // PDF / DOCX：二进制直传，服务端 document_ingest 解析（pypdf / python-docx）
    if (file && FILE_PARSE_EXTS.includes(ext)) {
      try {
        const tags = []
        if (job.source !== 'file') tags.push('文件夹批量')
        tags.push(labelOf(job.name))
        const res = await assistApi.kbCreateFile(file, tags)
        job.progress = 100
        job.status = 'done'
        docs.value.unshift({
          id: res.id || 'kb_' + Date.now(),
          title: res.title || job.name,
          tags: res.tags || tags,
          chunks: res.chunks || 0,
          chars: res.chars || 0,
          mode: res.mode || 'import',
          created: (res.created_at || new Date().toISOString()).slice(0, 10),
        })
        setTimeout(next, 200)
        return
      } catch (e) {
        if (e.status === 409) {
          job.progress = 100
          job.status = 'exists'
        } else {
          job.status = 'error'
          job.errorMsg = `解析失败:${e.message || '服务不可用'}`
        }
        setTimeout(next, 200)
        return
      }
    }
    if (file && TEXT_EXTS.includes(ext)) {
      try {
        const raw = await file.text()
        const content = (ext === 'html' || ext === 'htm') ? htmlToText(raw) : raw
        if (!content.trim()) throw new Error('HTML 中没有可提取的正文文本')
        const tags = []
        if (job.source !== 'file') tags.push('文件夹批量')
        tags.push(labelOf(job.name))
        const res = await assistApi.kbCreate({ title: job.name.replace(/\.[^.]+$/, '').slice(0, 40), content, tags })
        job.progress = 100
        job.status = 'done'
        docs.value.unshift({
          id: res.id || 'kb_' + Date.now(),
          title: res.title || job.name,
          tags: res.tags || tags,
          chunks: res.chunks || 0,
          chars: res.chars || content.length,
          mode: res.mode || 'import',
          created: (res.created_at || new Date().toISOString()).slice(0, 10),
        })
        setTimeout(next, 200)
        return
      } catch (e) {
        if (e.status === 409) {
          // 后端同名拒绝（并发/另一端已上传）：按已存入处理，不算失败
          job.progress = 100
          job.status = 'exists'
        } else {
          job.status = 'error'
          job.errorMsg = `入库失败:${e.message || '服务不可用'}`
        }
        setTimeout(next, 200)
        return
      }
    }
    // 其余二进制格式（旧版 .doc / Excel / 扫描件）：如实标记，不做假入库
    job.status = 'error'
    job.errorMsg = ext === 'doc' ? '旧版 .doc 不支持,请另存为 .docx 再上传'
      : '不支持在线解析（支持 MD/TXT/CSV/HTML/PDF/DOCX）'
    setTimeout(next, 200)
  }
  next()
}

/* —— 文件夹递归遍历（FileSystem Entry API）——
 * readEntries 每次最多返回 100 条，必须循环读到空数组为止
 */
function entryFile(entry) {
  return new Promise((resolve, reject) => entry.file(resolve, reject))
}
async function traverseEntry(entry, path, out) {
  if (!entry) return
  if (entry.isFile) {
    try {
      const file = await entryFile(entry)
      if (file && file.name && !file.name.startsWith('.')) out.push({ file, path: path + entry.name })
    } catch { /* 无读权限的文件跳过 */ }
    return
  }
  if (entry.isDirectory) {
    const reader = entry.createReader()
    const next = () => new Promise((resolve, reject) => reader.readEntries(resolve, reject))
    while (true) {
      const rows = await next()
      if (!rows || !rows.length) break
      for (const child of rows) await traverseEntry(child, path + entry.name + '/', out)
    }
  }
}
async function filesFromDataTransfer(dt) {
  // webkitGetAsEntry 必须在 drop 事件同步阶段收集（事件外 items 会失效）
  const entries = Array.from(dt.items || [])
    .map(it => (it.webkitGetAsEntry ? it.webkitGetAsEntry() : null))
    .filter(Boolean)
  if (!entries.length) return Array.from(dt.files || []).map(f => ({ file: f, path: f.name }))
  const out = []
  for (const entry of entries) await traverseEntry(entry, '', out)
  return out
}

/* —— DOM 事件 —— */
function onPickFiles(e)  {
  enqueue(Array.from(e.target.files || []).map(f => ({ file: f, path: f.name })), 'file')
  e.target.value = ''
}
function onPickFolder(e) {
  enqueue(Array.from(e.target.files || []).map(f => ({ file: f, path: f.webkitRelativePath || f.name })), 'folder')
  e.target.value = ''
}
async function onDrop(e) {
  e.preventDefault(); dragOver.value = false
  const dt = e.dataTransfer
  if (!dt) return
  const items = await filesFromDataTransfer(dt)
  const isFolder = Array.from(dt.items || []).some(it => {
    const entry = it.webkitGetAsEntry ? it.webkitGetAsEntry() : null
    return entry && entry.isDirectory
  })
  enqueue(items, isFolder ? 'folder' : 'drop')
}
function onDragOver(e) { e.preventDefault(); dragOver.value = true }

/* 下载导入模板：示例 Markdown，含分段规范 */
function downloadTemplate() {
  const md = ['# 知识库导入模板', '', '第一段：景点介绍、门票价格、开放时间等事实信息（空行分段，每段会被独立分块）。', '', '第二段：预约方式、注意事项、常见问题解答。', '', '第三段：推荐动线、游玩建议、雨天备选方案。', '', '> 提示：保存为 .md / .txt 后通过上方上传区批量导入。'].join('\n\n')
  const blob = new Blob([md], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = '知识库导入模板.md'
  a.click()
  URL.revokeObjectURL(a.href)
}
function onDragLeave() { dragOver.value = false }

function removeOne(p) {
  if (p.status === 'uploading') return // 上传中不让删,避免误判
  const i = pending.value.findIndex(x => x.id === p.id)
  if (i >= 0) pending.value.splice(i, 1)
}
function retryOne(p) { p.status = 'pending'; p.progress = 0; p.errorMsg = ''; pump() }
function clearDone() { pending.value = pending.value.filter(p => p.status !== 'done' && p.status !== 'exists') }
function clearAll()  { pending.value = pending.value.filter(p => p.status === 'uploading') }
function retryAllErrors() {
  pending.value.forEach(p => { if (p.status === 'error') { p.status = 'pending'; p.progress = 0; p.errorMsg = '' } })
  pump()
}

const doneLabel = (p) => {
  if (p.status === 'done') return `${labelOf(p.name)} · 已摄入语料层`
  if (p.status === 'exists') return '该文件已存入 · 跳过重复摄入'
  if (p.status === 'uploading') return `上传并分块摄入中 ${p.progress}%`
  if (p.status === 'error') return p.errorMsg || '等待处理'
  return `等待中 · ${labelOf(p.name)}`
}
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">知识 · 语料</div>
        <h1 class="page-title">知识库文档</h1>
        <p class="page-desc">
          RAG 语料构建:攻略 / 注意事项 / 常见问题。上传的文档会被分块摄入语义检索层
          (与标品语料、用户高分行程攻略同一知识库),toC 的 AI 导游问答与智能助手随即可以引用。
          支持 Markdown / 纯文本 / PDF / Word / Excel,按空行与标题分段。
        </p>
      </div>
      <div class="page-actions">
        <span class="tag">文档 {{ docs.length }} 篇</span>
        <span class="tag tag-accent">语料块 {{ totalChunks }} 块</span>
      </div>
    </div>

    <!-- 上传区 -->
    <section class="card upload-card" :class="{ 'is-drag': dragOver }">
      <div class="upload-head">
        <div>
          <div class="pane-title">上传文档 / 文件夹</div>
          <p class="upload-hint">
            把攻略、注意事项、FAQ 拖到这里,或选择本地文件 / 整个文件夹批量摄入。支持 Markdown / TXT / CSV / HTML（自动提取正文）与
            PDF / Word(.docx)（服务端解析,扫描版 PDF 无文字层除外）;文件夹递归收集子目录,Excel 与旧版 .doc 请先转换。文件按段分块 → 嵌入检索层,与标品语料、用户高分行程统一召回。
          </p>
        </div>
        <div class="upload-types">
          <span class="type-chip">📝 Markdown</span>
          <span class="type-chip">📃 纯文本</span>
          <span class="type-chip">📊 CSV</span>
          <span class="type-chip">🌐 HTML</span>
          <span class="type-chip">📕 PDF</span>
          <span class="type-chip">📘 Word</span>
          <span class="type-chip">🗂 整个文件夹</span>
        </div>
      </div>

      <div
        class="dropzone"
        :class="{ 'is-drag': dragOver }"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="fileInput && fileInput.click()">
        <div class="dz-emoji" aria-hidden="true">📥</div>
        <div class="dz-title">把文件拖到这里,或<span class="dz-em">点击选择</span></div>
        <div class="dz-sub">支持单文件 / 多个文件 / 整个文件夹批量摄入</div>
        <div class="dz-bar">
          <button type="button" class="btn btn-primary"
                  @click.stop="fileInput && fileInput.click()">
            <span aria-hidden="true">⬆</span> 选择文件
          </button>
          <button type="button" class="btn btn-ghost"
                  @click.stop="folderInput && folderInput.click()">
            <span aria-hidden="true">🗂</span> 选择文件夹
          </button>
          <button type="button" class="btn btn-text"
                  @click.stop="downloadTemplate">
            <span aria-hidden="true">⬇</span> 下载导入模板
          </button>
        </div>
        <input ref="fileInput" type="file" multiple hidden
               accept=".md,.markdown,.txt,.csv,.html,.htm,.pdf,.doc,.docx,.xls,.xlsx"
               @change="onPickFiles" />
        <input ref="folderInput" type="file" hidden webkitdirectory directory multiple
               @change="onPickFolder" />
        <p v-if="batchNote" class="batch-note" :class="batchNote.kind">
          {{ batchNote.kind === 'warn' ? '⚠' : 'ℹ' }} {{ batchNote.text }}
          <button v-if="batchNote.kind === 'warn'" class="bn-close" @click="batchNote = null">✕</button>
        </p>
      </div>

      <!-- 队列 -->
      <div v-if="pending.length" class="queue">
        <div class="queue-head">
          <div class="qh-left">
            <b>待处理队列</b>
            <span class="qh-counter">
              共 {{ stats.total }} 个 · 待 {{ stats.pending }} · 上传 {{ stats.uploading }} · 完成 {{ stats.done }}<template v-if="stats.exists"> · 已存入 {{ stats.exists }}</template>
            </span>
          </div>
          <div class="qh-ops">
            <button class="btn btn-ghost btn-sm" @click="retryAllErrors" :disabled="!stats.done && !stats.pending">
              重试失败
            </button>
            <button class="btn btn-ghost btn-sm" @click="clearDone" :disabled="!stats.done">
              清理已完成
            </button>
            <button class="btn btn-ghost btn-sm" @click="clearAll">
              清空
            </button>
          </div>
        </div>

        <ul class="q-rows">
          <li v-for="p in pending" :key="p.id" class="q-row" :class="{ 'is-done': p.status === 'done', 'is-error': p.status === 'error', 'is-exists': p.status === 'exists' }">
            <div class="q-ico" aria-hidden="true">{{ queueIcon(p.name) }}</div>
            <div class="q-body">
              <div class="q-line1">
                <span class="q-name" :title="p.name">{{ p.name }}</span>
                <span class="q-src">{{ SOURCE_ICON[p.source] || '📄' }} {{ SOURCE_LABEL[p.source] || p.source }}</span>
                <span class="q-size">{{ fmtSize(p.size) }}</span>
              </div>
              <div class="q-line2">
                <span class="q-state">{{ doneLabel(p) }}</span>
              </div>
              <div class="q-bar">
                <div class="q-bar-fill"
                  :style="{ width: (p.status === 'done' ? 100 : p.progress) + '%' }"
                  :class="{
                    'fill-uploading': p.status === 'uploading',
                    'fill-done':      p.status === 'done',
                    'fill-error':     p.status === 'error',
                    'fill-pending':   p.status === 'pending',
                    'fill-exists':    p.status === 'exists',
                  }"></div>
              </div>
            </div>
            <div class="q-actions">
              <button v-if="p.status === 'error'"   class="q-act q-act-retry"
                      @click="retryOne(p)"  title="重试">↻</button>
              <button v-else-if="p.status !== 'uploading'"
                      class="q-act"
                      @click="removeOne(p)" title="移除">✕</button>
              <span v-else class="q-act q-spin" title="上传中">◌</span>
            </div>
          </li>
        </ul>
      </div>

      <div v-else class="upload-empty">尚无待处理文件。直接拖入或点击上方按钮开始上传。</div>
    </section>

    <!-- 素材草稿（AI 抽取 → 人工确认入库） -->
    <section v-if="drafts.length" class="card draft-panel">
      <div class="pane-title" style="margin-bottom:var(--s-3);display:flex;align-items:center;gap:var(--s-3)">素材草稿 · AI 从文档抽取（确认后入库）</div>
      <button class="btn btn-primary btn-sm" style="margin-left:auto" @click="approveAllDrafts">✓ 全部确认入库</button>
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
    <div class="kb-grid">
      <!-- 手工录入(兼容老表单) -->
      <section class="card kb-form">
        <div class="pane-title">手工录入</div>
        <div class="field">
          <label>标题 <b>*</b></label>
          <input class="input" placeholder="如:苏州园林游览注意事项" />
        </div>
        <div class="field">
          <label>标签(逗号分隔)</label>
          <input class="input" placeholder="苏州, 注意事项" />
        </div>
        <div class="field">
          <label>正文 <b>*</b>(空行分段)</label>
          <textarea class="input" rows="10" placeholder="拙政园需提前一天实名预约…&#10;&#10;狮子林假山洞适合儿童游玩…"></textarea>
        </div>
        <button class="btn btn-primary">上传并摄入知识库</button>
        <p class="kb-tip">手工录入适合临时性、字数短、非结构化的笔记;批量资料建议使用上方「上传文件 / 文件夹」。</p>
      </section>

      <!-- 文档列表 -->
      <section class="card kb-list">
        <div class="pane-title" style="margin-bottom:var(--s-4)">已入库文档</div>
        <div class="kb-rows">
          <div v-for="d in docs" :key="d.id" class="kb-row">
            <div class="kr-body">
              <b>{{ d.title }}</b>
              <em class="mono-xs">{{ d.chunks }} 块 · {{ d.chars.toLocaleString() }} 字 · {{ d.mode === 'import' ? '批量导入' : '手工录入' }} · {{ d.created }} · <b :class="{ hot: docCitations(d) > 0 }" style="color:#5C7A9D">被引用 {{ docCitations(d) }} 次</b></em>
              <div class="kr-tags">
                <span v-for="t in d.tags" :key="t" class="tag">{{ t }}</span>
              </div>
            </div>
            <div class="kr-ops">
              <button class="btn btn-ghost btn-sm" @click="delDoc(d)">删除</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* —— 上传区 —— */
.upload-card { display: flex; flex-direction: column; gap: var(--s-4); margin-bottom: var(--s-5); }
.upload-head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--s-5); }
.upload-head .pane-title { margin-bottom: var(--s-2); }
.upload-hint { color: var(--text-2); font-size: var(--fs-sm); line-height: var(--lh-base); max-width: 760px; }
.upload-types { display: flex; gap: var(--s-2); flex-wrap: wrap; flex: none; }
.type-chip {
  background: var(--surface-2); color: var(--text-2);
  font-size: var(--fs-xs); padding: 6px var(--s-3); border-radius: var(--r-pill);
  border: 1px solid var(--border-soft);
}

/* dropzone */
.dropzone {
  border: 2px dashed var(--border);
  background: linear-gradient(180deg, var(--surface), var(--surface-2));
  border-radius: var(--r-lg);
  padding: var(--s-7) var(--s-5);
  text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: var(--s-3);
  cursor: pointer;
  transition: background var(--dur-2) var(--ease), border-color var(--dur-2) var(--ease), transform var(--dur-2) var(--ease);
}
.dropzone:hover { border-color: var(--accent); background: var(--surface); }
.dropzone.is-drag {
  border-color: var(--accent);
  background: rgba(107, 122, 92, 0.08);
  transform: scale(1.005);
}
.dz-emoji { font-size: 32px; line-height: 1; }
.dz-title { font-size: var(--fs-md); font-weight: var(--fw-medium); color: var(--text); }
.dz-em { color: var(--accent); margin: 0 4px; font-weight: var(--fw-semi); }
.dz-sub  { font-size: var(--fs-sm); color: var(--text-2); }
.dz-bar  { display: flex; gap: var(--s-3); margin-top: var(--s-2); flex-wrap: wrap; justify-content: center; }

/* queue */
.queue { display: flex; flex-direction: column; gap: var(--s-3); }
.queue-head {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: var(--s-3); border-bottom: 1px solid var(--border-soft); flex-wrap: wrap; gap: var(--s-3);
}
.qh-left { display: flex; align-items: baseline; gap: var(--s-3); }
.qh-counter { font-size: var(--fs-xs); color: var(--text-faint); }

.q-rows { display: flex; flex-direction: column; gap: var(--s-2); margin: 0; padding: 0; list-style: none; }
.q-row {
  display: flex; align-items: center; gap: var(--s-4);
  padding: var(--s-3) var(--s-4);
  background: var(--surface-2);
  border-radius: var(--r-md);
  border: 1px solid var(--border-soft);
  transition: border-color var(--dur-2) var(--ease), background var(--dur-2) var(--ease);
}
.q-row.is-done  { background: rgba(107,122,92,.06);  border-color: rgba(107,122,92,.25); }
.q-row.is-exists { background: rgba(92,122,157,.05); border-color: rgba(92,122,157,.22); }
.q-row.is-exists .q-line2 { color: #5C7A9D; }
.fill-exists     { background: #8CA6BC; }
.q-row.is-error { background: rgba(200, 90, 90, .05); border-color: rgba(200, 90, 90, .25); }
.q-ico  { font-size: 22px; line-height: 1; flex: none; }
.q-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.q-line1 {
  display: flex; align-items: baseline; gap: var(--s-3); font-size: var(--fs-sm);
  flex-wrap: wrap;
}
.q-name {
  font-weight: var(--fw-medium);
  max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.q-src  { color: var(--text-2); font-size: var(--fs-xs); }
.q-size { color: var(--text-faint); font-size: var(--fs-xs); font-variant-numeric: tabular-nums; }
.q-line2 { font-size: var(--fs-xs); color: var(--text-2); }
.q-row.is-done  .q-line2 { color: var(--accent); }
.q-row.is-error .q-line2 { color: var(--danger); }

.q-bar {
  height: 4px; background: var(--border-soft); border-radius: var(--r-pill); overflow: hidden;
}
.q-bar-fill {
  height: 100%; width: 0; border-radius: var(--r-pill); transition: width .3s var(--ease);
}
.fill-pending   { background: var(--text-faint); }
.fill-uploading { background: linear-gradient(90deg, var(--accent), #95a589); }
.fill-done      { background: var(--accent); }
.fill-error     { background: var(--danger); }

.q-actions { display: flex; gap: var(--s-2); flex: none; }
.q-act {
  width: 28px; height: 28px; border-radius: var(--r-sm); border: 1px solid var(--border-soft);
  background: var(--surface); color: var(--text-2); cursor: pointer; font-size: 14px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background var(--dur-2) var(--ease), color var(--dur-2) var(--ease);
}
.q-act:hover { background: var(--surface-2); color: var(--text); }
.q-act-retry:hover { color: var(--accent); border-color: var(--accent); }
.q-spin { animation: spin 1s linear infinite; color: var(--accent); border-color: var(--accent); }

@keyframes spin { from { transform: rotate(0) } to { transform: rotate(360deg) } }

.upload-empty {
  padding: var(--s-5) var(--s-4);
  background: var(--surface-2);
  border-radius: var(--r-md);
  color: var(--text-faint);
  font-size: var(--fs-sm); text-align: center;
}

/* —— 原 kb-grid —— */
.kb-grid { display: grid; grid-template-columns: 400px 1fr; gap: var(--s-4); align-items: start; }
.kb-form { display: flex; flex-direction: column; gap: var(--s-4); }
.kb-tip { font-size: var(--fs-xs); color: var(--text-faint); line-height: var(--lh-base); }

.kb-rows { display: flex; flex-direction: column; }
.kb-row {
  display: flex; align-items: center; gap: var(--s-4);
  padding: var(--s-4) 0;
  border-bottom: 1px solid var(--border-soft);
}
.kb-row:last-child { border-bottom: 0; }
.kr-body { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.kr-body b { font-size: var(--fs-sm); font-weight: var(--fw-medium); }
.kr-tags { display: flex; gap: var(--s-2); margin-top: 2px; }
.kr-ops { display: flex; gap: var(--s-2); flex: none; }

@media (max-width: 1000px) {
  .kb-grid { grid-template-columns: 1fr; }
  .upload-head { flex-direction: column; }
}
.draft-panel { margin-bottom: var(--s-4); padding: var(--s-5); }
.draft-row { display: flex; gap: var(--s-4); align-items: center; padding: var(--s-3) 0; border-bottom: 1px dashed var(--border-soft); }
.draft-row:last-child { border-bottom: none; }
.dr-body { flex: 1; }
.dr-body b { font-size: var(--fs-sm); }
.dr-body em { display: block; margin: 3px 0; }
.dr-body p { margin: 0; font-size: var(--fs-xs); color: var(--text-2); }
.dr-ops { display: flex; gap: var(--s-2); flex: none; }
.batch-note { margin-top: var(--s-3); font-size: var(--fs-xs); color: #9A7B54; background: #F5EFE7; padding: var(--s-2) var(--s-3); border-radius: var(--r-sm); display: flex; align-items: center; gap: var(--s-2); }
.batch-note.warn { color: #A8665C; background: #F6EBE9; border: 1px solid #EBD2CC; }
.batch-note .bn-close { margin-left: auto; border: none; background: transparent; color: inherit; cursor: pointer; font-size: var(--fs-xs); padding: 0 var(--s-2); }
</style>