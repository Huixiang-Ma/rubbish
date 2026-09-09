<template>
  <div class="book-split">
    <!-- 左：章节目录（需求6：行程书分解跳转） -->
    <aside class="book-toc">
      <div class="toc-title">📑 目录</div>
      <button v-for="(sec, i) in sections" :key="i" class="toc-item"
              :class="{ active: activeSec === i }" @click="jumpTo(i)">
        {{ sec.label }}
      </button>
    </aside>

    <!-- 右：章节内容 -->
    <div class="book-body">
      <div class="book-tools">
        <span class="sha">sha256: {{ sha.slice(0, 16) }}… {{ sections[activeSec]?.label || '' }}</span>
        <div class="toc-pager" v-if="sections.length > 1">
          <button class="btn btn-ghost btn-sm" :disabled="activeSec === 0" @click="jumpTo(activeSec - 1)">← 上一节</button>
          <button class="btn btn-ghost btn-sm" :disabled="activeSec === sections.length - 1" @click="jumpTo(activeSec + 1)">下一节 →</button>
        </div>
      </div>
      <!-- 章节渲染：景点名带点击替换（需求6）；决策辩论等纯文本章节直接渲染 -->
      <MdView v-if="!sections[activeSec]?.replaceable" :source="sections[activeSec]?.text || ''" />
      <div v-else class="md-body day-book" v-html="sectionHtml"></div>
    </div>
  </div>
</template>

<script setup>
// 行程书分解视图（需求6）：
//   1) 按 "### Day X" / "## " 大标题切段，左侧目录按钮跳转，解决全文过长问题；
//   2) Day 段落里的景点名渲染为可点击 token → 弹出搜索替换（emit replace-spot），
//      选中新景点后走 /api/plans/{id}/replan 增量重规划，仅重跑受影响节点。
import { ref, computed, watch, onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import MdView from './MdView.vue'

const props = defineProps({
  source: { type: String, default: '' },
  sha: { type: String, default: '' },
  spots: { type: Array, default: () => [] },   // 可替换景点名集合（来自 result.itinerary）
})
const emit = defineEmits(['replace-spot'])

const md = new MarkdownIt({ html: true, linkify: true, breaks: false })
const activeSec = ref(0)

const sections = computed(() => {
  const src = props.source || ''
  if (!src.trim()) return []
  // 以 ### 开头的 Day 标题与 ## 二级标题切节
  const lines = src.split('\n')
  const heads = []
  lines.forEach((l, i) => {
    const m = l.match(/^(#{2,3})\s+(.+)$/)
    if (m) heads.push({ line: i, level: m[1].length, title: m[2].trim() })
  })
  if (!heads.length) return [{ label: '全文', text: src, replaceable: false }]
  const out = []
  // 头部（第一个标题前的内容）
  const pre = lines.slice(0, heads[0].line).join('\n').trim()
  if (pre) out.push({ label: '📋 行程概览', text: pre, replaceable: false })
  heads.forEach((h, idx) => {
    const end = idx + 1 < heads.length ? heads[idx + 1].line : lines.length
    const text = lines.slice(h.line, end).join('\n').trim()
    // Day 标签：Day 标题 / 决策辩论 / 翻车预警等
    const label = /day\s*\d|第\s*\d\s*天/i.test(h.title) ? `🗓 ${h.title.slice(0, 18)}` : h.title.slice(0, 18)
    out.push({ label, text, replaceable: /day\s*\d|第\s*\d\s*天/i.test(h.title) })
  })
  return out
})

// Day 章节 HTML：把景点名包成可点击替换 token
const spotNames = computed(() => [...new Set((props.spots || []).filter(Boolean))])

function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') }

watch(sections, () => { activeSec.value = 0 })

const sectionHtml = computed(() => {
  const sec = sections.value[activeSec.value]
  if (!sec || !sec.replaceable) return ''
  let html = md.render(sec.text)
  for (const name of spotNames.value) {
    if (!name || name.length < 2) continue
    const token = `<button class="spot-token" data-spot="${esc(name)}" title="点击搜索替换该景点">📍 ${esc(name)} <span class="st-edit">改</span></button>`
    html = html.split(name).join(token)
  }
  return DOMPurify.sanitize(html, { ADD_ATTR: ['data-spot', 'title'], ADD_TAGS: ['button'] })
})

// expose html via computed for template (v-html binding)

function jumpTo(i) {
  const n = sections.value.length
  activeSec.value = Math.max(0, Math.min(n - 1, i))
}

onMounted(() => {
  document.querySelector('.book-body')?.addEventListener('click', onBodyClick)
})
function onBodyClick(e) {
  const btn = e.target.closest('.spot-token')
  if (btn) emit('replace-spot', btn.getAttribute('data-spot'))
}
</script>

<style scoped>
.book-split { display: grid; grid-template-columns: 168px 1fr; gap: 16px; }
.book-toc { display: flex; flex-direction: column; gap: 4px; position: sticky; top: 76px; align-self: start; }
.toc-title { font-size: 12px; font-weight: 800; color: var(--ink-400); letter-spacing: .1em; padding: 4px 8px; }
.toc-item {
  text-align: left; border: 1px solid var(--ink-100); background: #fff; border-radius: 9px;
  padding: 8px 10px; font-size: 12.5px; font-weight: 600; color: var(--ink-600); cursor: pointer;
  transition: all .14s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.toc-item:hover { border-color: var(--brand-500); color: var(--brand-600); }
.toc-item.active { background: var(--brand-600); border-color: var(--brand-600); color: #fff; }
.book-tools { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.toc-pager { display: flex; gap: 8px; }

/* 景点替换 token */
:deep(.spot-token) {
  display: inline-flex; align-items: center; gap: 4px; border: none; cursor: pointer;
  background: var(--brand-50, #EFF6FF); color: var(--brand-700); font-weight: 700;
  border-bottom: 1.5px dashed var(--brand-500); border-radius: 4px; padding: 0 4px;
  font-size: inherit; line-height: inherit; transition: all .13s;
}
:deep(.spot-token:hover) { background: var(--brand-600); color: #fff; }
:deep(.spot-token .st-edit) {
  font-size: 10px; background: var(--brand-600); color: #fff; border-radius: 3px; padding: 0 4px; font-weight: 800;
}
:deep(.spot-token:hover .st-edit) { background: #fff; color: var(--brand-700); }

@media (max-width: 900px) { .book-split { grid-template-columns: 1fr; } .book-toc { position: static; flex-direction: row; overflow-x: auto; } }
</style>
