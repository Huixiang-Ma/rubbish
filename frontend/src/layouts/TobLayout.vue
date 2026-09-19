<script setup>
import { ref, computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import TobIcon from '../components/TobIcon.vue'
import { auth, clearAdmin } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)

// 工作台会话（独立于游客端会话）：显示当前 staff 账号与角色
const userLabel = computed(() => (auth.admin && auth.admin.username) || '未登录')
const userRole = computed(() => auth.roleLabel(auth.admin && auth.admin.role))
function logout() { clearAdmin(); router.push('/tob/auth') }

const NAV = [
  {
    group: '经营',
    items: [
      { to: '/tob/dashboard',   icon: 'dashboard', label: '数据看板' },
      { to: '/tob/products',    icon: 'box',       label: '标品素材库' },
      { to: '/tob/plan-products', icon: 'compass', label: '方案上架' },
      { to: '/tob/orders',      icon: 'receipt',   label: '订单管理' },
      { to: '/tob/plans',       icon: 'folder',    label: '方案列表' },
      { to: '/tob/customers',   icon: 'users',     label: '客户管理' },
      { to: '/tob/accounts',    icon: 'user',      label: '企业账号' },
    ]
  },
  {
    group: '运营',
    items: [
      { to: '/tob/content-ops', icon: 'megaphone', label: '内容运营位' },
      { to: '/tob/nearby',      icon: 'pin',       label: '周边与舒适度' },
    ]
  },
  {
    group: '治理',
    items: [
      { to: '/tob/approvals',   icon: 'scale',     label: 'HITL 审核台', badge: 3 },
      { to: '/tob/safety',      icon: 'shield',    label: '安全治理' },
      { to: '/tob/audit',       icon: 'scroll',    label: '合规审计' },
      { to: '/tob/feedback',    icon: 'megaphone', label: '客户之声' },
    ]
  },
  {
    group: '交付',
    items: [
      { to: '/tob/whitelabel',  icon: 'tag',       label: '白标交付' },
    ]
  },
  {
    group: '知识',
    items: [
      { to: '/tob/rag-lab',     icon: 'brain',     label: 'RAG 实验室' },
      { to: '/tob/knowledge',   icon: 'book',      label: '知识库文档' },
      { to: '/tob/coverage',    icon: 'chart',     label: '标品覆盖率' },
    ]
  },
]
</script>

<template>
  <div class="tob-shell">
    <!-- 移动端顶栏 -->
    <header class="tob-m-top hide-desktop">
      <RouterLink to="/" class="brand-mini">
        <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="15" stroke="currentColor" stroke-width="1.2" opacity=".25"/>
          <path d="M5 22 L13 8 L19 18 L22 14 L27 22" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>企业工作台</span>
      </RouterLink>
      <button class="btn btn-ghost btn-icon" @click="menuOpen = !menuOpen" aria-label="菜单">
        <TobIcon name="filter" :size="18" />
      </button>
    </header>

    <!-- 侧边栏 -->
    <aside class="tob-side" :class="{ open: menuOpen }">
      <RouterLink to="/" class="side-brand">
        <span class="mark">
          <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="15" stroke="currentColor" stroke-width="1.2" opacity=".3"/>
            <path d="M5 22 L13 8 L19 18 L22 14 L27 22" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </span>
        <span class="side-brand-text">迹程智游<b>企业工作台</b></span>
      </RouterLink>

      <nav class="side-nav">
        <template v-for="g in NAV" :key="g.group">
          <div class="nav-group">{{ g.group }}</div>
          <RouterLink
            v-for="n in g.items" :key="n.to" :to="n.to"
            class="nav-item"
            :class="{ active: route.path === n.to }"
            @click="menuOpen = false">
            <TobIcon :name="n.icon" :size="17" class="nav-ico" />
            <span>{{ n.label }}</span>
            <em v-if="n.badge" class="nav-badge">{{ n.badge }}</em>
          </RouterLink>
        </template>
      </nav>

      <div class="side-foot">
        <RouterLink to="/" class="foot-back">
          <TobIcon name="chevron" :size="14" class="back-ico" />
          返回游客端
        </RouterLink>
        <div class="foot-user">
          <span class="avatar">{{ userLabel.slice(0, 1) }}</span>
          <div class="fu-info">
            <b>{{ userLabel }}</b>
            <i>{{ userRole }}</i>
          </div>
          <button class="fu-out" @click="logout">退出</button>
        </div>
      </div>
    </aside>

    <!-- 遮罩(移动端) -->
    <div v-if="menuOpen" class="side-mask hide-desktop" @click="menuOpen = false" />

    <!-- 主区 -->
    <main class="tob-main">
      <RouterView v-slot="{ Component }">
        <component :is="Component" :key="$route.fullPath" />
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
.tob-shell {
  display: grid;
  grid-template-columns: 236px 1fr;
  min-height: 100vh;
}

/* —— 侧边栏 —— */
.tob-side {
  background: var(--surface);
  border-right: 1px solid var(--border-soft);
  display: flex; flex-direction: column;
  position: sticky; top: 0;
  height: 100vh;
  overflow-y: auto;
  z-index: 60;
}

