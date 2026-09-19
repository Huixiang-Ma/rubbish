<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter, useRoute } from 'vue-router'
import { requestCode, loginBySms, loginByPassword, registerUser, resetPasswordBySms } from '../../stores/auth.js'

const router = useRouter()
const route = useRoute()
const mode = ref('login')        // login | register | reset
const loginType = ref('password') // password | sms（登录方式，默认账号密码）
const phone = ref('')
const code = ref('')
const account = ref('')          // 密码登录：用户名或手机号
const password = ref('')
const display = ref('')          // 注册昵称（选填）
const agreed = ref(true)
const sent = ref(false)
const countdown = ref(0)
const errMsg = ref('')
const devCode = ref('')          // mock 短信通道回显的验证码（演示环境）
const resetPwd = ref('')         // 找回密码：新密码
const busy = ref(false)

async function sendCode() {
  errMsg.value = ''
  if (!/^1\d{10}$/.test(phone.value)) { errMsg.value = '请输入正确的 11 位手机号'; return }
  try {
    const res = await requestCode(phone.value)
    devCode.value = res.dev_code || ''
    sent.value = true
    countdown.value = 60
    const t = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(t)
    }, 1000)
  } catch (e) {
    errMsg.value = e.message || '验证码发送失败'
  }
}

