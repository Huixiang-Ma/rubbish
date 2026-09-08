<template>
  <div class="ch-line">
    <span class="ch-label">官方购票渠道指引：</span>
    <a v-for="c in channels" :key="c.name" class="ch-item" :href="c.url" target="_blank" rel="noopener">
      <b>{{ c.name }}</b><span v-if="c.desc"> · {{ c.desc }}</span> ↗
    </a>
  </div>
</template>

<script setup>
defineProps({ channels: { type: Array, default: () => [] } })
</script>

<style scoped>
.ch-line { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 12px; padding: 11px 16px; background: var(--ink-50); border-radius: var(--r-sm); font-size: 12.5px; align-items: center; }
.ch-label { color: var(--ink-400); }
.ch-item { color: var(--brand-600); font-size: 12.5px; text-decoration: none; }
.ch-item:hover { text-decoration: underline; }
.ch-item b { font-weight: 700; }
</style>
