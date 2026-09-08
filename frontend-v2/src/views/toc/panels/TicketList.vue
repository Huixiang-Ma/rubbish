<template>
  <div>
    <div v-if="!tickets.length" class="empty"><p>暂无班次数据</p></div>
    <div class="t-list">
      <div v-for="(t, i) in tickets" :key="i" class="card t-row">
        <div class="t-no">
          <b>{{ t.train_no || t.flight_no || t.no || '—' }}</b>
          <span v-if="t.tag" class="tag tag-blue">{{ t.tag }}</span>
        </div>
        <div class="t-route">
          <div class="t-city">{{ t.departure }}</div>
          <div class="t-dur">⟶ {{ t.duration || '' }}</div>
          <div class="t-city">{{ t.arrival }}</div>
        </div>
        <div class="t-side">
          <div class="t-price">¥{{ t.price }}</div>
          <div class="t-seat">{{ t.seat }}<template v-if="t.status"> · {{ t.status }}</template></div>
        </div>
        <a v-if="t.booking_url" class="btn btn-primary btn-sm" :href="t.booking_url" target="_blank" rel="noopener"
           @click="$emit('book', kind)">订</a>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ tickets: { type: Array, default: () => [] }, kind: { type: String, default: 'train' } })
defineEmits(['book'])
</script>

<style scoped>
.t-list { display: flex; flex-direction: column; gap: 10px; }
.t-row { padding: 15px 20px; display: grid; grid-template-columns: 150px 1fr auto auto; gap: 16px; align-items: center; }
.t-no b { font-family: var(--mono); font-size: 15px; }
.t-route { display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: center; }
.t-city { font-weight: 700; font-size: 14.5px; }
.t-dur { text-align: center; font-size: 12px; color: var(--ink-400); }
.t-side { text-align: right; }
.t-price { font-weight: 900; color: #DC2626; font-size: 17px; }
.t-seat { font-size: 12px; color: var(--ink-400); }
@media (max-width: 760px) { .t-row { grid-template-columns: 1fr auto; } }
</style>