async function submit() {
  if (busy.value || !agreed.value) return
  errMsg.value = ''
  // 找回密码：手机号 + 验证码 + 新密码（POST /api/auth/reset-password），成功即自动登录
  if (mode.value === 'reset') {
    if (!/^1\d{10}$/.test(phone.value)) { errMsg.value = '请输入正确的 11 位手机号'; return }
    if (!code.value) { errMsg.value = '请输入验证码'; return }
    if ((resetPwd.value || '').length < 6) { errMsg.value = '新密码至少 6 位'; return }
    busy.value = true
    try {
      await resetPasswordBySms(phone.value, code.value, resetPwd.value)
      router.push(route.query.redirect || '/plans')
    } catch (e) {
      errMsg.value = e.message || '重置失败'
    } finally {
      busy.value = false
    }
    return
  }
  // 注册：手机号 + 短信验证码（服务端验码）+ 密码，账号即手机号；昵称选填
  if (mode.value === 'register') {
    if (!/^1\d{10}$/.test(phone.value)) { errMsg.value = '请输入正确的 11 位手机号'; return }
    if (!code.value) { errMsg.value = '请输入验证码'; return }
    if ((password.value || '').length < 6) { errMsg.value = '密码至少 6 位'; return }
    busy.value = true
    try {
      await registerUser(phone.value, password.value, display.value.trim() || undefined, code.value)
      router.push(route.query.redirect || '/plans')
    } catch (e) {
      errMsg.value = e.message || '注册失败'
    } finally {
      busy.value = false
    }
    return
  }
  // 登录 · 手机号验证码方式
  if (loginType.value === 'sms') {
    if (!/^1\d{10}$/.test(phone.value)) { errMsg.value = '请输入正确的 11 位手机号'; return }
    if (!code.value) { errMsg.value = '请输入验证码'; return }
    busy.value = true
    try {
      await loginBySms(phone.value, code.value)
      router.push(route.query.redirect || '/plans')
    } catch (e) {
      errMsg.value = e.message || '登录失败'
    } finally {
      busy.value = false
    }
    return
  }
  // 登录 · 账号密码方式（默认）
  if (!account.value.trim()) { errMsg.value = '请输入账号（用户名或手机号）'; return }
  if (!password.value) { errMsg.value = '请输入密码'; return }
  busy.value = true
  try {
    await loginByPassword('toc', account.value.trim(), password.value)
    router.push(route.query.redirect || '/plans')
  } catch (e) {
    errMsg.value = e.message || '登录失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth">
    <div class="auth-box card">
      <RouterLink to="/" class="brand">
        <span class="mark">迹</span>
        <b>迹游 · 智慧行程</b>
      </RouterLink>

      <div class="mode-tabs">
        <button :class="{ on: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ on: mode === 'register' }" @click="mode = 'register'">注册</button>
        <button :class="{ on: mode === 'reset' }" @click="mode = 'reset'">找回密码</button>
      </div>

      <div class="form">
        <!-- 登录 · 账号密码（默认方式） -->
        <template v-if="mode === 'login' && loginType === 'password'">
          <label class="field">
            <span>账号</span>
            <input v-model.trim="account" placeholder="用户名或手机号" maxlength="20" @keyup.enter="submit" />
          </label>
          <label class="field">
            <span>密码</span>
            <input v-model="password" type="password" placeholder="登录密码" maxlength="32" @keyup.enter="submit" />
          </label>
        </template>

        <!-- 登录 · 手机号验证码 / 注册 · 手机号验证码 -->
        <template v-if="mode === 'register' || (mode === 'login' && loginType === 'sms')">
          <label class="field">
            <span>手机号</span>
            <input v-model="phone" placeholder="用于接收行程与凭证短信" maxlength="11" />
          </label>
          <label class="field">
            <span>验证码</span>
            <div class="code-row">
              <input v-model="code" placeholder="6 位短信验证码" maxlength="6" @keyup.enter="submit" />
              <button class="code-btn" :disabled="countdown > 0" @click="sendCode">
                {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
              </button>
            </div>
          </label>
        </template>

        <!-- 注册：密码 + 昵称 -->
        <template v-if="mode === 'reset'">
          <label class="field">
            <span>手机号</span>
            <input v-model="phone" placeholder="注册时的手机号" maxlength="11" />
          </label>
          <label class="field">
            <span>验证码</span>
            <div class="code-row">
              <input v-model="code" placeholder="6 位短信验证码" maxlength="6" />
              <button class="code-btn" :disabled="countdown > 0" @click="sendCode">
                {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
              </button>
            </div>
          </label>
          <label class="field">
            <span>新密码</span>
            <input v-model="resetPwd" type="password" placeholder="至少 6 位，用于账号密码登录" maxlength="32" />
          </label>
        </template>

        <template v-if="mode === 'register'">
          <label class="field">
            <span>密码 <i class="req">*</i></span>
            <input v-model="password" type="password" placeholder="至少 6 位，用于账号密码登录" maxlength="32" />
          </label>
          <label class="field">
            <span>昵称 <em class="opt">选填</em></span>
            <input v-model.trim="display" placeholder="行程与订单中的展示名" maxlength="16" />
          </label>
        </template>

        <label class="agree">
          <input v-model="agreed" type="checkbox" />
          <span>我已阅读并同意 <a>用户协议</a> 与 <a>隐私政策</a></span>
        </label>

        <button class="btn btn-primary submit" :disabled="!agreed || busy" @click="submit">
          {{ busy ? '正在处理…' : (mode === 'login' ? '登录' : mode === 'reset' ? '重置并登录' : '注册并登录') }}
        </button>

        <p v-if="errMsg" class="err-tip">⚠ {{ errMsg }}</p>
        <p v-if="devCode" class="dev-tip">演示通道验证码:<b>{{ devCode }}</b>(真实环境将以短信下发)</p>

        <div v-if="mode === 'login'" class="alt">
          <span>其他方式</span>
          <div class="alt-row">
            <button class="alt-btn">💚 微信</button>
            <button class="alt-btn">🐧 QQ</button>
            <button class="alt-btn" @click="loginType = loginType === 'sms' ? 'password' : 'sms'">
              {{ loginType === 'sms' ? '🔑 账号密码登录' : '📱 手机号登录' }}
            </button>
          </div>
        </div>

        <p class="tip">登录后可同步我的行程、订单与收藏;游客也可 <RouterLink to="/manual" class="link">直接组装行程 →</RouterLink></p>
        <p class="to-b">企业/景区运营人员?<RouterLink to="/tob/auth" class="link">前往企业工作台登录 →</RouterLink></p>
      </div>
    </div>

    <p class="copy">© 2026 迹游 · AI 行程规划平台</p>
  </div>
</template>

<style scoped>
.auth { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--s-5);
  background:
    radial-gradient(600px 400px at 15% 20%, rgba(107,122,92,.10), transparent),
    radial-gradient(500px 380px at 85% 80%, rgba(123,141,160,.10), transparent),
    var(--bg);
  padding: var(--s-6) var(--s-4); }
.auth-box { width: min(400px, 100%); padding: var(--s-7) var(--s-6); }
.brand { display: flex; align-items: center; gap: var(--s-3); text-decoration: none; margin-bottom: var(--s-5); }
.mark { width: 34px; height: 34px; border-radius: 10px; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: var(--fw-bold); font-size: 17px; }
.brand b { color: var(--text); font-size: var(--fs-md); letter-spacing: .02em; }

.mode-tabs { display: flex; gap: 2px; padding: 3px; background: var(--surface-2); border-radius: var(--r); margin-bottom: var(--s-5); }
.mode-tabs button { flex: 1; border: none; background: transparent; padding: 8px; border-radius: calc(var(--r) - 3px); font-size: var(--fs-sm); color: var(--text-3); font-weight: var(--fw-medium); }
.mode-tabs button.on { background: var(--surface); color: var(--text); font-weight: var(--fw-bold); box-shadow: var(--shadow-xs); }

.form { display: flex; flex-direction: column; gap: var(--s-4); }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: var(--fs-xs); font-weight: var(--fw-bold); color: var(--text-2); }
.code-row { display: flex; gap: var(--s-2); }
.code-row input { flex: 1; }
.code-btn { flex: none; border: 1px solid var(--accent); color: var(--accent); background: transparent; border-radius: var(--r); padding: 0 var(--s-3); font-size: var(--fs-xs); cursor: pointer; }
.code-btn:disabled { border-color: var(--border); color: var(--text-faint); cursor: not-allowed; }

.req { color: #B0685C; font-style: normal; }
.opt { font-size: 10px; color: var(--text-faint); font-style: normal; font-weight: var(--fw-normal); margin-left: 4px; }

.agree { display: flex; align-items: center; gap: 8px; font-size: var(--fs-xs); color: var(--text-3); cursor: pointer; }
.agree a { color: var(--accent); }
.submit { width: 100%; }
.submit:disabled { opacity: .45; cursor: not-allowed; }

.alt { text-align: center; }
.alt > span { font-size: var(--fs-xs); color: var(--text-faint); display: block; margin-bottom: var(--s-2); }
.alt-row { display: flex; gap: var(--s-2); justify-content: center; }
.alt-btn { flex: 1; border: 1px solid var(--border); background: var(--surface); border-radius: var(--r); padding: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); cursor: pointer; }
.alt-btn:hover { border-color: var(--accent); }

.tip { font-size: var(--fs-xs); color: var(--text-faint); text-align: center; line-height: 1.7; }
.link { color: var(--accent); text-decoration: none; font-weight: var(--fw-medium); }
.to-b { font-size: var(--fs-xs); color: var(--text-faint); text-align: center; margin: 0; }

.copy { font-size: var(--fs-xs); color: var(--text-faint); }
.err-tip { margin: 0 0 var(--s-3); font-size: var(--fs-xs); color: #B0685C; }
.dev-tip { margin: 0 0 var(--s-3); font-size: var(--fs-xs); color: var(--text-3); background: var(--surface-2); padding: var(--s-2) var(--s-3); border-radius: var(--r-sm); }
.dev-tip b { color: var(--accent); letter-spacing: 2px; }
</style>
