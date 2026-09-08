<template>
  <div class="bare-shell">
    <router-view />
    <AppToast />
  </div>
</template>

<script setup>
import AppToast from '../components/AppToast.vue'
</script>

<style scoped>
.bare-shell { min-height: 100vh; background: var(--ink-50); }
</style>
