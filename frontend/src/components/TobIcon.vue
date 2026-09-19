<script setup>
// 统一线条图标库:stroke 1.5 / 圆角端点,与全站图标风格一致
const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
})

const PATHS = {
  dashboard: '<rect x="3" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5"/>',
  box: '<path d="M21 8.5v7a2 2 0 0 1-1.1 1.8l-7 3.5a2 2 0 0 1-1.8 0l-7-3.5A2 2 0 0 1 3 15.5v-7a2 2 0 0 1 1.1-1.8l7-3.5a2 2 0 0 1 1.8 0l7 3.5A2 2 0 0 1 21 8.5Z"/><path d="m3.5 7.5 8.5 4.2 8.5-4.2"/><path d="M12 21v-9.3"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z"/>',
  receipt: '<path d="M5 3h14v18l-2.3-1.6-2.4 1.6-2.3-1.6L9.7 21l-2.4-1.6L5 21V3Z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',
  users: '<circle cx="9" cy="8.5" r="3.5"/><path d="M3.5 20c0-3 2.5-5 5.5-5s5.5 2 5.5 5"/><path d="M16 5.5a3 3 0 0 1 0 6M17.5 15.2c2 .7 3 2.3 3 4.8"/>',
  user: '<circle cx="12" cy="8" r="3.8"/><path d="M4.5 20.5c0-3.6 3-6 7.5-6s7.5 2.4 7.5 6"/>',
  scale: '<path d="M12 3v18M5 21h14"/><path d="M5 7h14l-2.8 6.5a4.4 4.4 0 0 1-8.4 0L5 7Z" transform="translate(0 -1)"/>',
  shield: '<path d="M12 3 5 5.8v5.4c0 4.4 3 7.6 7 9.8 4-2.2 7-5.4 7-9.8V5.8L12 3Z"/><path d="m9 11.5 2.2 2.2L15.5 9.5"/>',
  scroll: '<path d="M6 4h12a1.5 1.5 0 0 1 1.5 1.5v13A1.5 1.5 0 0 1 18 20H6a1.5 1.5 0 0 1-1.5-1.5v-13A1.5 1.5 0 0 1 6 4Z"/><path d="M8.5 8.5h7M8.5 12h7M8.5 15.5h4"/>',
  megaphone: '<path d="M3.5 10.5v3a1.5 1.5 0 0 0 1.5 1.5h1.8l7.7 4V5l-7.7 4H5a1.5 1.5 0 0 0-1.5 1.5Z"/><path d="M18 9a4.5 4.5 0 0 1 0 6"/>',
  tag: '<path d="M3.5 11.2V4.5a1 1 0 0 1 1-1h6.7a1 1 0 0 1 .7.3l8.3 8.3a1 1 0 0 1 0 1.4l-6.7 6.7a1 1 0 0 1-1.4 0l-8.3-8.3a1 1 0 0 1-.3-.7Z"/><circle cx="8" cy="8" r="1.4"/>',
  brain: '<path d="M9.5 3.5A2.8 2.8 0 0 0 6.7 6.3c-1.6.4-2.7 1.7-2.7 3.2 0 .9.4 1.7 1 2.3-.4.6-.6 1.3-.6 2 0 1.9 1.5 3.4 3.5 3.6.3 1.5 1.7 2.6 3.4 2.6V3.5c-.3 0-.6 0-.8 0Z"/><path d="M14.5 3.5a2.8 2.8 0 0 1 2.8 2.8c1.6.4 2.7 1.7 2.7 3.2 0 .9-.4 1.7-1 2.3.4.6.6 1.3.6 2 0 1.9-1.5 3.4-3.5 3.6-.3 1.5-1.7 2.6-3.4 2.6V3.5c.3 0 .6 0 .8 0Z"/><path d="M12 3.5v17"/>',
  book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15Z"/><path d="M4 18.2V20.5A2.5 2.5 0 0 1 6.5 18H20"/>',
  puzzle: '<path d="M10 3.5a1.8 1.8 0 0 1 3.6 0c0 .4-.1.7-.3 1H17a1 1 0 0 1 1 1v3.2c.3-.2.6-.3 1-.3a1.8 1.8 0 0 1 0 3.6c-.4 0-.7-.1-1-.3V15a1 1 0 0 1-1 1h-3.4c.2.3.3.6.3 1a1.8 1.8 0 0 1-3.6 0c0-.4.1-.7.3-1H7a1 1 0 0 1-1-1v-3.4c-.3.2-.6.3-1 .3a1.8 1.8 0 0 1 0-3.6c.4 0 .7.1 1 .3V5.5a1 1 0 0 1 1-1h3.7c-.2-.3-.3-.6-.3-1Z"/>',
  chart: '<path d="M4 4v16h16"/><path d="M8 16v-5M12.5 16V8M17 16v-3"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20.5 20.5-4.6-4.6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  refresh: '<path d="M20 11.5a8 8 0 1 0-.6 4.2"/><path d="M20 4.5v7h-7"/>',
  download: '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5"/><path d="M4.5 19.5h15"/>',
  check: '<path d="m4.5 12.5 5 5L19.5 6.5"/>',
  x: '<path d="M5.5 5.5l13 13M18.5 5.5l-13 13"/>',
  chevron: '<path d="m9 5.5 7 6.5-7 6.5"/>',
  arrowRight: '<path d="M4.5 12h15M14 6.5l5.5 5.5L14 17.5"/>',
  lock: '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  pin: '<path d="M12 21s-6.5-5.3-6.5-10.3a6.5 6.5 0 0 1 13 0C18.5 15.7 12 21 12 21Z"/><circle cx="12" cy="10.5" r="2.3"/>',
  spark: '<path d="M12 3.5 14 9.5l6 2-6 2-2 6-2-6-6-2 6-2 2-6Z"/>',
  doc: '<path d="M6 3.5h8L19 8.5v12H6v-17Z"/><path d="M13.5 3.5v5.5H19M9 13h6M9 16.5h6"/>',
  filter: '<path d="M4 6.5h16M7 12h10M10 17.5h4"/>',
  wand: '<path d="m5 19 10-10"/><path d="M14.5 5.5 16 4M19 8.5 20.5 7M18 13l1.5 1.5M12.5 4.5 11 3"/><path d="M15 9.5a2.8 2.8 0 0 0-4 4"/>',
}
</script>

<template>
  <svg
    :width="size" :height="size" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="1.5"
    stroke-linecap="round" stroke-linejoin="round"
    aria-hidden="true" v-html="PATHS[name] || ''" />
</template>
