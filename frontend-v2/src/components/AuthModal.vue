<template>
  <Teleport to="body">
    <div v-if="open" class="am-mask" @click.self="close">
      <div class="am-card">
        <button class="am-x" @click="close">×</button>
        <div class="a-brand">
          <span class="mark">迹</span>
          <div>
            <div class="a-title">{{ mode === 'login' ? '登录迹程智游' : '注册新账号' }}</div>
            <div class="a-sub">{{ hint || '登录后才能使用该功能 · 行程随身带' }}</div>
          </div>
        </div>
        <div class="tabs" style="margin:14px 0 16px">
          <button class="tab" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
          <button class="tab" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
        </div>
        <form @submit.prevent="submit" v-if="mode === 'login'">
          <div class="field" style="margin-bottom:12px">
            <label>用户名</label>
            <input v-model.trim="form.username" class="input" placeholder="旅者" required />
          </div>
          <div class="field" style="margin-bottom:16px">
            <label>密码</label>
            <input v-model="form.password" type="password" class="input" placeholder="请输入密码" required />
          </div>
          <button class="btn btn-primary btn-block" :disabled="busy">{{ busy ? '登录中…' : '登 录' }}</button>
        </form>
        <form @submit.prevent="submit" v-else>
          <div class="field" style="margin-bottom:12px">
            <label>用户名</label>
            <input v-model.trim="form.username" class="input" placeholder="给自己起个名字" required />
          </div>
          <div class="field" style="margin-bottom:12px">
            <label>手机号（演示可不填）</label>
            <input v-model.trim="form.phone" class="input" placeholder="11 位手机号" maxlength="11" />
          </div>
          <div class="field" style="margin-bottom:16px">
            <label>密码</label>
            <input v-model="form.password" type="password" class="input" placeholder="至少 6 位" required minlength="6" />
          </div>
          <button class="btn btn-primary btn-block" :disabled="busy">{{ busy ? '注册中…' : '注 册' }}</button>
        </form>
        <p class="am-tip">还没有账号？切到「注册」即买即用 · 企业员工请走<a href="#/login" style="color:var(--brand)">工作台入口</a></p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
// toC 功能门禁弹窗：未登录点击受保护功能时弹出（登录/注册一体化，成功后自动重放被拦截的跳转）
import { ref, reactive, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api'
import { toast } from '../composables/toast'

const props = defineProps({
  open: { type: Boolean, default: false },
  hint: { type: String, default: '' },
})
const emit = defineEmits(['close', 'ok'])

const auth = useAuthStore()
const mode = ref('login')
const busy = ref(false)
const form = reactive({ username: '', password: '', phone: '' })

watch(() => props.open, (v) => { if (v) { mode.value = 'login'; busy.value = false } })

function close() { emit('close') }

async function submit() {
  busy.value = true
  try {
    if (mode.value === 'login') {
      const r = await auth.login('toc', form.username, form.password)
      toast(`欢迎，${r.name || form.username}`, 'ok')
    } else {
      if (!form.password || form.password.length < 6) throw new Error('密码至少 6 位')
      const r = await authApi.register({ username: form.username, password: form.password, phone: form.phone || undefined })
      // 注册即登录（后端直接发 token）
      auth.token = r.token
      auth.name = r.name || form.username
      auth.role = r.role || 'traveler'
      localStorage.setItem('wl_token', auth.token)
      localStorage.setItem('wl_name', auth.name)
      localStorage.setItem('wl_role', auth.role)
      toast(`注册成功，欢迎 ${auth.name}`, 'ok')
    }
    emit('ok')
    close()
  } catch (e) {
    toast(e.message || '登录失败', 'err')
  } finally { busy.value = false }
}
</script>

<style scoped>
.am-mask {
  position: fixed; inset: 0; background: rgba(15, 23, 42, .45); backdrop-filter: blur(3px);
  display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px;
}
.am-card { position: relative; width: min(400px, 100%); background: #fff; border-radius: 18px; padding: 26px 28px 22px; box-shadow: 0 24px 60px rgba(0,0,0,.25); }
.am-x { position: absolute; top: 10px; right: 14px; border: none; background: none; font-size: 24px; color: var(--ink-400); cursor: pointer; line-height: 1; }
.a-brand { display: flex; gap: 12px; align-items: center; margin-bottom: 4px; }
.mark {
  width: 40px; height: 40px; border-radius: 12px; flex: none;
  background: linear-gradient(135deg, var(--brand-600), var(--brand-400)); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 19px; font-weight: 800;
}
.a-title { font-size: 17px; font-weight: 800; }
.a-sub { font-size: 12.5px; color: var(--ink-500); margin-top: 2px; }
.am-tip { margin-top: 14px; font-size: 12px; color: var(--ink-400); text-align: center; }
</style>
