<template>
  <div class="sec">
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:4px">
      <div class="sec-title" style="margin:0">{{ title }}</div>
      <slot name="extra" />
    </div>
    <p v-if="desc" class="sec-desc">{{ desc }}</p>
    <div v-if="source" class="src-line">
      <span class="tag" :class="source === 'fliggy' ? 'tag-green' : 'tag-gray'">
        {{ source === 'fliggy' ? '⚡ 飞猪实时检索' : '📍 本地口径与官方渠道' }}
      </span>
      <span v-if="note" class="src-note">{{ note }}</span>
    </div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: String,
  source: String,
  note: String,
  desc: String,
})
</script>

<style scoped>
.sec { margin-top: 30px; }
.src-line { display: flex; align-items: center; gap: 10px; margin: -8px 0 14px; flex-wrap: wrap; }
.src-note { font-size: 12.5px; color: var(--ink-400); }
</style>
