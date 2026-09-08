<template>
  <div class="auth-wrap container">
    <div class="card auth-card rise">
      <div class="a-brand">
        <span class="mark">迹</span>
        <div>
          <div class="a-title">{{ mode === 'login' ? '欢迎回来' : '加入迹程智游' }}</div>
          <div class="a-sub">{{ mode === 'login' ? '登录后同步你的行程与偏好记忆' : '注册一个 toC 账号，行程随身带' }}</div>
        </div>
      </div>

      <div class="tabs" style="margin:18px 0 20px">
        <button class="tab" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button class="tab" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>

      <form @submit.prevent="submit" v-if="mode === 'login'">
        <div class="field" style="margin-bottom:14px">
          <label>身份</label>
          <div class="chip-group">
            <button type="button" class="chip" :class="{ active: realm === 'toc' }" @click="realm = 'toc'">游客 toC</button>
            <button type="button" class="chip" :class="{ active: realm === 'tob' }" @click="realm = 'tob'">企业 toB</button>
          </div>
        </div>
        <div class="field" style="margin-bottom:14px">
          <label>用户名</label>
          <input v-model.trim="form.username" class="input" :placeholder="realm === 'toc' ? '旅者' : 'admin'" required />
        </div>
        <div class="field" style="margin-bottom:20px">
          <label>密码</label>
          <input v-model="form.password" type="password" class="input" :placeholder="realm === 'toc' ? '123456' : 'wl2026'" required />
        </div>
        <button class="btn btn-primary btn-block btn-lg" :disabled="busy">{{ busy ? '登录中…' : '登 录' }}</button>
      </form>

      <form @submit.prevent="submit" v-else>
        <div class="field" style="margin-bottom:14px">
          <label>用户名</label>
          <input v-model.trim="form.username" class="input" placeholder="给自己起个名字" required />
        </div>
        <div class="field" style="margin-bottom:14px">
          <label>手机号（演示可不填）</label>
          <div style="display:flex;gap:10px">
            <input v-model.trim="form.phone" class="input" placeholder="11 位手机号" maxlength="11" />
            <button type="button" class="btn btn-ghost" :disabled="!form.phone || codeSent" @click="sendCode">
              {{ codeSent ? '验证码已发送' : '获取验证码' }}</button>
          </div>
        </div>
        <div class="field" style="margin-bottom:14px">
          <label>密码</label>
          <input v-model="form.password" type="password" class="input" placeholder="至少 6 位" required minlength="6" />
        </div>
        <div class="field" style="margin-bottom:20px">
          <label>确认密码</label>
          <input v-model="form.password2" type="password" class="input" required />
        </div>
        <button class="btn btn-primary btn-block btn-lg" :disabled="busy">{{ busy ? '注册中…' : '注 册' }}</button>
      </form>

      <p class="demo-tip">演示账号 — toC：<code>旅者 / 123456</code> · toB：<code>admin / wl2026</code></p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { authApi } from '../../api'
import { toast } from '../../composables/toast'

const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const realm = ref('toc')
const busy = ref(false)
const codeSent = ref(false)
const form = reactive({ username: '', password: '', password2: '', phone: '' })

async function sendCode() {
  try {
    await authApi.requestCode(form.phone)
    codeSent.value = true
    toast('验证码已发送（演示环境任意码可用）', 'ok')
  } catch (e) { toast(e.message, 'err') }
}

async function submit() {
  busy.value = true
  try {
    if (mode.value === 'login') {
      const r = await auth.login(realm.value, form.username, form.password)
      toast(`欢迎，${r.name || form.username}`, 'ok')
      router.push(realm.value === 'tob' ? { name: 'tob-dashboard' } : { name: 'home' })
    } else {
      if (form.password !== form.password2) throw new Error('两次密码不一致')
      await authApi.register({ username: form.username, password: form.password, phone: form.phone || undefined })
      toast('注册成功，请登录', 'ok')
      mode.value = 'login'
    }
  } catch (e) { toast(e.message, 'err') } finally { busy.value = false }
}
</script>

<style scoped>
.auth-wrap { display: flex; justify-content: center; padding: 64px 24px 40px; }
.auth-card { width: min(440px, 100%); padding: 32px 34px; box-shadow: var(--shadow-lg); }
.a-brand { display: flex; gap: 14px; align-items: center; }
.mark {
  width: 46px; height: 46px; border-radius: 14px; flex: none;
  background: linear-gradient(135deg, var(--brand-600), var(--brand-400)); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 800;
}
.a-title { font-size: 19px; font-weight: 800; letter-spacing: -.01em; }
.a-sub { font-size: 13px; color: var(--ink-500); margin-top: 2px; }
.demo-tip { margin-top: 18px; font-size: 12.5px; color: var(--ink-400); text-align: center; }
.demo-tip code { background: var(--ink-100); padding: 2px 7px; border-radius: 6px; font-size: 11.5px; }
</style>
