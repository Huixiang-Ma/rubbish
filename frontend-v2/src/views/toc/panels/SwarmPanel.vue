<template>
  <div>
    <!-- swarm 踩点 -->
    <div class="sec-title">虚拟游客踩点</div>
    <p class="sec-desc">不同人设的虚拟游客提前"走"一遍行程，带回一手体感</p>
    <div v-if="!reports.length" class="empty"><div class="icon">👥</div><p>暂无踩点报告（任务完成后生成）</p></div>
    <div class="swarm">
      <div v-for="(r, i) in reports" :key="i" class="card sw-card">
        <div class="sw-top">
          <span class="sw-avatar">{{ r.persona?.[0] || '客' }}</span>
          <div>
            <div class="sw-name">{{ r.persona }} <span class="tag tag-gray" style="margin-left:6px">{{ r.style }}</span></div>
            <div class="sw-meta">Day{{ r.day }} · {{ r.theme }}</div>
          </div>
          <span class="tag" :class="verdictCls(r.verdict)">{{ r.verdict }}</span>
        </div>
        <p class="sw-tip">💡 {{ r.tip }}</p>
      </div>
    </div>

    <!-- 反事实 -->
    <div class="sec-title" style="margin-top:48px">反事实后悔药</div>
    <p class="sec-desc">如果当初做了另一种选择，会得到什么、又错过什么</p>
    <div v-if="!cards.length" class="empty"><div class="icon">🔮</div><p>暂无对照卡（任务完成后生成）</p></div>
    <div class="cf">
      <div v-for="(c, i) in cards" :key="i" class="card cf-card">
        <div class="cf-gave"><span class="cf-label">❌ 放弃了</span>{{ c.gave_up }}</div>
        <div class="cf-arrow">→</div>
        <div class="cf-got"><span class="cf-label">✅ 得到了</span>{{ c.got }}</div>
        <p class="cf-reason">{{ c.reason }}</p>
        <div v-if="c.cost_note" class="cf-cost">💰 {{ c.cost_note }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { expApi } from '../../../api'

const props = defineProps({ jobId: { type: String, required: true } })

const reports = ref([])
const cards = ref([])

function verdictCls(v) {
  if (!v) return 'tag-gray'
  if (v.includes('很棒') || v.includes('推荐') || v.includes('赞')) return 'tag-green'
  if (v.includes('累') || v.includes('赶') || v.includes('坑')) return 'tag-amber'
  return 'tag-blue'
}

onMounted(async () => {
  try { reports.value = (await expApi.swarm(props.jobId)).reports || [] } catch {}
  try { cards.value = (await expApi.counterfactual(props.jobId)).cards || [] } catch {}
})
</script>

<style scoped>
.swarm { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.sw-card { padding: 20px 22px; }
.sw-top { display: flex; align-items: center; gap: 12px; }
.sw-top .tag { margin-left: auto; }
.sw-avatar {
  width: 40px; height: 40px; border-radius: 50%; flex: none;
  background: linear-gradient(135deg, #F59E0B, #F97316); color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 17px;
}
.sw-name { font-weight: 700; font-size: 14.5px; }
.sw-meta { font-size: 12px; color: var(--ink-400); margin-top: 1px; }
.sw-tip { font-size: 13.5px; color: var(--ink-700); margin-top: 12px; line-height: 1.7; background: var(--ink-50); border-radius: var(--r-sm); padding: 10px 14px; }

.cf { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
.cf-card { padding: 20px 22px; }
.cf-label { display: block; font-size: 11.5px; font-weight: 700; letter-spacing: .06em; margin-bottom: 3px; }
.cf-gave .cf-label { color: #B91C1C; }
.cf-got .cf-label { color: #047857; }
.cf-gave, .cf-got { font-size: 14px; font-weight: 600; }
.cf-arrow { color: var(--ink-300, var(--ink-400)); font-weight: 900; margin: 6px 0; font-size: 16px; }
.cf-reason { font-size: 13px; color: var(--ink-500); margin-top: 10px; line-height: 1.7; }
.cf-cost { font-size: 12.5px; color: #B45309; background: var(--warn-bg); border-radius: var(--r-sm); padding: 6px 12px; margin-top: 10px; display: inline-block; }
</style>
