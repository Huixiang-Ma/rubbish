<template>
  <div class="toc-shell">
    <header class="toc-nav">
      <div class="container nav-inner">
        <router-link :to="{ name: 'home' }" class="brand" @click.prevent="">
          <span class="brand-mark">迹</span>
          <span class="brand-text">迹程智游<small>TrailMind</small></span>
        </router-link>
        <nav class="nav-links">
          <router-link :to="{ name: 'home' }">首页</router-link>
          <router-link :to="{ name: 'my-plans' }">我的行程</router-link>
          <router-link :to="{ name: 'services' }">服务大厅</router-link>
          <router-link :to="{ name: 'tob-dashboard' }" class="tob-link">企业工作台 ↗</router-link>
        </nav>
        <div class="nav-right">
          <template v-if="auth.isLogged">
            <span class="user-chip">👤 {{ auth.name }}</span>
            <button class="btn btn-ghost btn-sm" @click="auth.logout(); toast('已退出登录', 'ok')">退出</button>
          </template>
          <router-link v-else :to="{ name: 'auth' }" class="btn btn-primary btn-sm">登录 / 注册</router-link>
        </div>
      </div>
    </header>

    <main class="toc-main">
      <router-view />
    </main>

    <footer class="toc-foot">
      <div class="container">
        <div class="foot-row">
          <div>
            <div class="foot-brand">迹程智游 · TrailMind</div>
            <p class="foot-desc">多智能体协作的文旅行程规划平台 —— 一句话需求，交给 10 个智能体吵出一趟好旅程。</p>
          </div>
          <div class="foot-meta">
            <span>行程可审计 · 状态可恢复 · 预算可审批</span>
            <span>Frontend v2 · Vue3 + Vite</span>
          </div>
        </div>
      </div>
    </footer>
    <AppToast />
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import { toast } from '../composables/toast'
import AppToast from '../components/AppToast.vue'

const auth = useAuthStore()
</script>

<style scoped>
.toc-shell { min-height: 100vh; display: flex; flex-direction: column; background:
  radial-gradient(1200px 500px at 85% -10%, rgba(59,130,246,.07), transparent 60%),
  radial-gradient(900px 420px at -10% 5%, rgba(245,158,11,.06), transparent 55%),
  var(--ink-50);
}
.toc-nav {
  height: var(--nav-h); background: rgba(255,255,255,.82); backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--ink-100); position: sticky; top: 0; z-index: 50;
}
.nav-inner { height: 100%; display: flex; align-items: center; gap: 34px; }
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none !important; }
.brand-mark {
  width: 36px; height: 36px; border-radius: 11px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--brand-600), var(--brand-400)); color: #fff;
  font-size: 18px; font-weight: 800; box-shadow: 0 4px 12px rgba(37,99,235,.4);
}
.brand-text { font-size: 18px; font-weight: 800; color: var(--ink-900); letter-spacing: -.02em; display: flex; align-items: baseline; gap: 7px; }
.brand-text small { font-size: 11px; color: var(--ink-400); font-weight: 600; letter-spacing: .08em; }
.nav-links { display: flex; gap: 4px; flex: 1; }
.nav-links a {
  padding: 8px 15px; border-radius: var(--r-sm); font-size: 14.5px; font-weight: 500;
  color: var(--ink-700); text-decoration: none !important; transition: all .15s;
}
.nav-links a:hover { background: var(--brand-50); color: var(--brand-600); }
.nav-links a.router-link-active { background: var(--brand-50); color: var(--brand-700); font-weight: 700; }
.tob-link { color: var(--ink-500) !important; }
.nav-right { display: flex; align-items: center; gap: 10px; }
.user-chip { font-size: 13.5px; color: var(--ink-700); font-weight: 600; background: var(--ink-100); padding: 6px 13px; border-radius: 999px; }

.toc-main { flex: 1; }
.toc-foot { border-top: 1px solid var(--ink-100); background: #fff; margin-top: 72px; padding: 36px 0 30px; }
.foot-row { display: flex; justify-content: space-between; gap: 24px; flex-wrap: wrap; }
.foot-brand { font-weight: 800; font-size: 15px; color: var(--ink-900); margin-bottom: 6px; }
.foot-desc { font-size: 13px; color: var(--ink-500); max-width: 480px; }
.foot-meta { display: flex; flex-direction: column; gap: 6px; align-items: flex-end; font-size: 12.5px; color: var(--ink-400); }
</style>
