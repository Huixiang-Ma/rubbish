<template>
  <div class="md-body" v-html="html"></div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const props = defineProps({ source: { type: String, default: '' } })

const md = new MarkdownIt({ html: true, linkify: true, breaks: false })

const html = computed(() => {
  const raw = md.render(props.source || '')
  // 允许行程书内嵌的 details/summary/img 等标签，清掉脚本类危险内容
  return DOMPurify.sanitize(raw, {
    ADD_ATTR: ['target'],
    ADD_TAGS: ['details', 'summary'],
  })
})
</script>
