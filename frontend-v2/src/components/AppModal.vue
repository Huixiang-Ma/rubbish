<template>
  <Teleport to="body">
    <div class="modal-mask" @click.self="$emit('close')">
      <div class="modal">
        <div class="modal-head">{{ title }}</div>
        <div class="modal-body"><slot /></div>
        <div class="modal-foot">
          <button class="btn btn-ghost" @click="$emit('close')">取消</button>
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
