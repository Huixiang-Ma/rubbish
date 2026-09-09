// 统一 API 封装：同源相对路径（dev 由 Vite proxy 转发到 FastAPI）
//
// 全部数据走真实后端 /api（商业闭环 /api/plan-products、/api/orders、/api/favorites，
// 标品素材库 /api/products，标品线路 /api/routes，标品 RAG 选品与组装 /api/composer/*，
// 知识背书 /api/catalog/*，覆盖率 /api/stats/product-coverage*）。旧 mock 层已随旧前端移除。
const BASE = '/api'

// 查询串工具：过滤空值，避免 /x?foo=undefined
const toQs = (params = {}) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
  return q.toString() ? `?${q.toString()}` : ''
}

async function request(method, path, body, opts = {}) {
  const headers = { ...(opts.headers || {}) }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = localStorage.getItem('wl_token')
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: opts.signal,
  })

  if (opts.raw) return res

  if (!res.ok) {
    let detail = ''
    try {
      const j = await res.json()
      detail = typeof j.detail === 'string' ? j.detail
        : Array.isArray(j.detail) ? j.detail.map(e => `${(e.loc || []).join('.')}: ${e.msg}`).join('; ')
        : JSON.stringify(j)
    } catch { detail = res.statusText }
    const err = new Error(detail || `HTTP ${res.status}`)
    err.status = res.status
    throw err
  }
  // 204 或空体
  const text = await res.text()
  return text ? JSON.parse(text) : null
}

export const api = {
  get: (p, o) => request('GET', p, undefined, o),
  post: (p, b, o) => request('POST', p, b, o),
  sse: (path, onEvent, onDone) => {
    // SSE 直播辩论
    const token = localStorage.getItem('wl_token')
    const es = new EventSource(`${BASE}${path}${token ? `?token=${token}` : ''}`)
    es.onmessage = (ev) => {
      if (ev.data === 'done') { es.close(); onDone && onDone(); return }
      try { onEvent(JSON.parse(ev.data)) } catch { onEvent({ text: ev.data }) }
    }
    es.onerror = () => { es.close(); onDone && onDone() }
    return es
  },
}

/* ---------- 行程规划 ---------- */
export const plansApi = {
  create: (payload) => api.post('/plans', payload),
  list: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== '')).toString()
    return api.get(`/plans${q ? `?${q}` : ''}`)
  },
  mine: () => api.get('/plans/mine'),
  status: (jobId) => api.get(`/plans/${jobId}`),
  result: (jobId) => api.get(`/plans/${jobId}/result`),
  audit: (jobId) => api.get(`/plans/${jobId}/audit`),
  diff: (jobId) => api.get(`/plans/${jobId}/diff`),
  approval: (jobId, body) => api.post(`/plans/${jobId}/approval`, body),
  replan: (jobId, body) => api.post(`/plans/${jobId}/replan`, body),
  feedback: (jobId, body) => api.post(`/plans/${jobId}/feedback`, body),
  export: (jobId, body) => api.post(`/plans/${jobId}/export`, body),
  intervene: (jobId, body) => api.post(`/plans/${jobId}/intervene`, body),
  memory: (jobId) => api.get(`/plans/${jobId}/memory`),
  interventions: (jobId) => api.get(`/plans/${jobId}/interventions`),
}

/* ---------- 体验接口 ---------- */
export const expApi = {
  map: (jobId) => api.get(`/plans/${jobId}/map`),
  nearby: (jobId, kind) => api.get(`/plans/${jobId}/nearby?kind=${kind}`),
  debates: (jobId) => api.get(`/plans/${jobId}/debates`),
  counterfactual: (jobId) => api.get(`/plans/${jobId}/counterfactual`),
  swarm: (jobId) => api.get(`/plans/${jobId}/swarm`),
  guides: (jobId) => api.get(`/plans/${jobId}/guides`),
  dialogue: (jobId, body) => api.post(`/plans/${jobId}/dialogue`, body),
  debateVote: (jobId, side) => api.post(`/plans/${jobId}/debate/vote`, { side }),
}

