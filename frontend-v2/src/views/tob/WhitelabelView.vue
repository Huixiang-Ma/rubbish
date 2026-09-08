<template>
  <div>
    <div class="page-head">
      <div>
        <h1>白标交付</h1>
        <div class="desc" style="color:var(--text-faint)">把行程书打上企业品牌与顾问署名，生成交付版 Markdown（头部含中立声明）</div>
      </div>
    </div>

    <div class="grid">
      <div class="card card-pad">
        <div class="field" style="margin-bottom:14px">
          <label>任务 job_id *</label>
          <input v-model.trim="form.job_id" class="input" placeholder="plan_xxxx（从方案列表复制）" />
        </div>
        <div class="field" style="margin-bottom:14px">
          <label>企业品牌名 *</label>
          <input v-model.trim="form.brand" class="input" placeholder="如：远山国际旅行社" />
        </div>
        <div class="field" style="margin-bottom:18px">
          <label>顾问署名</label>
          <input v-model.trim="form.consultant" class="input" placeholder="如：行程顾问 · 王雅" />
        </div>
        <button class="btn btn-primary btn-block" :disabled="!form.job_id || !form.brand || busy" @click="exportIt">
          {{ busy ? '生成中…' : '🏷 生成交付版' }}</button>
      </div>

      <div class="card card-pad">
        <div v-if="!result" class="empty" style="padding:40px 12px"><div class="icon">🏷</div><p>生成后在此预览交付版行程书</p></div>
        <template v-else>
          <div class="ok-line">
            <span class="tag tag-green">✓ 已生成 travel_plan_branded.md</span>
            <span class="sha">sha256: {{ result.sha256?.slice(0, 20) }}…</span>
          </div>
          <div style="margin-top:14px">
            <MdView :source="result.travel_plan_md || preview" />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { plansApi } from '../../api'
import { toast } from '../../composables/toast'
import MdView from '../../components/MdView.vue'

const form = reactive({ job_id: '', brand: '', consultant: '' })
const busy = ref(false)
const result = ref(null)
const preview = ref('')

async function exportIt() {
  busy.value = true
  try {
    const r = await plansApi.export(form.job_id, { brand: form.brand, consultant: form.consultant })
    result.value = r
    // 交付文件在服务端 data/jobs/<id>/travel_plan_branded.md；取原行程书做预览对照
    try {
      const orig = await plansApi.result(form.job_id)
      preview.value = (orig.travel_plan_md || '')
        .replace(/^# .*$/m, `# ${form.brand} · 定制行程方案`)
      if (form.consultant) preview.value += `\n\n---\n> 顾问署名：${form.consultant}`
    } catch { preview.value = '' }
    toast('白标交付版已生成', 'ok')
  } catch (e) { toast(e.message, 'err') } finally { busy.value = false }
}
</script>

<style scoped>
.grid { display: grid; grid-template-columns: 360px 1fr; gap: 16px; align-items: start; }
@media (max-width: 1000px) { .grid { grid-template-columns: 1fr; } }
.ok-line { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.sha { font-family: var(--mono); font-size: 11.5px; color: var(--text-faint); }
</style>
