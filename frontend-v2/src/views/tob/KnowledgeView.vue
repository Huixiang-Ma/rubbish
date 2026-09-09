<template>
  <div class="kb">
    <header class="kb-head">
      <div>
        <h1>📚 知识库文档 <small>RAG 语料构建：攻略 / 注意事项 / 常见问题</small></h1>
        <p class="hint">
          上传的文档会被分块摄入语义检索层（与标品语料、用户高分行程攻略同一知识库），
          toC 的 AI 导游问答与智能助手随即可以引用。支持 Markdown / 纯文本，按空行分段。
        </p>
      </div>
      <div class="head-stats">
        <span>文档 <b>{{ docs.length }}</b> 篇</span>
        <span>语料块 <b>{{ totalChunks }}</b> 块</span>
      </div>
    </header>

    <div class="kb-grid">
      <!-- 左：上传/编辑 -->
      <section class="card kb-form">
        <h3>{{ editingId ? '✏️ 编辑文档' : '＋ 新建文档' }}</h3>
        <label class="kf-field"><span>标题 <b>*</b></span>
          <input v-model.trim="f.title" class="input" maxlength="60" placeholder="如：苏州园林游览注意事项" /></label>
        <label class="kf-field"><span>标签（逗号分隔）</span>
          <input v-model.trim="f.tags" class="input" placeholder="苏州, 注意事项" /></label>
        <label class="kf-field"><span>正文 <b>*</b>（空行分段）</span>
          <textarea v-model="f.content" class="textarea" rows="12" placeholder="拙政园需提前一天实名预约…&#10;&#10;狮子林假山洞适合儿童游玩…"></textarea></label>
        <div class="kf-actions">
          <button class="btn btn-primary" :disabled="saving || !f.title || !f.content" @click="save">
            {{ saving ? '摄入中…' : (editingId ? '保存并重新摄入' : '上传并摄入知识库') }}
          </button>
          <button v-if="editingId" class="btn btn-ghost" @click="resetForm">取消编辑</button>
        </div>
        <p class="kf-tip">摄入后 RAG 立即可检索；检索层不可用时文档仍保留台账，待服务恢复后重传。</p>
      </section>

      <!-- 右：文档列表 -->
      <section class="card kb-list">
        <h3>已入库文档</h3>
        <div v-if="loading" class="kb-loading"><span class="spinner"></span> 加载中…</div>
        <div v-else-if="!docs.length" class="kb-empty">还没有文档，从左侧上传第一篇攻略吧</div>
        <div v-else class="kb-rows">
          <div v-for="d in docs" :key="d.id" class="kb-row">
            <div class="kr-body">
              <b>{{ d.title }}</b>
              <em>{{ d.chunks }} 块 · {{ d.chars }} 字 · {{ d.mode }} · {{ d.created_at }}</em>
              <div class="kr-tags" v-if="d.tags && d.tags.length">
                <span v-for="t in d.tags" :key="t" class="kr-tag">{{ t }}</span>
              </div>
            </div>
            <div class="kr-ops">
              <button class="btn btn-ghost btn-sm" @click="edit(d)">编辑</button>
              <button class="btn btn-danger btn-sm" @click="removeOne(d)">删除</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
// 需求2（toB）：知识库文档构建 —— 文档分块摄入语义层（kb: 前缀），与标品语料共用 RAG
import { ref, reactive, computed, onMounted } from 'vue'
import { assistApi } from '../../api'
import { toast } from '../../composables/toast'

const docs = ref([])
const loading = ref(true)
const saving = ref(false)
const editingId = ref('')
const f = reactive({ title: '', tags: '', content: '' })

const totalChunks = computed(() => docs.value.reduce((s, d) => s + (d.chunks || 0), 0))

async function load() {
  loading.value = true
  try {
    const r = await assistApi.kbList()
    docs.value = r.docs || []
  } catch (e) { toast('知识库加载失败：' + (e.message || e), 'err') } finally { loading.value = false }
}

function resetForm() {
  editingId.value = ''
  f.title = ''; f.tags = ''; f.content = ''
}

function edit(d) {
  editingId.value = d.id
  f.title = d.title
  f.tags = (d.tags || []).join(', ')
  // 编辑时正文不在台账里（只在检索层），给占位提示
  f.content = f.content || ''
  toast('编辑将重新摄入全文，请在正文框粘贴最新版内容', 'info')
}

async function save() {
  saving.value = true
  try {
    const r = await assistApi.kbCreate({
      title: f.title,
      content: f.content,
      tags: f.tags.split(/[,，]/).map(x => x.trim()).filter(Boolean),
    })
    toast(`已摄入：${r.chunks} 块语料（${r.mode}）`, 'ok')
    resetForm()
    await load()
  } catch (e) { toast(e.message || '摄入失败', 'err') } finally { saving.value = false }
}

async function removeOne(d) {
  if (!confirm(`删除文档「${d.title}」？其语料块将从检索层移除。`)) return
  try {
    await assistApi.kbDelete(d.id)
    toast('已删除', 'ok')
    await load()
  } catch (e) { toast(e.message || '删除失败', 'err') }
}

onMounted(load)
</script>

<style scoped>
.kb { display: flex; flex-direction: column; gap: 16px; }
.kb-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.kb-head h1 { font-size: 21px; font-weight: 800; margin: 0; }
.kb-head h1 small { font-size: 12px; font-weight: 600; color: var(--text-faint); margin-left: 8px; }
.hint { color: var(--text-dim); font-size: 13px; margin: 6px 0 0; max-width: 720px; line-height: 1.7; }
.head-stats { display: flex; gap: 16px; font-size: 12.5px; color: var(--text-faint); }
.head-stats b { color: var(--text); font-size: 14px; }

.kb-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: start; }
.kb-form, .kb-list { padding: 18px 20px; }
.kb-form h3, .kb-list h3 { margin: 0 0 12px; font-size: 15px; }
.kf-field { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; }
.kf-field span { font-size: 12.5px; font-weight: 700; color: var(--text-dim); }
.kf-field span b { color: var(--danger); }
.kf-actions { display: flex; gap: 10px; }
.kf-tip { font-size: 11.5px; color: var(--text-faint); margin: 10px 0 0; }
.kb-loading, .kb-empty { padding: 40px 0; text-align: center; color: var(--text-faint); font-size: 13px; }
.kb-rows { display: flex; flex-direction: column; gap: 8px; max-height: 480px; overflow-y: auto; }
.kb-row { display: flex; justify-content: space-between; gap: 10px; align-items: center; border: 1px solid var(--line); border-radius: 11px; padding: 10px 13px; }
.kr-body b { display: block; font-size: 13.5px; }
.kr-body em { font-style: normal; font-size: 11.5px; color: var(--text-faint); }
.kr-tags { margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap; }
.kr-tag { font-size: 10.5px; background: var(--bg-hover); color: var(--text-dim); padding: 1px 8px; border-radius: 999px; }
.kr-ops { display: flex; gap: 6px; flex: none; }
@media (max-width: 1000px) { .kb-grid { grid-template-columns: 1fr; } }
</style>
