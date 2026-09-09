<template>
  <div class="acc">
    <header class="acc-head">
      <div>
        <h1>👤 企业账号管理 <small>员工工作台账号发放 / 重置 / 停用</small></h1>
        <p class="hint">
          toB 账号由企业管理员内部发放，不开放自助注册。内置演示账号（admin / supervisor / consultant）
          口令由 .env 管理，仅自建账号可重置与删除。
        </p>
      </div>
      <div class="head-stats">
        <span>账号 <b>{{ accounts.length }}</b> 个</span>
        <span>自建 <b>{{ managedCount }}</b> 个</span>
      </div>
    </header>

    <div class="acc-grid">
      <!-- 新建 -->
      <section class="card acc-form">
        <h3>＋ 发放新账号</h3>
        <label class="af"><span>账号（工号）<b>*</b></span>
          <input v-model.trim="f.username" class="input" maxlength="40" placeholder="如：wl_chen" /></label>
        <label class="af"><span>姓名 / 显示名</span>
          <input v-model.trim="f.display" class="input" maxlength="40" placeholder="如：陈顾问" /></label>
        <label class="af"><span>角色</span>
          <select v-model="f.role" class="select">
            <option value="consultant">consultant · 顾问（方案与客户）</option>
            <option value="supervisor">supervisor · 主管（审批）</option>
            <option value="admin">admin · 管理员（全部权限）</option>
          </select></label>
        <label class="af"><span>初始口令 <b>*</b></span>
          <input v-model="f.password" class="input" type="text" minlength="6" placeholder="至少 6 位，发放后员工可请管理员重置" /></label>
        <button class="btn btn-primary" :disabled="saving || !f.username || f.password.length < 6" @click="create">
          {{ saving ? '发放中…' : '发放账号' }}
        </button>
      </section>

      <!-- 列表 -->
      <section class="card acc-list">
        <h3>账号清单</h3>
        <div v-if="loading" class="acc-loading"><span class="spinner"></span> 加载中…</div>
        <div v-else class="acc-rows">
          <div v-for="a in accounts" :key="a.username" class="acc-row">
            <div class="ar-body">
              <b>{{ a.display }}</b>
              <em>{{ a.username }} · {{ a.role }} · {{ a.tenant }}</em>
            </div>
            <span class="ar-src" :class="a.source">{{ a.source === 'builtin' ? '内置' : '自建' }}</span>
            <div class="ar-ops">
              <button v-if="a.source === 'managed'" class="btn btn-ghost btn-sm" @click="openReset(a)">重置口令</button>
              <button v-if="a.source === 'managed'" class="btn btn-danger btn-sm" @click="removeOne(a)">删除</button>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 重置口令弹窗 -->
    <AppModal v-if="reset.open" :title="`重置「${reset.name}」口令`" @close="reset.open = false">
      <label class="af"><span>新口令（至少 6 位）</span>
        <input v-model="reset.pwd" class="input" type="text" minlength="6" placeholder="告知员工后建议其尽快自行修改" /></label>
      <template #foot>
        <button class="btn btn-primary" :disabled="reset.pwd.length < 6 || reset.busy" @click="doReset">
          {{ reset.busy ? '重置中…' : '确认重置' }}</button>
      </template>
    </AppModal>
  </div>
</template>

<script setup>
// 需求6：toB 企业账号管理（admin 专属）——发放/重置/删除自建账号
import { ref, reactive, computed, onMounted } from 'vue'
import { authApi } from '../../api'
import { toast } from '../../composables/toast'
import AppModal from '../../components/AppModal.vue'

const accounts = ref([])
const loading = ref(true)
const saving = ref(false)
const f = reactive({ username: '', display: '', role: 'consultant', password: '' })
const reset = reactive({ open: false, name: '', pwd: '', busy: false })

const managedCount = computed(() => accounts.value.filter(a => a.source === 'managed').length)

async function load() {
  loading.value = true
  try {
    const r = await authApi.tobAccounts()
    accounts.value = r.accounts || []
  } catch (e) { toast(e.message || '账号清单加载失败（需管理员登录）', 'err') } finally { loading.value = false }
}

async function create() {
  saving.value = true
  try {
    await authApi.tobAccountCreate({ ...f })
    toast(`账号「${f.username}」已发放`, 'ok')
    Object.assign(f, { username: '', display: '', role: 'consultant', password: '' })
    await load()
  } catch (e) { toast(e.message || '发放失败', 'err') } finally { saving.value = false }
}

function openReset(a) {
  reset.open = true
  reset.name = a.username
  reset.pwd = ''
}

async function doReset() {
  reset.busy = true
  try {
    await authApi.tobAccountReset(reset.name, reset.pwd)
    toast(`「${reset.name}」口令已重置`, 'ok')
    reset.open = false
  } catch (e) { toast(e.message || '重置失败', 'err') } finally { reset.busy = false }
}

async function removeOne(a) {
  if (!confirm(`删除账号「${a.username}」？删除后该员工将无法登录工作台。`)) return
  try {
    await authApi.tobAccountDelete(a.username)
    toast('已删除', 'ok')
    await load()
  } catch (e) { toast(e.message || '删除失败', 'err') }
}

onMounted(load)
</script>

<style scoped>
.acc { display: flex; flex-direction: column; gap: 16px; }
.acc-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; }
.acc-head h1 { font-size: 21px; font-weight: 800; margin: 0; }
.acc-head h1 small { font-size: 12px; font-weight: 600; color: var(--text-faint); margin-left: 8px; }
.hint { color: var(--text-dim); font-size: 13px; margin: 6px 0 0; max-width: 720px; line-height: 1.7; }
.head-stats { display: flex; gap: 16px; font-size: 12.5px; color: var(--text-faint); }
.head-stats b { color: var(--text); font-size: 14px; }

.acc-grid { display: grid; grid-template-columns: 1fr 1.3fr; gap: 14px; align-items: start; }
.acc-form, .acc-list { padding: 18px 20px; }
.acc-form h3, .acc-list h3 { margin: 0 0 12px; font-size: 15px; }
.af { display: flex; flex-direction: column; gap: 5px; margin-bottom: 12px; }
.af span { font-size: 12.5px; font-weight: 700; color: var(--text-dim); }
.af span b { color: var(--danger); }
.acc-loading, .acc-empty { padding: 40px 0; text-align: center; color: var(--text-faint); font-size: 13px; }
.acc-rows { display: flex; flex-direction: column; gap: 8px; max-height: 460px; overflow-y: auto; }
.acc-row { display: flex; align-items: center; gap: 10px; border: 1px solid var(--line); border-radius: 11px; padding: 10px 13px; }
.ar-body { flex: 1; min-width: 0; }
.ar-body b { display: block; font-size: 13.5px; }
.ar-body em { font-style: normal; font-size: 11.5px; color: var(--text-faint); }
.ar-src { font-size: 10.5px; font-weight: 700; padding: 2px 9px; border-radius: 999px; }
.ar-src.builtin { background: var(--bg-hover); color: var(--text-dim); }
.ar-src.managed { background: var(--brand-bg, #EFF6FF); color: var(--brand); }
.ar-ops { display: flex; gap: 6px; }
@media (max-width: 1000px) { .acc-grid { grid-template-columns: 1fr; } }
</style>
