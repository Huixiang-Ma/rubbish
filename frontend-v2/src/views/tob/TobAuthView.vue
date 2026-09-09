<template>
  <div class="tba">
    <div class="tba-card">
      <div class="tba-brand">
        <span class="mark">迹</span>
        <div>
          <div class="tba-title">迹程智游 · 企业工作台</div>
          <div class="tba-sub">员工账号由企业管理员内部发放，不支持自助注册</div>
        </div>
      </div>

      <form @submit.prevent="submit">
        <div class="f">
          <label>企业账号</label>
          <input v-model.trim="form.username" class="inp" placeholder="admin / supervisor / consultant / 工号" required autocomplete="username" />
        </div>
        <div class="f">
          <label>口令</label>
          <input v-model="form.password" type="password" class="inp" placeholder="请输入工作台口令" required autocomplete="current-password" />
        </div>
        <button class="btn-login" :disabled="busy">{{ busy ? '验证中…' : '登录工作台' }}</button>
      </form>

      <p class="tba-note">🔒 工作台数据涉及客户与订单，请勿共享账号；口令遗失请联系企业管理员重置</p>
      <router-link :to="{ name: 'home' }" class="tba-back">← 返回游客端</router-link>
    </div>
  </div>
</template>

<script setup>
// 需求6：toB 独立登录页（与 toC 登录页完全分离，走暗色企业视觉；账号由企业内部发放）
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { authApi } from '../../api'
import { toast } from '../../composables/toast'

const router = useRouter()
const auth = useAuthStore()
const busy = ref(false)
const form = reactive({ username: '', password: '' })

async function submit() {
  busy.value = true
  try {
    const r = await auth.login('tob', form.username, form.password)
    toast(`欢迎，${r.name || form.username}`, 'ok')
    router.push({ name: 'tob-dashboard' })
  } catch (e) {
    toast(e.message || '登录失败', 'err')
  } finally { busy.value = false }
}
</script>

<style scoped>
.tba {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: #0A1526 radial-gradient(900px 480px at 78% 8%, rgba(59,130,246,.16), transparent 60%),
              radial-gradient(700px 420px at 6% 92%, rgba(16,185,129,.10), transparent 55%);
  padding: 24px;
}
.tba-card {
  width: min(420px, 100%); background: #0F1D33; border: 1px solid rgba(148,163,184,.18);
  border-radius: 20px; padding: 36px 38px 26px; color: #E2E8F0;
  box-shadow: 0 30px 80px rgba(0,0,0,.5);
}
.tba-brand { display: flex; gap: 13px; align-items: center; margin-bottom: 26px; }
.mark {
  width: 44px; height: 44px; border-radius: 13px; flex: none;
  background: linear-gradient(135deg, #38BDF8, #34D399); color: #06281F;
  display: flex; align-items: center; justify-content: center; font-size: 21px; font-weight: 800;
}
.tba-title { font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.tba-sub { font-size: 12px; color: #94A3B8; margin-top: 3px; }
.f { display: flex; flex-direction: column; gap: 6px; margin-bottom: 15px; }
.f label { font-size: 12.5px; font-weight: 700; color: #94A3B8; }
.inp {
  background: rgba(15, 29, 51, .8); border: 1px solid rgba(148,163,184,.25); color: #E2E8F0;
  border-radius: 11px; padding: 11px 14px; font-size: 14px; outline: none; transition: border .15s;
}
.inp::placeholder { color: #64748B; }
.inp:focus { border-color: #38BDF8; }
.btn-login {
  width: 100%; margin-top: 6px; padding: 12px; border: none; border-radius: 11px; cursor: pointer;
  background: linear-gradient(135deg, #0EA5E9, #22C55E); color: #04211A;
  font-size: 15px; font-weight: 800; transition: filter .15s;
}
.btn-login:hover { filter: brightness(1.08); }
.btn-login:disabled { opacity: .6; cursor: default; }
.tba-note { margin-top: 18px; font-size: 11.5px; color: #64748B; line-height: 1.6; }
.tba-back { display: block; text-align: center; margin-top: 10px; font-size: 12.5px; color: #94A3B8; text-decoration: none !important; }
.tba-back:hover { color: #38BDF8; }
</style>
