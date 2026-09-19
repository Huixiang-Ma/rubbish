<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import TobIcon from '../../components/TobIcon.vue'
import { loginByPassword, auth } from '../../stores/auth.js'

const router = useRouter()
const route = useRoute()
const busy = ref(false)
const errMsg = ref('')
const form = reactive({ username: '', password: '' })

// 已有工作台会话：直接进入（守卫也会兜底跳转）
onMounted(() => { if (auth.isStaff) router.replace('/tob/dashboard') })

async function submit() {
  if (busy.value) return
  busy.value = true
  errMsg.value = ''
  try {
    // POST /api/auth/login realm=tob（admin/supervisor/consultant 工作台账号，写入独立的工作台会话）
    await loginByPassword('tob', form.username, form.password)
    router.push(route.query.redirect || '/tob/dashboard')
  } catch (e) {
    errMsg.value = e.message || '登录失败,请检查账号密码'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="auth-card">
      <div class="brand">
        <span class="mark">迹</span>
        <div>
          <div class="brand-title">迹程智游 · 企业工作台</div>
          <div class="brand-sub">员工账号由企业管理员内部发放,不支持自助注册</div>
        </div>
      </div>

      <form @submit.prevent="submit">
        <div class="field f-gap">
          <label>企业账号</label>
          <input v-model.trim="form.username" class="inp" placeholder="admin / supervisor / consultant / 工号" required autocomplete="username" />
        </div>
        <div class="field f-gap">
          <label>口令</label>
          <input v-model="form.password" type="password" class="inp" placeholder="请输入工作台口令" required autocomplete="current-password" />
        </div>
        <button class="btn-login" :disabled="busy">
          <TobIcon v-if="!busy" name="lock" :size="14" />
          {{ busy ? '验证中…' : '登录工作台' }}
        </button>
        <p v-if="errMsg" class="err-tip">⚠ {{ errMsg }}</p>
      </form>

      <p class="note"><TobIcon name="shield" :size="12" /> 工作台数据涉及客户与订单,请勿共享账号;口令遗失请联系企业管理员重置</p>
      <router-link :to="{ name: 'home' }" class="back">
        <TobIcon name="arrowRight" :size="12" style="transform:rotate(180deg)" />返回游客端
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.auth {
  min-height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background:
    radial-gradient(900px 480px at 82% 6%, var(--accent-soft), transparent 60%),
    radial-gradient(700px 420px at 8% 94%, var(--accent-3-soft), transparent 55%),
    var(--bg);
  padding: var(--s-6);
}
.auth-card {
  width: min(420px, 100%);
  background: var(--surface);
  border: 1px solid var(--border-soft);
  border-radius: var(--r-lg);
  padding: var(--s-8) var(--s-8) var(--s-6);
  box-shadow: var(--shadow-md);
}

.brand { display: flex; gap: var(--s-4); align-items: center; margin-bottom: var(--s-7); }
.mark {
  width: 44px; height: 44px; border-radius: var(--r-md); flex: none;
  background: var(--accent); color: #FFFFFF;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: var(--fw-semi);
}
.brand-title { font-size: var(--fs-lg); font-weight: var(--fw-semi); letter-spacing: -0.01em; }
.brand-sub { font-size: var(--fs-xs); color: var(--text-faint); margin-top: 3px; line-height: var(--lh-base); }

.f-gap { margin-bottom: var(--s-4); }
.inp {
  height: 42px; padding: 0 var(--s-4);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--r);
  font-size: var(--fs-sm); color: var(--text);
  transition: border-color var(--dur-1) var(--ease), box-shadow var(--dur-1) var(--ease);
}
.inp::placeholder { color: var(--text-faint); }
.inp:hover { border-color: var(--border-strong); }
.inp:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }

.btn-login {
  width: 100%; margin-top: var(--s-3);
  height: 42px; border: none; border-radius: var(--r);
  cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  background: var(--accent); color: #FFFFFF;
  font-size: var(--fs-base); font-weight: var(--fw-medium);
  transition: filter var(--dur-1) var(--ease), transform var(--dur-1) var(--ease);
}
.btn-login:hover { filter: brightness(1.06); }
.btn-login:active { transform: translateY(1px); }
.btn-login:disabled { opacity: .6; cursor: default; }

.note {
  margin-top: var(--s-5);
  display: flex; align-items: flex-start; gap: 6px;
  font-size: var(--fs-xs); color: var(--text-faint); line-height: var(--lh-base);
}
.note :deep(svg) { flex: none; margin-top: 2px; }

.back {
  display: flex; align-items: center; justify-content: center; gap: 5px;
  margin-top: var(--s-3);
  font-size: var(--fs-xs); color: var(--text-3);
  text-decoration: none;
  transition: color var(--dur-1) var(--ease);
}
.back:hover { color: var(--accent); }
.err-tip { margin-top: var(--s-3); font-size: var(--fs-xs); color: #B0685C; text-align: center; }
</style>