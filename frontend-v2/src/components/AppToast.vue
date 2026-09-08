<template>
  <div class="toast-wrap">
    <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
      <span>{{ t.type === 'ok' ? '✓' : t.type === 'err' ? '✕' : 'ℹ' }}</span>
      <span>{{ t.msg }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onToast } from '../composables/toast'

const toasts = ref([])
const off = onToast((t) => {
  toasts.value.push(t)
  setTimeout(() => { toasts.value = toasts.value.filter(x => x.id !== t.id) }, 3400)
})
onUnmounted(off)
</script>
