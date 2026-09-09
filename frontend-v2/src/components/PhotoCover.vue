<template>
  <div class="pc-cover" :style="{ background: cover?.gradient || 'linear-gradient(135deg,#E2E8F0,#94A3B8)' }">
    <template v-if="photos && photos.length">
      <img v-for="(ph, i) in photos" :key="ph.url" v-show="idx % photos.length === i"
           class="pc-photo" :src="ph.url" :alt="ph.name" loading="lazy" />
      <div v-if="photos.length > 1" class="pc-dots">
        <i v-for="(ph, i) in photos" :key="i" :class="{ on: idx % photos.length === i }" />
      </div>
    </template>
    <span v-else class="pc-emoji">{{ cover?.emoji || '🧭' }}</span>
    <slot />
  </div>
</template>

<script setup>
// 方案封面轮播（需求5）：高德 POI 实拍图轮换，无图回落 emoji 封面
// 由父组件轮询定时器驱动 idx（或本组件自转：auto）
import { ref, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  cover: { type: Object, default: null },
  photos: { type: Array, default: () => [] },
  auto: { type: Boolean, default: false },  // true = 组件自己轮换（首页精选）
  interval: { type: Number, default: 3500 },
})
const idx = ref(0)
let timer = null
onMounted(() => {
  if (props.auto && props.photos.length > 1) {
    timer = setInterval(() => { idx.value++ }, props.interval)
  }
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.pc-cover { aspect-ratio: 4/3; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; }
.pc-photo { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; animation: pcIn .5s ease; }
@keyframes pcIn { from { opacity: 0; transform: scale(1.04); } to { opacity: 1; transform: scale(1); } }
.pc-dots { position: absolute; bottom: 8px; left: 0; right: 0; display: flex; justify-content: center; gap: 5px; z-index: 2; }
.pc-dots i { width: 6px; height: 6px; border-radius: 999px; background: rgba(255,255,255,.55); transition: all .25s; }
.pc-dots i.on { background: #fff; width: 14px; }
.pc-emoji { font-size: 56px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.18)); }
.pc-cover :deep(.shop-badges), .pc-cover :deep(.days-chip) { z-index: 2; }
</style>
