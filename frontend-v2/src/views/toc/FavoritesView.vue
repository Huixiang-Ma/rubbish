<template>
  <div class="container fv">
    <div class="fv-head">
      <h1>❤️ 我的收藏</h1>
      <p>收藏的整订线路方案：看到想去的先收着，定下来随时下单</p>
    </div>

    <div v-if="loading" class="load-wrap"><div class="spinner"></div></div>

    <template v-else>
      <div v-if="!items.length" class="empty card big">
        <div class="icon">🤍</div>
        <p>还没有收藏任何方案。</p>
        <p class="sub">去方案馆挑一条排好的线路，点「收藏方案」就会出现在这里</p>
        <router-link :to="{ name: 'malls' }" class="btn btn-primary">去逛方案馆</router-link>
      </div>

      <div v-else class="grid">
        <div v-for="p in items" :key="p.id" class="shop-card card">
          <router-link :to="{ name: 'malls-product', params: { id: p.id } }" class="cover-link">
            <span class="shop-cover" :style="{ background: p.cover.gradient }">
              <span class="shop-emoji">{{ p.cover.emoji }}</span>
              <span class="days-chip">{{ p.days }} 日</span>
            </span>
          </router-link>
          <div class="shop-body">
            <div class="shop-top">
              <span class="shop-cat">{{ p.category }}</span>
              <span class="shop-city">📍{{ p.city }}</span>
            </div>
            <router-link :to="{ name: 'malls-product', params: { id: p.id } }" class="shop-name">{{ p.name }}</router-link>
            <div class="shop-meta">
              <span>★ {{ Number(p.rating).toFixed(1) }}</span>
              <span>{{ p.poi_count }} 点位 · {{ p.pace_zh }}</span>
            </div>
            <div class="shop-foot">
              <div class="shop-price"><span class="y">¥</span><b>{{ p.per_price }}</b><span class="suffix">/人 整订</span></div>
              <button class="btn btn-ghost btn-sm like-on" @click="unlike(p)">❤️ 取消收藏</button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { favApi } from '../../api'
import { toast } from '../../composables/toast'

const items = ref([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const r = await favApi.list()
    items.value = r.items || []
  } finally { loading.value = false }
}

async function unlike(p) {
  await favApi.remove(p.id)
  toast('已取消收藏', 'ok')
  await load()
}

onMounted(load)
</script>

<style scoped>
.fv { max-width: 1080px; padding: 26px 0 50px; }
.fv-head h1 { font-size: 24px; font-weight: 900; color: var(--ink-900); margin: 0; }
.fv-head p { font-size: 13px; color: var(--ink-500); margin: 4px 0 20px; }
.load-wrap { text-align: center; padding: 70px 0; }
.empty { text-align: center; padding: 60px 20px; }
.empty .sub { font-size: 13px; color: var(--ink-400); margin-bottom: 18px; }
.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.shop-card { padding: 0; overflow: hidden; }
.cover-link { display: block; }
.shop-cover { display: block; aspect-ratio: 4/3; display: flex; align-items: center; justify-content: center; position: relative; }
.shop-emoji { font-size: 70px; filter: drop-shadow(0 4px 8px rgba(0,0,0,.16)); }
.days-chip { position: absolute; left: 10px; top: 10px; background: rgba(0,0,0,.48); color: #fff; font-size: 11px; padding: 3px 9px; border-radius: 999px; backdrop-filter: blur(6px); }
.shop-body { padding: 12px 15px 14px; }
.shop-top { display: flex; justify-content: space-between; align-items: center; }
.shop-cat { font-size: 11px; font-weight: 700; color: var(--brand-700); background: var(--brand-50); padding: 2px 7px; border-radius: 4px; }
.shop-city { font-size: 11.5px; color: var(--ink-400); }
.shop-name { display: block; font-weight: 800; font-size: 14.5px; color: var(--ink-900); text-decoration: none !important; margin: 7px 0 0; line-height: 1.35; }
.shop-name:hover { color: var(--brand-700); }
.shop-meta { display: flex; gap: 12px; font-size: 12px; color: var(--ink-400); margin-top: 6px; }
.shop-foot { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 10px; }
.shop-price { display: flex; align-items: baseline; gap: 2px; }
.shop-price .y { font-size: 12px; color: var(--danger); font-weight: 700; }
.shop-price b { font-size: 20px; color: var(--danger); font-weight: 900; }
.shop-price .suffix { font-size: 11px; color: var(--ink-400); }
.like-on { color: var(--danger); border-color: #fecaca; }
@media (max-width: 1080px) { .grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 800px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 500px) { .grid { grid-template-columns: 1fr; } }
</style>
