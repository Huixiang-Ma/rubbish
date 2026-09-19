import { createRouter, createWebHashHistory } from 'vue-router'

import HomeView from './views/HomeView.vue'
import DashboardView from './views/tob/DashboardView.vue'
import MallsView from './views/MallsView.vue'
import { auth } from './stores/auth.js'

// TOB 页面(懒加载)
const tob = (path, name, comp) => ({
  path, name,
  component: () => import(`./views/tob/${comp}.vue`),
  meta: { tob: true },
})

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    // —— TOC ——
    { path: '/', name: 'home', component: HomeView },
    { path: '/malls', name: 'malls', component: MallsView },

    // —— TOC · AI 行程规划链路 ——
    { path: '/planner', name: 'planner', component: () => import('./views/toc/PlannerView.vue') },
    { path: '/plans', name: 'my-plans', component: () => import('./views/toc/PlansListView.vue') },
    { path: '/plan/:jobId', name: 'plan-detail', component: () => import('./views/toc/PlanDetailView.vue') },
    { path: '/trip/:id', name: 'trip-detail', component: () => import('./views/toc/TripDetailView.vue') },
    { path: '/trip/:id/edit', name: 'trip-edit', component: () => import('./views/toc/TripEditView.vue') },
    { path: '/trip/:id/map', name: 'trip-map', component: () => import('./views/toc/TripMapView.vue') },
    { path: '/manual', name: 'manual-composer', component: () => import('./views/toc/ManualComposerView.vue') },

    // —— TOC · 商城购物链路 ——
    { path: '/malls/product/:id', name: 'malls-product', component: () => import('./views/toc/ProductDetailView.vue') },
    { path: '/checkout', name: 'malls-checkout', component: () => import('./views/toc/CheckoutView.vue') },
    { path: '/orders', name: 'my-orders', component: () => import('./views/toc/MyOrdersView.vue') },
    { path: '/favorites', name: 'my-favorites', component: () => import('./views/toc/FavoritesView.vue') },

    // —— TOC · 服务与登录 ——
    { path: '/services', name: 'services', component: () => import('./views/toc/ServicesView.vue') },
    { path: '/share/:jobId', name: 'share', component: () => import('./views/toc/ShareView.vue'), meta: { bare: true } },
    { path: '/auth', name: 'auth', component: () => import('./views/toc/AuthView.vue'), meta: { bare: true } },

    // —— TOB 企业工作台 ——
    { path: '/tob/dashboard', name: 'tob-dashboard', component: DashboardView, meta: { tob: true } },
    tob('/tob/products',      'tob-products',      'ProductsView'),
    tob('/tob/plan-products', 'tob-plan-products', 'PlanProductsView'),
    tob('/tob/orders',        'tob-orders',        'OrdersView'),
    tob('/tob/plans',         'tob-plans',         'PlansView'),
    tob('/tob/customers',     'tob-customers',     'CustomersView'),
    tob('/tob/accounts',      'tob-accounts',      'AccountsView'),
    tob('/tob/approvals',     'tob-approvals',     'ApprovalView'),
    tob('/tob/safety',        'tob-safety',        'SafetyView'),
    tob('/tob/audit',         'tob-audit',         'AuditView'),
    tob('/tob/feedback',      'tob-feedback',      'FeedbackView'),
    tob('/tob/whitelabel',    'tob-whitelabel',    'WhitelabelView'),
    tob('/tob/rag-lab',       'tob-rag-lab',       'RagLabView'),
    tob('/tob/knowledge',     'tob-knowledge',     'KnowledgeView'),
    tob('/tob/coverage',      'tob-coverage',      'CoverageView'),
    tob('/tob/content-ops',   'tob-content-ops',   'ContentOpsView'),
    tob('/tob/nearby',        'tob-nearby',        'NearbyOpsView'),
    // 登录页:全屏无侧栏(bare)
    { path: '/tob/auth', name: 'tob-auth', component: () => import('./views/tob/TobAuthView.vue'), meta: { tob: true, bare: true } },
  ],
  scrollBehavior() { return { top: 0 } }
})

// RBAC 路由守卫：toB 工作台页面（meta.tob，登录页除外）需工作台会话（admin/supervisor/consultant）。
// toC 账号（traveler）与未登录访客访问 /tob/* 一律跳工作台登录页；toC 页面所有人可用。
router.beforeEach((to) => {
  if (to.meta && to.meta.tob && !to.meta.bare && !auth.isStaff) {
    return { path: '/tob/auth', query: { redirect: to.fullPath } }
  }
  if (to.path === '/tob/auth' && auth.isStaff) {
    return { path: '/tob/dashboard' }
  }
})

// 懒加载 chunk 失败（部署更新后旧页面引用的 chunk 已被新构建替换）：
// 整页跳转到目标路由，加载最新版本的前端，避免"点导航无反应"。
// 守卫标记在任一次成功导航后清除——这样"反复构建期间"每次失败都能重新恢复，
// 且同一次页面加载内同一目标至多恢复一次，不会死循环。
router.onError((error, to) => {
  const msg = String(error && error.message || '')
  if (msg.includes('Failed to fetch dynamically imported module') || msg.includes('Importing a module script failed')) {
    const key = 'wl_chunk_reload'
    const target = (to && to.fullPath) || '/'
    if (sessionStorage.getItem(key) !== target) {
      sessionStorage.setItem(key, target)
      window.location.assign(window.location.origin + window.location.pathname + '#' + target)
    }
  }
})

router.afterEach(() => {
  sessionStorage.removeItem('wl_chunk_reload')
})
