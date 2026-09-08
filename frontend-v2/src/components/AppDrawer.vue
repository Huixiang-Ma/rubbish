<template>
  <Teleport to="body">
    <div class="drawer-mask" @click.self="$emit('close')">
      <div class="drawer">
        <div class="drawer-head">
          <div style="font-size:16.5px;font-weight:700">{{ title }}</div>
          <button class="btn btn-ghost btn-sm" @click="$emit('close')">关闭 ✕</button>
        </div>
        <div class="drawer-body"><slot /></div>
        <div v-if="$slots.foot" class="drawer-foot" style="padding:14px 24px;border-top:1px solid var(--ink-100);display:flex;gap:10px;justify-content:flex-end">
          <slot name="foot" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({ title: { type: String, default: '' } })
defineEmits(['close'])
</script>
