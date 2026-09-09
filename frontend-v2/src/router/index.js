import { createRouter, createWebHashHistory } from 'vue-router'

// hash 路由：后端 FastAPI 无 SPA fallback，hash 模式可任意深层路径直达
//
// 多页面系统路由表（W2 重构）：
//   - /plans                       P1 总览：本地行程书 + AI 任务分栏
//   - /trip/:id                    P2 详情：只读行程书
//   - /trip/:id/edit               P2 编辑：就地编辑
//   - /trip/:id/map                P3 地图：路线图 + 24h 时间线双视图
//   - 旧 /planner* 入口 redirect 到新路由（保留兼容）
//   - /plans?new=1                 P1 总览右上"新建规划"触发 TemplatePickerSheet 弹层
const routes = [
  {
    path: '/s/:jobId',
    component: () => import('../layouts/BareLayout.vue'),
    children: [
      { path: '', name: 'share', component: () => import('../views/share/ShareView.vue') },
    ],
  },
  {
    path: '/b',
    component: () => import('../layouts/TobLayout.vue'),
    children: [
      { path: '', redirect: { name: 'tob-dashboard' } },
      { path: 'dashboard', name: 'tob-dashboard', component: () => import('../views/tob/DashboardView.vue'), meta: { title: '经营看板' } },
      { path: 'plans', name: 'tob-plans', component: () => import('../views/tob/PlansView.vue'), meta: { title: '方案列表' } },
      { path: 'approvals', name: 'tob-approvals', component: () => import('../views/tob/ApprovalView.vue'), meta: { title: 'HITL 审核台' } },
      { path: 'safety', name: 'tob-safety', component: () => import('../views/tob/SafetyView.vue'), meta: { title: '安全治理' } },
      { path: 'audit', name: 'tob-audit', component: () => import('../views/tob/AuditView.vue'), meta: { title: '合规审计' } },
      { path: 'feedback', name: 'tob-feedback', component: () => import('../views/tob/FeedbackView.vue'), meta: { title: '客户之声' } },
      { path: 'rag-lab', name: 'tob-rag-lab', component: () => import('../views/tob/RagLabView.vue'), meta: { title: 'RAG 实验室' } },
      { path: 'knowledge', name: 'tob-knowledge', component: () => import('../views/tob/KnowledgeView.vue'), meta: { title: '知识库文档' } },
      { path: 'composer', name: 'tob-composer', component: () => import('../views/tob/ComposerView.vue'), meta: { title: '行程组装器' } },
      { path: 'coverage', name: 'tob-coverage', component: () => import('../views/tob/CoverageView.vue'), meta: { title: '标品覆盖率' } },
      { path: 'products', name: 'tob-products', component: () => import('../views/tob/ProductsView.vue'), meta: { title: '标品素材库' } },
      { path: 'plan-products', name: 'tob-plan-products', component: () => import('../views/tob/PlanProductsView.vue'), meta: { title: '方案上架' } },
      { path: 'orders', name: 'tob-orders', component: () => import('../views/tob/OrdersView.vue'), meta: { title: '订单管理' } },
      { path: 'customers', name: 'tob-customers', component: () => import('../views/tob/CustomersView.vue'), meta: { title: '客户管理' } },
      { path: 'whitelabel', name: 'tob-whitelabel', component: () => import('../views/tob/WhitelabelView.vue'), meta: { title: '白标交付' } },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/TocLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('../views/toc/HomeView.vue') },

      // ===== P1 总览 =====
      { path: 'plans', name: 'my-plans', component: () => import('../views/toc/PlansListView.vue'), meta: { title: '我的行程' } },

      // ===== 手动行程规划（组装器游客版：标品选品 → 排程 → 编辑保存） =====
      { path: 'manual', name: 'manual-composer', component: () => import('../views/toc/ManualComposerView.vue'), meta: { title: '手动行程规划' } },

      // ===== P2 详情/编辑 + P3 地图（多页面系统核心）=====
      { path: 'trip/:id',           name: 'trip-detail', component: () => import('../views/toc/TripDetailView.vue'), meta: { title: '行程书' } },
      { path: 'trip/:id/edit',      name: 'trip-edit',   component: () => import('../views/toc/TripEditView.vue'),   meta: { title: '编辑行程书' } },
      { path: 'trip/:id/map',       name: 'trip-map',    component: () => import('../views/toc/TripMapView.vue'),    meta: { title: '行程地图' } },

      // ===== AI 智能体生成的任务详情（旧页保留）=====
      { path: 'plan/:jobId', name: 'plan-detail', component: () => import('../views/toc/PlanDetailView.vue') },

      // ===== 线路方案馆（C 端：游客买的是排好的行程方案，整订不散卖门票）=====
      { path: 'malls',               name: 'malls',          component: () => import('../views/toc/MallsView.vue') },
      { path: 'malls/category/:key', name: 'malls-category', component: () => import('../views/toc/MallsView.vue') },
      { path: 'malls/search',        name: 'malls-search',   component: () => import('../views/toc/MallsView.vue') },
      { path: 'malls/product/:id',   name: 'malls-product',  component: () => import('../views/toc/ProductDetailView.vue') },
      { path: 'malls/checkout',             name: 'malls-checkout',  component: () => import('../views/toc/CheckoutView.vue'), meta: { title: '确认订单' } },

      // ===== 我的（C 端个人中心）=====
      { path: 'orders', name: 'my-orders', component: () => import('../views/toc/MyOrdersView.vue'), meta: { title: '我的订单' } },
      { path: 'favorites', name: 'my-favorites', component: () => import('../views/toc/FavoritesView.vue'), meta: { title: '我的收藏' } },

      // ===== 其他 =====
      { path: 'services', name: 'services', component: () => import('../views/toc/ServicesView.vue') },
      { path: 'auth', name: 'auth', component: () => import('../views/toc/AuthView.vue') },

      // ===== 旧 /planner 入口兼容（W2 路由迁移过渡）=====
      // /planner                  → /plans?new=1（弹层入口；PlannerView 不再承担选模板职责）
      // /planner/trip/:tripId     → /trip/:tripId（旧 URL 仍能直达只读详情）
      // /planner/trip/:tripId/map → /trip/:tripId/map
      { path: 'planner',                          redirect: (to) => ({ name: 'my-plans', query: { new: 1, ...to.query } }) },
      { path: 'planner/trip/:tripId',             redirect: (to) => ({ name: 'trip-detail', params: { id: to.params.tripId } }) },
      { path: 'planner/trip/:tripId/map',         redirect: (to) => ({ name: 'trip-map',    params: { id: to.params.tripId } }) },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() { return { top: 0 } },
})

router.afterEach((to) => {
  const t = to.meta?.title
  document.title = t ? `${t} · 迹程智游` : '迹程智游 · 多Agent行程规划平台'
})

// toC 登录门禁：受保护页面未登录时弹登录注册弹窗（?login=1 驱动 TocLayout 的 AuthModal），
// 登录成功后回到原页面。BareLayout 分享页与 auth 本身不拦。
const TOC_PROTECTED = new Set(['my-plans', 'trip-detail', 'trip-edit', 'trip-map', 'plan-detail',
  'my-orders', 'my-favorites', 'malls-checkout', 'manual-composer'])
router.beforeEach((to) => {
  if (to.name === 'auth' || to.name === 'share') return true
  const token = localStorage.getItem('wl_token')
  if (token) return true
  if (TOC_PROTECTED.has(String(to.name))) {
    return { name: 'home', query: { login: 1, next: to.fullPath } }
  }
  return true
})

export default router