.side-brand {
  display: flex; align-items: center; gap: var(--s-3);
  padding: var(--s-5) var(--s-5) var(--s-4);
  color: var(--text);
}
.side-brand .mark {
  width: 38px; height: 38px;
  border-radius: var(--r);
  background: var(--accent-soft);
  color: var(--accent);
  display: inline-flex; align-items: center; justify-content: center;
  flex: none;
}
.side-brand-text {
  display: flex; flex-direction: column;
  font-size: var(--fs-base); font-weight: var(--fw-semi);
  letter-spacing: -0.01em;
  line-height: 1.2;
}
.side-brand-text b {
  font-size: var(--fs-xs); font-weight: var(--fw-regular);
  color: var(--text-3); letter-spacing: 0;
}

.side-nav {
  flex: 1;
  padding: var(--s-2) var(--s-3) var(--s-4);
  display: flex; flex-direction: column; gap: 2px;
}
.nav-group {
  font-size: 11px; font-weight: var(--fw-medium);
  color: var(--text-faint);
  text-transform: uppercase; letter-spacing: 0.14em;
  padding: var(--s-4) var(--s-3) var(--s-2);
}
.nav-group:first-child { padding-top: var(--s-2); }

.nav-item {
  display: flex; align-items: center; gap: var(--s-3);
  padding: 8px var(--s-3);
  border-radius: var(--r);
  font-size: var(--fs-sm); color: var(--text-2);
  transition: background var(--dur-1) var(--ease), color var(--dur-1) var(--ease);
  position: relative;
}
.nav-item:hover { background: var(--surface-2); color: var(--text); }
.nav-item.active {
  background: var(--accent-soft);
  color: var(--text);
  font-weight: var(--fw-medium);
}
.nav-item.active .nav-ico { color: var(--accent); }
.nav-ico { color: var(--text-faint); flex: none; transition: color var(--dur-1) var(--ease); }
.nav-item:hover .nav-ico { color: var(--text-2); }
.nav-badge {
  margin-left: auto;
  font-style: normal;
  min-width: 18px; height: 18px;
  padding: 0 5px;
  border-radius: var(--r-pill);
  background: var(--accent-2-soft); color: var(--accent-2);
  font-size: 11px; font-weight: var(--fw-semi);
  display: inline-flex; align-items: center; justify-content: center;
}

.side-foot {
  border-top: 1px solid var(--border-soft);
  padding: var(--s-3) var(--s-3) var(--s-4);
  display: flex; flex-direction: column; gap: var(--s-2);
}
.foot-back {
  display: inline-flex; align-items: center; gap: var(--s-2);
  padding: 6px var(--s-3);
  border-radius: var(--r);
  font-size: var(--fs-xs); color: var(--text-3);
  transition: color var(--dur-1) var(--ease), background var(--dur-1) var(--ease);
  align-self: flex-start;
}
.foot-back:hover { color: var(--text); background: var(--surface-2); }
.back-ico { transform: rotate(180deg); }

.foot-user {
  display: flex; align-items: center; gap: var(--s-3);
  padding: var(--s-2) var(--s-3);
}
.fu-info { flex: 1; display: flex; flex-direction: column; line-height: 1.25; }
.fu-info b { font-size: var(--fs-sm); font-weight: var(--fw-medium); }
.fu-info i { font-size: var(--fs-xs); font-style: normal; color: var(--text-faint); }
.fu-out {
  border: none; background: none;
  font-size: var(--fs-xs); color: var(--text-faint);
  transition: color var(--dur-1) var(--ease);
}
.fu-out:hover { color: var(--danger); }

/* —— 主区 —— */
.tob-main {
  padding: var(--s-6) var(--s-5) var(--s-9);
  min-width: 0;
}
@media (min-width: 1400px) {
  .tob-main { padding: var(--s-7) var(--s-6) var(--s-9); }
}

/* —— 移动端 —— */
.tob-m-top {
  display: none;
  position: sticky; top: 0; z-index: 70;
  height: 56px;
  padding: 0 var(--s-4);
  align-items: center; justify-content: space-between;
  background: rgba(250,249,246,.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-soft);
}
.brand-mini {
  display: inline-flex; align-items: center; gap: var(--s-2);
  font-size: var(--fs-base); font-weight: var(--fw-semi);
  color: var(--accent);
}
.side-mask {
  position: fixed; inset: 0;
  background: rgba(31,29,26,.24);
  z-index: 55;
}

@media (max-width: 960px) {
  .tob-shell { grid-template-columns: 1fr; }
  .tob-m-top { display: flex; }
  .tob-side {
    position: fixed; left: 0; top: 0; bottom: 0;
    width: 252px;
    transform: translateX(-100%);
    transition: transform var(--dur-2) var(--ease);
    box-shadow: var(--shadow-lg);
  }
  .tob-side.open { transform: translateX(0); }
  .tob-main { padding: var(--s-5) var(--s-4) var(--s-8); }
}
</style>