/* ---------- toB 治理 ---------- */
export const govApi = {
  pendingApprovals: () => api.get('/approvals/pending'),
  feedbacks: () => api.get('/feedbacks'),
  stats: () => api.get('/stats/overview'),
  safety: () => api.get('/safety/summary'),
  auditCsvUrl: () => `${BASE}/audit/export.csv`,
  integrations: () => api.get('/integrations/status'),
}

/* ---------- 服务大厅 ---------- */
export const svcApi = {
  travel: (destination, origin, days) =>
    api.get(`/services/travel?destination=${encodeURIComponent(destination)}&origin=${encodeURIComponent(origin)}&days=${days}`),
  byKind: (kind, destination, origin) =>
    api.get(`/services/${kind}?destination=${encodeURIComponent(destination)}&origin=${encodeURIComponent(origin)}`),
  cityPhoto: (destination) =>
    api.get(`/services/city/photo?destination=${encodeURIComponent(destination)}`),
  // 方案卡片景点实拍图（目的地 + 方案内停留点名，逗号分隔）
  planPhotos: (destination, spots) =>
    api.get(`/services/plan/photos?destination=${encodeURIComponent(destination || '')}&spots=${encodeURIComponent(spots || '')}`),
  bookingClick: (kind, jobId = null) => api.post('/services/booking/click', { kind, job_id: jobId }),
}

/* ---------- 认证 ---------- */
export const authApi = {
  login: (realm, username, password) => api.post('/auth/login', { realm, username, password }),
  register: (body) => api.post('/auth/register', body),
  requestCode: (phone) => api.post('/auth/request-code', { phone }),
  me: () => api.get('/auth/me'),
}

/* ---------- RAG 知识问答 ----------
 * 同步 ask：返回 {mode, answer, sources[], sub_questions[]}
 *   mode: llm(命中并LLM生成) | refusal(距离>阈值拒答) | empty(无相关) | retrieval(检索到但LLM不可用)
 * 流式 chat：POST + SSE 响应，事件为 {type:'meta'|'token'|'done'|'error', ...}
 *   meta -> token* -> done (与 rag_lab 口径对齐)
 */
export const ragApi = {
  ask: (message, topK = 3, tenantId) =>
    api.post('/rag/ask', { message, top_k: topK, tenant_id: tenantId || null }),
  chat: (message, topK = 3, tenantId, { onMeta, onToken, onDone, onError, signal } = {}) => {
    // POST + SSE：fetch + ReadableStream 手动切分 data: 行
    const token = localStorage.getItem('wl_token')
    const ctrl = new AbortController()
    const composed = signal
      ? (() => { signal.addEventListener('abort', () => ctrl.abort()); return ctrl.signal })()
      : ctrl.signal
    const url = `${BASE}/rag/chat`
    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    const promise = fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, top_k: topK, tenant_id: tenantId || null }),
      signal: composed,
    }).then(async (res) => {
      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try { const j = await res.json(); msg = (j.detail || j.message || msg) + '' } catch {}
        throw new Error(msg)
      }
      const reader = res.body.getReader()
      const dec = new TextDecoder('utf-8')
      let buf = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const block = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          const line = block.split('\n').find(l => l.startsWith('data: '))
          if (!line) continue
          const payload = line.slice(6).trim()
          if (!payload || payload === '[DONE]') continue
          let evt
          try { evt = JSON.parse(payload) } catch { continue }
          if (evt.type === 'meta') onMeta && onMeta(evt)
          else if (evt.type === 'token') onToken && onToken(evt.text || '')
          else if (evt.type === 'done') { onDone && onDone(evt); return }
          else if (evt.type === 'error') { onError && onError(evt); return }
        }
      }
      onDone && onDone({ type: 'done', mode: 'empty', answer: '' })
    }).catch((e) => {
      if (e.name === 'AbortError') return
      onError && onError({ type: 'error', message: e.message || String(e) })
    })
    return { abort: () => ctrl.abort(), promise }
  },
}

