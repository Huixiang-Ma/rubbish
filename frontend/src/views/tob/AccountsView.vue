<script setup>
import { ref, onMounted } from 'vue'
import { authApi } from '../../api/index.js'

const ROLE_LABEL = { admin: '管理员 · 全部权限', supervisor: '主管 · 审批', consultant: '顾问 · 方案与客户' }

/* 企业账号：GET/POST /api/auth/tob/accounts + reset/delete（admin 专属） */
const FALLBACK = [
  { username: 'admin', display: '系统管理员', role: 'admin', tenant: 'TrailMind', source: 'builtin' },
  { username: 'supervisor', display: '审批主管', role: 'supervisor', tenant: 'TrailMind', source: 'builtin' },
]
const accounts = ref(FALLBACK)

async function load() {
  try {
    const res = await authApi.tobAccounts()
    const rows = (res && (res.accounts || res.items)) || []
    if (rows.length) accounts.value = rows
  } catch { /* 回退演示数据 */ }
}
onMounted(load)

const creating = ref(false)
const draft = ref({ username: '', display: '', password: '', role: 'consultant' })
async function createAccount() {
  if (!draft.value.username || !draft.value.password) return
  creating.value = true
  try {
    await authApi.tobAccountCreate({ ...draft.value })
    draft.value = { username: '', display: '', password: '', role: 'consultant' }
    await load()
  } catch (e) {
    window.alert(e.message || '创建失败')
  } finally { creating.value = false }
}
async function resetPwd(a) {
  const pwd = window.prompt(`为「${a.username}」设置新口令:`)
  if (!pwd) return
  try { await authApi.tobAccountReset(a.username, pwd); window.alert('口令已重置') }
  catch (e) { window.alert(e.message || '重置失败') }
}
async function delAccount(a) {
  if (!window.confirm(`确认删除账号「${a.username}」?`)) return
  try { await authApi.tobAccountDelete(a.username); await load() }
  catch (e) { window.alert(e.message || '删除失败') }
}
</script>

<template>
  <div class="tob-page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <div class="eyebrow">组织管理</div>
        <h1 class="page-title">企业账号</h1>
        <p class="page-desc">
          员工工作台账号发放 / 重置 / 停用。toB 账号由企业管理员内部发放,不开放自助注册;
          内置演示账号口令由 .env 管理,仅自建账号可重置与删除。
        </p>
      </div>
      <div class="page-actions">
        <span class="tag">账号 {{ accounts.length }} 个</span>
        <span class="tag tag-accent">自建 {{ accounts.filter(a => a.source === 'managed').length }} 个</span>
      </div>
    </div>

    <div class="acc-grid">
      <!-- 新建 -->
      <section class="card acc-form">
        <div class="pane-title">发放新账号</div>
        <div class="field">
          <label>账号(工号) <b>*</b></label>
          <input v-model.trim="draft.username" class="input" placeholder="如:wl_chen" />
        </div>
        <div class="field">
          <label>姓名 / 显示名</label>
          <input v-model.trim="draft.display" class="input" placeholder="如:陈顾问" />
        </div>
        <div class="field">
          <label>角色</label>
          <select v-model="draft.role" class="select">
            <option value="consultant">consultant · 顾问(方案与客户)</option>
            <option value="supervisor">supervisor · 主管(审批)</option>
            <option value="admin">admin · 管理员(全部权限)</option>
          </select>
        </div>
        <div class="field">
          <label>初始口令 <b>*</b></label>
          <input v-model="draft.password" class="input" type="text" placeholder="至少 6 位,发放后员工可请管理员重置" />
        </div>
        <button class="btn btn-primary" style="width:100%" :disabled="creating" @click="createAccount">发放账号</button>
      </section>

      <!-- 列表 -->
      <section class="card acc-list">
        <div class="pane-title">账号清单</div>
        <div class="acc-rows">
          <div v-for="a in accounts" :key="a.username" class="acc-row">
            <span class="avatar" :class="{ 'avatar-admin': a.role === 'admin' }">{{ a.display.slice(0, 1) }}</span>
            <div class="ar-body">
              <b>{{ a.display }}</b>
              <em>{{ a.username }} · {{ ROLE_LABEL[a.role] }}</em>
            </div>
            <span class="tag" :class="a.source === 'builtin' ? '' : 'tag-accent'">{{ a.source === 'builtin' ? '内置' : '自建' }}</span>
            <div class="ar-ops">
              <button v-if="a.source === 'managed'" class="btn btn-ghost btn-sm" @click="resetPwd(a)">重置口令</button>
              <button v-if="a.source === 'managed'" class="btn btn-ghost btn-sm" style="color:var(--danger)" @click="delAccount(a)">删除</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.acc-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: var(--s-4);
  align-items: start;
}
.acc-form { display: flex; flex-direction: column; gap: var(--s-4); }

.acc-list { display: flex; flex-direction: column; gap: var(--s-4); }
.acc-rows { display: flex; flex-direction: column; }
.acc-row {
  display: flex; align-items: center; gap: var(--s-4);
  padding: var(--s-3) 0;
  border-bottom: 1px solid var(--border-soft);
}
.acc-row:last-child { border-bottom: 0; }
.acc-row:hover .ar-body b { color: var(--accent); }
.avatar-admin { background: var(--accent-soft); color: var(--accent); }
.ar-body { flex: 1; display: flex; flex-direction: column; line-height: 1.35; min-width: 0; }
.ar-body b { font-size: var(--fs-sm); font-weight: var(--fw-medium); transition: color var(--dur-1) var(--ease); }
.ar-body em { font-style: normal; font-size: var(--fs-xs); color: var(--text-faint); }
.ar-ops { display: flex; gap: var(--s-2); }

@media (max-width: 1000px) {
  .acc-grid { grid-template-columns: 1fr; }
}
</style>
