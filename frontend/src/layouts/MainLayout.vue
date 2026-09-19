<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { auth, logout as doLogout } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const scrolled = ref(false)
const menuOpen = ref(false)

const NAV = [
  { to: '/',         label: '首页' },
  { to: '/malls',    label: '方案馆' },
  { to: '/planner',  label: 'AI 规划' },
  { to: '/manual',   label: '手动规划' },
  { to: '/services', label: '服务大厅' },
  { to: '/plans',    label: '我的行程' },
]
const isActive = (to) => to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(to + '/')

function handleLogout() { doLogout(); router.push('/') }
function onScroll() { scrolled.value = window.scrollY > 8 }
onMounted(() => { window.addEventListener('scroll', onScroll, { passive: true }); onScroll() })
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <div class="app-shell">
    <!-- 顶部导航 -->
    <header class="topbar" :class="{ scrolled }">
      <div class="container-wide topbar-inner">
        <RouterLink to="/" class="brand">
          <span class="brand-mark" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="15" stroke="currentColor" stroke-width="1.2" opacity=".25"/>
              <path d="M5 22 L13 8 L19 18 L22 14 L27 22" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
          <span class="brand-text">迹程智游</span>
        </RouterLink>

        <nav class="nav hide-mobile" aria-label="主导航">
          <RouterLink
            v-for="n in NAV" :key="n.to" :to="n.to"
            class="nav-link"
            :class="{ active: isActive(n.to) }">
            {{ n.label }}
          </RouterLink>
        </nav>

        <div class="actions">
          <RouterLink to="/orders" class="btn btn-text btn-sm hide-mobile">订单</RouterLink>
          <RouterLink to="/favorites" class="btn btn-text btn-sm hide-mobile">收藏</RouterLink>
          <button v-if="auth.isLogin" class="btn btn-text btn-sm hide-mobile" @click="handleLogout">{{ auth.traveler && auth.traveler.username }} · 退出</button>
          <RouterLink v-else to="/auth" class="btn btn-text btn-sm hide-mobile">登录</RouterLink>
          <RouterLink :to="auth.isStaff ? '/tob/dashboard' : '/tob/auth'" class="btn btn-primary btn-sm">企业工作台</RouterLink>
          <button class="btn btn-ghost btn-icon hide-desktop" @click="menuOpen = !menuOpen" aria-label="菜单">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
          </button>
        </div>
      </div>

      <transition name="drawer">
        <div v-if="menuOpen" class="mobile-menu hide-desktop">
          <RouterLink
            v-for="n in NAV" :key="n.to" :to="n.to"
            class="mobile-link"
            :class="{ active: isActive(n.to) }"
            @click="menuOpen = false">
            {{ n.label }}
          </RouterLink>
          <RouterLink to="/orders" class="mobile-link" @click="menuOpen = false">我的订单</RouterLink>
          <RouterLink to="/favorites" class="mobile-link" @click="menuOpen = false">我的收藏</RouterLink>
          <RouterLink to="/auth" class="mobile-link" @click="menuOpen = false">登录 / 注册</RouterLink>
          <RouterLink to="/tob/dashboard" class="mobile-link" @click="menuOpen = false">企业工作台 →</RouterLink>
        </div>
      </transition>
    </header>

    <!-- 主区 -->
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <component :is="Component" :key="$route.fullPath" />
      </RouterView>
    </main>

    <!-- 底部 -->
    <footer class="footer">
      <div class="container-wide footer-inner">
        <div class="footer-brand">
          <div class="row gap-2">
            <svg width="18" height="18" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="15" stroke="currentColor" stroke-width="1.2" opacity=".3"/>
              <path d="M5 22 L13 8 L19 18 L22 14 L27 22" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="fw-semi">迹程智游</span>
          </div>
          <p class="footer-tagline">让每段旅程都被精心安排</p>
        </div>
        <div class="footer-cols">
          <div class="footer-col">
            <div class="footer-h">产品</div>
            <a>方案馆</a><a>AI 行程</a><a>线路定制</a>
          </div>
          <div class="footer-col">
            <div class="footer-h">商家</div>
            <a>企业入驻</a><a>运营后台</a><a>API 接入</a>
          </div>
          <div class="footer-col">
            <div class="footer-h">关于</div>
            <a>关于我们</a><a>联系</a><a>隐私</a>
          </div>
        </div>
      </div>
      <div class="container-wide footer-base">
        <span>© 2026 迹程智游 · 仅作 UI 重做示意</span>
        <span>浅色基调 · 克制点缀 · 高级质感</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
