<template>
  <div class="tob-scope tob-shell">
    <aside class="side">
      <router-link :to="{ name: 'home' }" class="side-brand">
        <span class="mark">迹</span>
        <span>迹程智游<b>企业工作台</b></span>
      </router-link>

      <nav class="side-nav">
        <div class="nav-group">经营</div>
        <router-link :to="{ name: 'tob-dashboard' }"><span class="ico">📊</span>数据看板</router-link>
        <router-link :to="{ name: 'tob-products' }"><span class="ico">📦</span>标品素材库</router-link>
        <router-link :to="{ name: 'tob-plan-products' }"><span class="ico">🧭</span>方案上架</router-link>
        <router-link :to="{ name: 'tob-orders' }"><span class="ico">🧾</span>订单管理</router-link>
        <router-link :to="{ name: 'tob-plans' }"><span class="ico">🗂</span>方案列表</router-link>
        <router-link :to="{ name: 'tob-customers' }"><span class="ico">👥</span>客户管理</router-link>
    <router-link :to="{ name: 'tob-accounts' }"><span class="ico">👤</span>企业账号</router-link>

        <div class="nav-group">治理</div>
        <router-link :to="{ name: 'tob-approvals' }"><span class="ico">⚖️</span>HITL 审核台<em v-if="pendingCount" class="badge">{{ pendingCount }}</em></router-link>
        <router-link :to="{ name: 'tob-safety' }"><span class="ico">🛡</span>安全治理</router-link>
        <router-link :to="{ name: 'tob-audit' }"><span class="ico">📜</span>合规审计</router-link>
        <router-link :to="{ name: 'tob-feedback' }"><span class="ico">📣</span>客户之声</router-link>

        <div class="nav-group">交付</div>
        <router-link :to="{ name: 'tob-whitelabel' }"><span class="ico">🏷</span>白标交付</router-link>

        <div class="nav-group">知识</div>
        <router-link :to="{ name: 'tob-rag-lab' }"><span class="ico">🧠</span>RAG 实验室</router-link>
    <router-link :to="{ name: 'tob-knowledge' }"><span class="ico">📚</span>知识库文档</router-link>
        <router-link :to="{ name: 'tob-composer' }"><span class="ico">🧩</span>行程组装器</router-link>
        <router-link :to="{ name: 'tob-coverage' }"><span class="ico">📐</span>标品覆盖率</router-link>
      </nav>

      <div class="side-foot">
        <router-link :to="{ name: 'home' }" class="back-toc">← 返回游客端</router-link>
        <div class="op" v-if="auth.isLogged">
          <span>{{ auth.name }} · {{ auth.role }}</span>
          <button @click="auth.logout(); toast('已退出', 'ok')">退出</button>
        </div>
        <router-link v-else :to="{ name: 'tob-auth' }" class="btn btn-primary btn-sm" style="text-decoration:none">登录工作台</router-link>
      </div>
    </aside>

    <main class="tob-main">
      <router-view />
    </main>
    <AppToast />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { govApi } from '../api'
import { toast } from '../composables/toast'
import AppToast from '../components/AppToast.vue'

const auth = useAuthStore()
const pendingCount = ref(0)

onMounted(async () => {
  try {
    const r = await govApi.pendingApprovals()
    pendingCount.value = r.total || 0
  } catch { /* 认证未开启时忽略 */ }
})
</script>

<style scoped>
.tob-shell { display: flex; min-height: 100vh; background: var(--bg); color: var(--text); }
.side {
  width: 232px; flex: none; background: #0A1526; border-right: 1px solid var(--line);
  display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.side-brand {
  display: flex; align-items: center; gap: 10px; padding: 20px 18px 16px;
  text-decoration: none !important; color: var(--text); font-weight: 800; font-size: 15.5px; letter-spacing: -.01em;
  border-bottom: 1px solid var(--line);
}
.side-brand .mark {
  width: 32px; height: 32px; border-radius: 9px; flex: none;
  background: linear-gradient(135deg, var(--brand-2), var(--brand)); color: #1C1814;
  display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 800;
}
.side-brand b { display: block; font-size: 10.5px; color: var(--text-faint); font-weight: 600; letter-spacing: .14em; margin-top: 1px; }

.side-nav { flex: 1; padding: 12px 10px; display: flex; flex-direction: column; gap: 2px; }
.nav-group { font-size: 11px; color: var(--text-faint); font-weight: 700; letter-spacing: .16em; padding: 16px 10px 7px; }
.side-nav a {
  display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 9px;
  color: var(--text-dim); font-size: 14px; font-weight: 500; text-decoration: none !important; transition: all .14s;
}
.side-nav a:hover { background: var(--bg-hover); color: var(--text); }
.side-nav a.router-link-active { background: var(--brand-bg); color: var(--brand); font-weight: 700; }
.side-nav .ico { font-size: 15px; width: 20px; text-align: center; }
.side-nav .badge {
  margin-left: auto; background: var(--danger); color: #fff; font-size: 11px; font-style: normal;
  padding: 1px 8px; border-radius: 999px; font-weight: 700;
}
.side-foot { padding: 14px 16px; border-top: 1px solid var(--line); display: flex; flex-direction: column; gap: 10px; }
.back-toc { font-size: 12.5px; color: var(--text-faint); text-decoration: none !important; }
.back-toc:hover { color: var(--brand); }
.op { display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; color: var(--text-dim); }
.op button { background: none; border: none; color: var(--text-faint); cursor: pointer; font-size: 12px; }
.op button:hover { color: var(--danger); }

.tob-main { flex: 1; padding: 28px 32px 60px; min-width: 0; }
</style>
