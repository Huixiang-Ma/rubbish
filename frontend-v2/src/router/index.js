import { createRouter, createWebHashHistory } from 'vue-router'

// hash 路由：后端 FastAPI 无 SPA fallback，hash 模式可任意深层路径直达
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
      { path: 'composer', name: 'tob-composer', component: () => import('../views/tob/ComposerView.vue'), meta: { title: '行程组装器' } },
      { path: 'coverage', name: 'tob-coverage', component: () => import('../views/tob/CoverageView.vue'), meta: { title: '标品覆盖率' } },
      { path: 'customers', name: 'tob-customers', component: () => import('../views/tob/CustomersView.vue'), meta: { title: '客户管理' } },
      { path: 'whitelabel', name: 'tob-whitelabel', component: () => import('../views/tob/WhitelabelView.vue'), meta: { title: '白标交付' } },
    ],
  },
  {
    path: '/',
    component: () => import('../layouts/TocLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('../views/toc/HomeView.vue') },
      { path: 'plans', name: 'my-plans', component: () => import('../views/toc/PlansListView.vue') },
      { path: 'plan/:jobId', name: 'plan-detail', component: () => import('../views/toc/PlanDetailView.vue') },
      { path: 'services', name: 'services', component: () => import('../views/toc/ServicesView.vue') },
      { path: 'auth', name: 'auth', component: () => import('../views/toc/AuthView.vue') },
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

export default router
