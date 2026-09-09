<template>
  <div class="edit-page">
    <template v-if="loading">
      <div class="loading-block"><div class="spinner spin"></div>{{ mode === 'create' ? '模板加载中…' : '行程书加载中…' }}</div>
    </template>

    <template v-else-if="mode === 'create'">
      <!-- 新建模式：直接进入 TripDayEditor 的 step1 编排 -->
      <TripDayEditor
        :template="creatingTemplate"
        :seed="seedProduct"
        @saved="onSaved"
        @cancelled="onCancel"
      />
    </template>

    <template v-else-if="!trip">
      <div class="empty card big"><div class="icon">🧳</div><p>没有找到这份行程书，无法进入编辑</p>
        <div class="act">
          <router-link :to="{ name: 'my-plans' }" class="btn btn-primary">返回我的行程</router-link>
        </div>
      </div>
    </template>

    <!-- 编辑模式（已有行程书） -->
    <TripDayEditor
      v-else
      :trip="trip"
      @saved="onSaved"
      @cancelled="onCancel"
    />
  </div>
</template>

<script setup>
// P2-编辑页：壳 + 复用 TripDayEditor
//   - 路由 /trip/:id/edit
//   - 三种进入路径：
//       1) /trip/:id/edit            已有行程书 → 打开 TripDayEditor(openEdit)
//       2) /trip/_new/edit?template= 从 PlansListView 选模板跳来 → 打开 TripDayEditor(openCreate)
//       3) /trip/:id/edit?seed=     （预留：商城标品"用它排行程"深链，先在 P1 弹层入口接）
//   - 保存成功：跳 /trip/:id（只读详情）
//   - 取消编辑：跳 /trip/:id 或 /plans
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTripsStore } from '../../stores/trips'
import { routeTemplatesApi } from '../../api'
import { toast } from '../../composables/toast'
import TripDayEditor from '../../components/TripDayEditor.vue'

const route = useRoute()
const router = useRouter()
const store = useTripsStore()

const trip = ref(null)
const creatingTemplate = ref(null)
const seedProduct = ref(null)
const loading = ref(true)
const mode = ref('edit')   // 'edit' | 'create'

async function load() {
  store.load()
  const id = String(route.params.id || '')
  const tplId = String(route.query.template || '')
  const seedId = String(route.query.seed || '')

  // 预置商品（如有）
  if (seedId) {
    try {
      const r = await productsApi.detail(seedId)
      seedProduct.value = r || null
    } catch { seedProduct.value = null }
  } else {
    seedProduct.value = null
  }

  // 新建分支：id 是 _new（来自选模板弹层）或 id 找不到但 query.template 有
  if (id === '_new' || tplId) {
    try {
      const r = await routeTemplatesApi.list()
      const tpl = (r.items || []).find(x => x.id === tplId) || null
      if (!tpl) {
        toast('未找到该模板，回到总览', 'err')
        router.replace({ name: 'my-plans' })
        return
      }
      creatingTemplate.value = tpl
      mode.value = 'create'
      loading.value = false
      return
    } catch (e) {
      toast('模板加载失败：' + (e.message || e), 'err')
      router.replace({ name: 'my-plans' })
      return
    }
  }

  // 编辑分支
  trip.value = store.byId(id)
  mode.value = 'edit'
  loading.value = false
}

onMounted(load)
watch(() => [route.params.id, route.query.template, route.query.seed].join('|'), load)

function onSaved(savedTrip) {
  toast('行程书已保存', 'ok')
  router.replace({ name: 'trip-detail', params: { id: savedTrip.id } })
}
function onCancel() {
  // 新建取消回总览；编辑取消回详情
  if (mode.value === 'create') {
    router.replace({ name: 'my-plans' })
  } else {
    router.replace({ name: 'trip-detail', params: { id: route.params.id } })
  }
}
</script>

<style scoped>
.edit-page { padding-top: 28px; max-width: 1200px; margin: 0 auto; }
.loading-block { padding: 90px 0; text-align: center; color: var(--ink-400); }
.empty.big { padding: 80px 20px; text-align: center; }
.empty .icon { font-size: 54px; }
.empty p { font-size: 15px; color: var(--ink-500); }
.act { display: flex; gap: 10px; justify-content: center; margin-top: 18px; }
</style>
