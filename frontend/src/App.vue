<script setup>
import { computed } from 'vue'
import { useRoute, RouterView } from 'vue-router'
import MainLayout from './layouts/MainLayout.vue'
import TobLayout from './layouts/TobLayout.vue'

const route = useRoute()
const isBare = computed(() => route.meta.bare === true)
const isTob = computed(() => route.meta.tob === true && !isBare.value)
</script>

<template>
  <RouterView v-if="isBare" />
  <component :is="isTob ? TobLayout : MainLayout" v-else />
</template>

<style>
.fade-enter-active,
.fade-leave-active { transition: opacity .28s var(--ease), transform .28s var(--ease); }
.fade-enter-from { opacity: 0; transform: translateY(6px); }
.fade-leave-to   { opacity: 0; transform: translateY(-4px); }
</style>
