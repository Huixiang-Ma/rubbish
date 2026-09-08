<template>
  <span class="tag" :class="cls"><span v-if="live" class="dot pulse-dot"></span>{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ status: { type: String, required: true } })

const MAP = {
  QUEUED:               { cls: 'tag-gray',  label: '排队中' },
  RUNNING:              { cls: 'tag-blue',  label: '生成中', live: true },
  COMPLETED:            { cls: 'tag-green', label: '已完成' },
  WAITING_SAFETY_REVIEW:{ cls: 'tag-red',   label: '待安全审核' },
  WAITING_BUDGET_APPROVAL:{ cls: 'tag-amber', label: '待预算审批' },
  FAILED:               { cls: 'tag-red',   label: '失败' },
  CORRUPTED:            { cls: 'tag-red',   label: '数据损坏' },
  RECOVERY_REQUIRED:    { cls: 'tag-amber', label: '需恢复' },
  REPLAN_REQUIRED:      { cls: 'tag-amber', label: '需重规划' },
  // RAG 检索模式
  llm:        { cls: 'tag-green', label: 'LLM 有据生成' },
  refusal:    { cls: 'tag-red',   label: '拒答' },
  empty:      { cls: 'tag-gray',  label: '空命中' },
  retrieval:  { cls: 'tag-amber', label: '检索兜底' },
  streaming:  { cls: 'tag-blue',  label: '流式中', live: true },
  unknown:    { cls: 'tag-gray',  label: '未知' },
}
const info = computed(() => MAP[props.status] || { cls: 'tag-gray', label: props.status })
const cls = computed(() => info.value.cls)
const label = computed(() => info.value.label)
const live = computed(() => !!info.value.live)
</script>