/* ---------- 标品 → 行程（RAG 选品 + 行程积木组装器） ---------- */
export const composerApi = {
  // 拉取标品目录（按分类），供 Composer 选择
  listProducts: (params = {}) => api.get('/composer/products', { params }),
  // RAG 语义选品：自然语言主题 → 混合检索标品知识语料（命中含匹配分与语料摘要）
  searchProducts: (q, params = {}) => api.get(`/composer/search${toQs({ q, ...params })}`),
  // 提交标品 ID 列表，生成行程模板（含 RAG 知识背书）
  compose: (body) => api.post('/composer/from-products', body),
  // 预览单步（拖拽过程中实时计算时间冲突 / 距离）
  preview: (body) => api.post('/composer/preview', body),
}

/* ---------- 行程中标品替换 ---------- */
export const swapApi = {
  // 替换行程某时段内的标品
  swap: (jobId, body) => api.post(`/plans/${jobId}/swap-product`, body),
  // 查看替换影响
  inspect: (jobId, body) => api.post(`/plans/${jobId}/swap-product/inspect`, body),
}

/* ---------- 标品覆盖率分析 ---------- */
export const coverageApi = {
  overview: (params = {}) => api.get('/stats/product-coverage', { params }),
  trend: (params = {}) => api.get('/stats/product-coverage/trend', { params }),
  missing: (params = {}) => api.get('/stats/product-coverage/missing', { params }),
}

/* ---------- 体验增强：行程评分沉淀 / 知识库文档 / RAG 问答助手 ---------- */
export const assistApi = {
  // 评分
  getRating: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/rating`),
  rate: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/rating`, body),
  rateIngest: (jobId) => api.post(`/plans/${encodeURIComponent(jobId)}/rate-ingest`),
  rateListing: (jobId) => api.post(`/plans/${encodeURIComponent(jobId)}/rate-listing`),
  // toB 知识库文档
  kbList: () => api.get('/kb/docs'),
  kbCreate: (body) => api.post('/kb/docs', body),
  kbDelete: (id) => api.delete(`/kb/docs/${encodeURIComponent(id)}`),
  // toC RAG 问答助手（知识库未命中自动联网搜索）
  assistant: (message, topK = 3) => api.post('/rag/assistant', { message, top_k: topK }),
  assistantChat: (message, topK = 3, { onMeta, onToken, onDone, onError } = {}) => {
    const ctrl = new AbortController()
    const promise = fetch(`${BASE}/rag/assistant/chat`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, top_k: topK }), signal: ctrl.signal,
    }).then(async (res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const reader = res.body.getReader()
      const dec = new TextDecoder('utf-8')
      let buf = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const block = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          const line = block.split('\n').find(l => l.startsWith('data: '))
          if (!line) continue
          let evt
          try { evt = JSON.parse(line.slice(6)) } catch { continue }
          if (evt.type === 'meta') onMeta && onMeta(evt)
          else if (evt.type === 'token') onToken && onToken(evt.text || '')
          else if (evt.type === 'done') { onDone && onDone(evt); return }
          else if (evt.type === 'error') { onError && onError(evt); return }
        }
      }
      onDone && onDone({ type: 'done', mode: 'empty', answer: '' })
    }).catch((e) => {
      if (e.name !== 'AbortError') onError && onError({ type: 'error', message: e.message || String(e) })
    })
    return { abort: () => ctrl.abort(), promise }
  },
}

/* =====================================================================
 * 商业闭环聚合出口（全部真实后端 /api）：
 *   planShopApi  线路方案馆：目录/详情/榜单 + toB 上架管理（/api/plan-products*）。
 *   productsApi  标品素材库目录与素材管理（/api/products*）。
 *   ordersApi    订单：真实落库 /api/orders；pay=演示级支付回执，未支付才可取消。
 *   favApi       收藏：真实落库 /api/favorites，按登录用户隔离（未登录 guest 账本）。
 * ===================================================================== */
