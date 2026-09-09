<template>
  <div class="auth-wrap container">
    <div class="card auth-card rise">
      <div class="a-brand">
        <span class="mark">迹</span>
        <div>
          <div class="a-title">{{ realmTitle }} · {{ mode === 'login' ? '欢迎回来' : '注册新账号' }}</div>
          <div class="a-sub">{{ realmSub }}</div>
        </div>
      </div>

      <div class="tabs" style="margin:18px 0 20px">
        <button class="tab" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button v-if="realm === 'toc'" class="tab" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>

      <form @submit.prevent="submit" v-if="mode === 'login'">
        <div class="field" style="margin-bottom:14px">
          <label>用户名</label>
          <input v-model.trim="form.username" class="input" :placeholder="realm === 'toc' ? '旅者' : 'admin'" required />
        </div>
        <div class="field" style="margin-bottom:20px">
          <label>密码</label>
          <input v-model="form.password" type="password" class="input" placeholder="请输入密码"" required />
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

      <p class="demo-tip">
        演示环境账号由系统配置发放；游客端支持手机验证码注册
      </p>
      <p v-if="realm === 'toc'" class="demo-tip" style="margin-top:6px">企业员工？请从
        <router-link :to="{ name: 'tob-auth' }" style="color:var(--brand)">企业工作台入口</router-link>
        登录</p>
      <p v-else class="demo-tip" style="margin-top:6px">个人游客？请从
        <router-link :to="{ name: 'auth', query: { realm: 'toc' } }" style="color:var(--brand)">游客端入口</router-link>
        登录 / 注册</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { authApi } from '../../api'
import { toast } from '../../composables/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// 双端分离：/auth?realm=toc 游客端、/auth?realm=tob 企业端；互不可见对方的入口
const realm = computed(() => (String(route.query.realm || 'toc') === 'tob' ? 'tob' : 'toc'))
const mode = ref('login')
const busy = ref(false)
const codeSent = ref(false)
const form = reactive({ username: '', password: '', password2: '', phone: '' })

const realmTitle = computed(() => (realm.value === 'toc' ? '游客中心' : '企业工作台'))
const realmSub = computed(() => (realm.value === 'toc'
  ? (mode.value === 'login' ? '登录后同步你的行程与偏好记忆' : '注册一个 toC 账号，行程随身带')
  : 'toB 管理账号登录（游客请从游客端进入）'))

watch(realm, () => { mode.value = 'login' })

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
