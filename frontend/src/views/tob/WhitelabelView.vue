<script setup>
import { ref, reactive } from 'vue'
import { plansApi } from '../../api/index.js'

const form = reactive({ job_id: '', brand: '', consultant: '' })
const generated = ref(false)
const exporting = ref(false)
const errMsg = ref('')

/* 白标交付：POST /api/plans/{job_id}/export（注入品牌与顾问署名另存） */
async function exportIt() {
  if (exporting.value) return
  errMsg.value = ''
  exporting.value = true
  try {
    await plansApi.export(form.job_id.trim(), { brand: form.brand.trim(), consultant: form.consultant.trim() })
    generated.value = true
  } catch (e) {
    errMsg.value = e.message || '导出失败,请检查任务 ID'
    generated.value = false
  } finally { exporting.value = false }
}
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">交付 · 品牌</div>
        <h1 class="page-title">白标交付</h1>
        <p class="page-desc">把行程书打上企业品牌与顾问署名,生成交付版 Markdown(头部含中立声明)</p>
      </div>
    </div>

    <div class="wl-grid">
      <!-- 表单 -->
      <div class="card wl-form">
        <div class="pane-title">交付配置</div>
        <div class="field">
          <label>任务 job_id <b>*</b></label>
          <input v-model.trim="form.job_id" class="input" placeholder="plan_xxxx(从方案列表复制)" />
        </div>
        <div class="field">
          <label>企业品牌名 <b>*</b></label>
          <input v-model.trim="form.brand" class="input" placeholder="如:远山国际旅行社" />
        </div>
        <div class="field">
          <label>顾问署名</label>
          <input v-model.trim="form.consultant" class="input" placeholder="如:行程顾问 · 王雅" />
        </div>
        <button class="btn btn-primary" style="width:100%" :disabled="!form.job_id || !form.brand" @click="exportIt">
          生成交付版
        </button>
        <p class="wl-tip">生成文件:travel_plan_branded.md,头部将附加品牌信息与中立声明。</p>
      </div>

      <!-- 预览 -->
      <div class="card wl-preview">
        <template v-if="!generated">
          <div class="empty-box">
            <div class="e-title">尚未生成</div>
            <p>填写左侧配置并点击「生成交付版」,此处将预览打上品牌与署名的行程书。</p>
          </div>
        </template>
        <template v-else>
          <div class="ok-line">
            <span class="tag tag-ok">已生成 travel_plan_branded.md</span>
            <span class="mono-xs">sha256: 8f3a1c9d2e4b…</span>
          </div>
          <div class="md-doc">
            <h1>{{ form.brand }} · 定制行程方案</h1>
            <p class="md-meta">目的地 苏州 · 3 天 2 晚 · 出发地 上海 · 人均预算 ¥3,200</p>
            <hr />
            <h2>第 1 天 · 初见姑苏</h2>
            <p><b>上午</b> 抵达苏州站,专车接站 → <b>拙政园</b>(建议时段 09:30-12:00,提前一日实名预约)。园林以水为中心,山水萦绕,厅榭精美,建议跟随语音导览慢行约 2.5 小时。</p>
            <p><b>下午</b> 平江路历史街区自由漫步,可选 <b>摇橹船夜游</b>(19:00 场次,水巷灯影体验约 40 分钟)。</p>
            <p><b>晚餐</b> 苏帮菜 · 松鹤楼(已按 2 人预留 18:00 位,人均 ¥158-268)。</p>
            <h2>第 2 天 · 水巷与评弹</h2>
            <p><b>上午</b> 山塘街 + 虎丘(交通:地铁 2 号线转有轨,约 40 分钟)。</p>
            <p><b>下午</b> 苏州博物馆(需提前预约)→ 平江府下午茶。</p>
            <p><b>晚间</b> 评弹书场,感受"中国最美声音"。</p>
            <h2>第 3 天 · 返程</h2>
            <p><b>上午</b> 金鸡湖晨间漫步 → 诚品书店选购伴手礼;12:00 前退房,专车送站。</p>
            <hr />
            <p class="md-note">> 本方案由智能行程规划系统生成并经人工顾问审核,信息以当日营业公告为准。<br />> 顾问署名:{{ form.consultant }}</p>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wl-grid {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: var(--s-4);
  align-items: start;
}
.wl-form { display: flex; flex-direction: column; gap: var(--s-4); }
.wl-tip { font-size: var(--fs-xs); color: var(--text-faint); line-height: var(--lh-base); }

.wl-preview { min-height: 420px; }
.ok-line { display: flex; align-items: center; gap: var(--s-4); flex-wrap: wrap; margin-bottom: var(--s-4); }

.md-doc {
  background: var(--surface-2);
  border: 1px solid var(--border-soft);
  border-radius: var(--r);
  padding: var(--s-6);
  font-size: var(--fs-sm);
  color: var(--text-2);
  line-height: var(--lh-loose);
}
.md-doc h1 { font-size: var(--fs-lg); margin-bottom: var(--s-2); }
.md-doc h2 { font-size: var(--fs-base); margin: var(--s-5) 0 var(--s-2); }
.md-doc hr { border: 0; border-top: 1px solid var(--border-soft); margin: var(--s-4) 0; }
.md-meta { color: var(--text-3); font-size: var(--fs-xs); }
.md-note { color: var(--text-faint); font-size: var(--fs-xs); }
.md-doc b { color: var(--text); font-weight: var(--fw-medium); }

@media (max-width: 1000px) { .wl-grid { grid-template-columns: 1fr; } }
</style>