export const planShopApi = {
  list: (params = {}) => api.get(`/plan-products${toQs(params)}`),
  categories: () => api.get('/plan-products/categories'),
  detail: (id) => api.get(`/plan-products/${encodeURIComponent(id)}`),
  featured: () => api.get('/plan-products/featured'),
  top: () => api.get('/plan-products/top'),
  manageList: (p = {}) => api.get(`/plan-products/manage${toQs(p)}`),
  create: (d) => api.post('/plan-products', d),
  update: (id, patch) => api.put(`/plan-products/${encodeURIComponent(id)}`, patch),
  setStatus: (id, listed) => api.post(`/plan-products/${encodeURIComponent(id)}/status`, { listed }),
  remove: (id) => api.delete(`/plan-products/${encodeURIComponent(id)}`),
}
export const productsApi = {
  categories: () => api.get('/products/categories'),
  list: (p = {}) => api.get(`/products${toQs(p)}`),
  detail: (id) => api.get(`/products/${encodeURIComponent(id)}`),
  manageList: (p = {}) => api.get(`/products/manage${toQs(p)}`),
  create: (d) => api.post('/products', d),
  update: (id, patch) => api.put(`/products/${encodeURIComponent(id)}`, patch),
  setStatus: (id, listed) => api.post(`/products/${encodeURIComponent(id)}/status`, { listed }),
  remove: (id) => api.delete(`/products/${encodeURIComponent(id)}`),
}

export const ordersApi = {
  list: (params = {}) => api.get(`/orders${toQs(params)}`),
  detail: (id) => api.get(`/orders/${encodeURIComponent(id)}`),
  create: (payload) => api.post('/orders', payload),
  pay: (id, opts) => {
    const body = typeof opts === 'string' ? { method: opts } : (opts || {})
    return api.post(`/orders/${encodeURIComponent(id)}/pay`, body)
  },
  cancel: (id, reason) => api.post(`/orders/${encodeURIComponent(id)}/cancel`, reason ? { reason } : undefined),
  complete: (id) => api.post(`/orders/${encodeURIComponent(id)}/complete`),
  refund: (id) => api.post(`/orders/${encodeURIComponent(id)}/refund`),
  stats: () => api.get('/orders/stats'),
}

export const favApi = {
  list: () => api.get('/favorites'),
  add: (id) => api.put(`/favorites/${encodeURIComponent(id)}`),
  remove: (id) => api.delete(`/favorites/${encodeURIComponent(id)}`),
  toggle: (id) => api.post(`/favorites/${encodeURIComponent(id)}/toggle`),
}

/* ---------- 标品路线模板（GET /api/routes，详情自动 RAG 知识渲染 enrich_knowledge） ---------- */
// 后端线路记录 → 前端模板契约（route_id→id；缺省的展示字段给默认值，保证卡片/编排可用）
function toRouteTemplate(raw = {}) {
  return {
    ...raw,
    id: raw.route_id || raw.id,
    cover: raw.cover || { emoji: '🧩', gradient: 'linear-gradient(135deg,#60A5FA,#8B5CF6)' },
    badges: raw.badges || [],
    product_ids: raw.product_ids || [],
    price_total: Number(raw.price_total) || 0,
    original_total: Number(raw.original_total) || Number(raw.price_total) || 0,
    sales: Number(raw.sales) || 0,
    rating: Number(raw.rating) || 4.5,
    review_count: Number(raw.review_count) || 0,
  }
}

const routeQuery = (params = {}) => {
  const q = new URLSearchParams()
  if (params.city) q.set('city', params.city)
  return q.toString() ? `?${q.toString()}` : ''
}

export const routeTemplatesApi = {
  list: async (params = {}) => {
    const data = await api.get(`/routes${routeQuery(params)}`)
    const items = (Array.isArray(data && data.routes) ? data.routes : []).map(toRouteTemplate)
    return { total: items.length, items }
  },
  detail: async (id) => {
    const data = await api.get(`/routes/${encodeURIComponent(id)}`)
    if (!data || !(data.route_id || data.id)) throw new Error('模板不存在')
    return { template: toRouteTemplate(data) }
  },
}

/* ---------- 标品知识背书（RAG）：逐点检索语料、返回原文与出处 ---------- */
export const catalogApi = {
  health: () => api.get('/catalog/health'),
  ground: (terms, tenantId) => api.post('/catalog/grounding', { terms, tenant_id: tenantId || null }),
}
