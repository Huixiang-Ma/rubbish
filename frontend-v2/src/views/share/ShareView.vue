<template>
  <div class="share-shell">
    <header class="s-head">
      <div class="s-brand"><span class="mark">迹</span>迹程智游 · 行程分享</div>
      <router-link :to="{ name: 'home' }" class="s-cta">我也要生成一份 →</router-link>
    </header>

    <main class="s-main container">
      <div v-if="loading" class="loading-block card"><div class="spinner spin"></div>加载行程书…</div>

      <div v-else-if="err" class="empty card">
        <div class="icon">🔒</div>
        <p>{{ err }}</p>
        <p style="font-size:12px;margin-top:6px">分享链接仅对有效任务开放，且不可枚举</p>
      </div>

      <template v-else>
        <div class="s-meta card card-pad">
          <div class="m-row">
            <StatusTag :status="jobStatus" />
            <b class="m-dest">{{ destination }}</b>
            <span class="m-info">{{ metaText }}</span>
            <span class="m-ver tag tag-gray">v{{ result.version }}</span>
          </div>
          <div class="m-note">📕 只读分享页 · 由 10 个智能体协作生成 · 内容含审计可追溯信息（sha256: {{ result.sha256?.slice(0, 16) }}…）</div>
        </div>
        <div class="s-book card card-pad" style="margin-top:16px">
          <MdView :source="result.travel_plan_md" />
        </div>
      </template>
    </main>

    <AppToast />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { plansApi } from '../../api'
import StatusTag from '../../components/StatusTag.vue'
import MdView from '../../components/MdView.vue'
import AppToast from '../../components/AppToast.vue'

const route = useRoute()
const jobId = route.params.jobId

const loading = ref(true)
const err = ref('')
const result = ref(null)
const status = ref('')

const destination = computed(() => result.value?.user_input?.destination || '行程方案')
const jobStatus = computed(() => status.value || 'COMPLETED')
const metaText = computed(() => {
  const u = result.value?.user_input || {}
  const parts = []
  if (u.days) parts.push(`${u.days} 天`)
  if (u.budget != null) parts.push(`预算 ¥${Number(u.budget).toLocaleString()}`)
  if (u.origin) parts.push(`${u.origin} 出发`)
  return parts.join(' · ')
})

onMounted(async () => {
  try {
    result.value = await plansApi.result(jobId)
  } catch (e) {
    err.value = e.status === 404 ? '行程不存在或尚未生成完成' : `加载失败：${e.message}`
  } finally { loading.value = false }
  try { status.value = (await plansApi.status(jobId)).status } catch {}
})
</script>

<style scoped>
.share-shell { min-height: 100vh; background:
  radial-gradient(1000px 400px at 90% -8%, rgba(245,158,11,.07), transparent 60%),
  radial-gradient(900px 400px at -5% 0%, rgba(37,99,235,.07), transparent 55%), var(--ink-50); }
.s-head {
  height: var(--nav-h); background: rgba(255,255,255,.85); backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--ink-100); display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; position: sticky; top: 0; z-index: 20;
}
.s-brand { display: flex; align-items: center; gap: 10px; font-weight: 800; color: var(--ink-900); }
.s-brand .mark {
  width: 32px; height: 32px; border-radius: 9px; background: linear-gradient(135deg, var(--brand-600), var(--brand-400));
  color: #fff; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 800;
}
.s-cta { font-size: 13.5px; font-weight: 700; text-decoration: none; }
.s-main { padding: 32px 24px 64px; }
.s-meta .m-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.m-dest { font-size: 20px; font-weight: 900; letter-spacing: -.01em; }
.m-info { font-size: 13.5px; color: var(--ink-500); }
.m-ver { margin-left: auto; }
.m-note { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--ink-200); font-size: 12.5px; color: var(--ink-400); }
.s-book { margin-top: 0; }
</style>