.app-main  { flex: 1; }

/* —— 顶部 —— */
.topbar {
  position: sticky; top: 0; z-index: 50;
  height: var(--nav-h);
  background: rgba(250,249,246,.8);
  backdrop-filter: saturate(180%) blur(14px);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid transparent;
  transition: border-color var(--dur-2) var(--ease), background var(--dur-2) var(--ease);
}
.topbar.scrolled { border-bottom-color: var(--border-soft); background: rgba(250,249,246,.92); }

.topbar-inner {
  height: 100%;
  display: flex; align-items: center; gap: var(--s-7);
}

.brand {
  display: inline-flex; align-items: center; gap: var(--s-2);
  color: var(--text);
  font-weight: var(--fw-semi); font-size: var(--fs-md);
  letter-spacing: -0.005em;
}
.brand-mark { display: inline-flex; color: var(--accent); }

.nav { display: flex; gap: var(--s-2); flex: 1; justify-content: center; }
.nav-link {
  position: relative;
  padding: var(--s-2) var(--s-3);
  font-size: var(--fs-sm); color: var(--text-2);
  border-radius: var(--r);
  transition: color var(--dur-1) var(--ease);
}
.nav-link::after {
  content: ""; position: absolute; left: 50%; bottom: -2px;
  width: 0; height: 1px; background: var(--text);
  transition: width var(--dur-2) var(--ease), left var(--dur-2) var(--ease);
}
.nav-link:hover { color: var(--text); }
.nav-link:hover::after { width: 60%; left: 20%; }
.nav-link.active { color: var(--text); font-weight: var(--fw-medium); }
.nav-link.active::after { width: 24px; left: calc(50% - 12px); }

.actions { display: flex; align-items: center; gap: var(--s-2); }

/* —— 移动菜单 —— */
.mobile-menu {
  border-top: 1px solid var(--border-soft);
  background: var(--surface);
  padding: var(--s-3) var(--s-5);
  display: flex; flex-direction: column;
}
.mobile-link {
  padding: var(--s-3) 0;
  font-size: var(--fs-base); color: var(--text-2);
  border-bottom: 1px solid var(--border-soft);
}
.mobile-link.active { color: var(--text); font-weight: var(--fw-medium); }
.mobile-link:last-child { border-bottom: 0; }
.drawer-enter-active, .drawer-leave-active { transition: opacity .2s var(--ease), transform .2s var(--ease); }
.drawer-enter-from, .drawer-leave-to { opacity: 0; transform: translateY(-4px); }

/* —— 底部 —— */
.footer {
  margin-top: var(--s-10);
  border-top: 1px solid var(--border-soft);
  background: var(--bg-soft);
  padding: var(--s-7) 0 var(--s-5);
  color: var(--text-3);
}
.footer-inner {
  display: grid; grid-template-columns: 1fr 2fr; gap: var(--s-7);
  padding-bottom: var(--s-6);
}
.footer-tagline { font-size: var(--fs-sm); color: var(--text-3); margin-top: var(--s-2); }
.footer-cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--s-6); }
.footer-col { display: flex; flex-direction: column; gap: var(--s-2); }
.footer-col a {
  font-size: var(--fs-sm); color: var(--text-3);
  cursor: pointer; transition: color var(--dur-1) var(--ease);
}
.footer-col a:hover { color: var(--text); }
.footer-h {
  font-size: var(--fs-xs); font-weight: var(--fw-semi); color: var(--text);
  text-transform: uppercase; letter-spacing: 0.1em;
  margin-bottom: var(--s-2);
}
.footer-base {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: var(--s-5);
  border-top: 1px solid var(--border-soft);
  font-size: var(--fs-xs);
}

@media (max-width: 900px) {
  .footer-inner { grid-template-columns: 1fr; gap: var(--s-6); }
  .footer-cols { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  .footer-cols { grid-template-columns: 1fr 1fr; gap: var(--s-4); }
  .footer-base { flex-direction: column; gap: var(--s-2); align-items: flex-start; }
}
</style>
