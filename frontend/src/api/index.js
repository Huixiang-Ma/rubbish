// 统一 API 封装：同源相对路径（dev 由 Vite proxy 转发到 FastAPI，生产由后端同源挂载）
// 接口面与 backend/app/api/* 一一对应；token 复用 wl_token（与旧版前端/后端口径一致）。
const BASE = '/api'
const TOKEN_KEY = 'wl_token'             // toC 游客端会话
const ADMIN_TOKEN_KEY = 'wl_admin_token' // toB 工作台会话（admin/supervisor/consultant）

// 双端会话：请求按端别附加 token。默认游客 token；toB 端点组（或调用显式 staff:true）带工作台 token，
// 两组会话互不覆盖 —— 工作台登录不顶掉游客端，反之亦然。
const tokenFor = (opts = {}) => localStorage.getItem(opts.staff ? ADMIN_TOKEN_KEY : TOKEN_KEY)

const toQs = (params = {}) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
  return q.toString() ? `?${q.toString()}` : ''
}

async function request(method, path, body, opts = {}) {
  const headers = { ...(opts.headers || {}) }
  if (opts.rawBody !== undefined) {
    // 二进制直传（文件上传）：body 传 ArrayBuffer/Blob，浏览器自动设置 Content-Type
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  const token = tokenFor(opts)
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: opts.rawBody !== undefined ? opts.rawBody : (body !== undefined ? JSON.stringify(body) : undefined),
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
  const text = await res.text()
  return text ? JSON.parse(text) : null
}

export const api = {
  get: (p, o) => request('GET', p, undefined, o),
  post: (p, b, o) => request('POST', p, b, o),
  put: (p, b, o) => request('PUT', p, b, o),
  delete: (p, o) => request('DELETE', p, undefined, o),
  sse: (path, onEvent, onDone) => {
    const token = localStorage.getItem(TOKEN_KEY)
    const es = new EventSource(`${BASE}${path}${token ? `?token=${token}` : ''}`)
    es.onmessage = (ev) => {
      if (ev.data === 'done') { es.close(); onDone && onDone(); return }
      try { onEvent(JSON.parse(ev.data)) } catch { onEvent({ text: ev.data }) }
    }
    es.onerror = () => { es.close(); onDone && onDone() }
    return es
  },
}

/* ---------- 行程规划 ----------
 * 端别口径：list/approval/intervene/feedback/memory/interventions/audit/diff/export 属工作台；
 * mine/创建/状态/结果/replan 属游客端（replan 服务端按归属放行）。status/result 公开。
 */
export const plansApi = {
  create: (payload) => api.post('/plans', payload),
  list: (params = {}) => api.get(`/plans${toQs(params)}`, { staff: true }),
  mine: () => api.get('/plans/mine'),
  status: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}`),
  result: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/result`),
  audit: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/audit`, { staff: true }),
  diff: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/diff`, { staff: true }),
  approval: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/approval`, body, { staff: true }),
  replan: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/replan`, body),
  feedback: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/feedback`, body, { staff: true }),
  export: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/export`, body, { staff: true }),
  intervene: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/intervene`, body, { staff: true }),
  memory: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/memory`, { staff: true }),
  interventions: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/interventions`, { staff: true }),
}

/* ---------- 体验接口（辩论 / 名导 / 踩点 / 反事实 / 地图 / 问答） ---------- */
export const expApi = {
  map: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/map`),
  nearby: (jobId, kind) => api.get(`/plans/${encodeURIComponent(jobId)}/nearby?kind=${kind}`),
  debates: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/debates`),
  counterfactual: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/counterfactual`),
  swarm: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/swarm`),
  guides: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/guides`),
  dialogue: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/dialogue`, body),
  agentOutputs: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/agent-outputs`),
  debateVote: (jobId, side) => api.post(`/plans/${encodeURIComponent(jobId)}/debate/vote`, { side }),
}

/* ---------- toB 治理（工作台会话） ---------- */
export const govApi = {
  pendingApprovals: (tenant) => api.get(`/approvals/pending${toQs(tenant ? { tenant } : {})}`, { staff: true }),
  feedbacks: (params = {}) => api.get(`/feedbacks${toQs(params)}`, { staff: true }),
  stats: (tenant) => api.get(`/stats/overview${toQs(tenant ? { tenant } : {})}`, { staff: true }),
  safety: () => api.get('/safety/summary', { staff: true }),
  auditCsvUrl: () => `${BASE}/audit/export.csv`,
  integrations: () => api.get('/integrations/status', { staff: true }),
  priceDrift: (jobId) => api.get(`/stats/price-drift${jobId ? `?job_id=${encodeURIComponent(jobId)}` : ''}`, { staff: true }),
}

/* ---------- 服务大厅 ---------- */
export const svcApi = {
  travel: (destination, origin, days) =>
    api.get(`/services/travel?destination=${encodeURIComponent(destination)}&origin=${encodeURIComponent(origin || '')}&days=${days}`),
  byKind: (kind, destination, origin) =>
    api.get(`/services/${kind}?destination=${encodeURIComponent(destination || '')}&origin=${encodeURIComponent(origin || '')}`),
  cityPhoto: (destination) =>
    api.get(`/services/city/photo?destination=${encodeURIComponent(destination)}`),
  planPhotos: (destination, spots) =>
    api.get(`/services/plan/photos?destination=${encodeURIComponent(destination || '')}&spots=${encodeURIComponent(spots || '')}`),
  bookingClick: (kind, jobId = null) => api.post('/services/booking/click', { kind, job_id: jobId }),
}

/* ---------- 认证 ---------- */
export const authApi = {
  login: (realm, username, password) => api.post('/auth/login', { realm, username, password }),
  loginSms: (phone, smsCode) => api.post('/auth/login', { realm: 'toc', phone, sms_code: smsCode }),
  register: (body) => api.post('/auth/register', body),
  requestCode: (phone) => api.post('/auth/request-code', { phone }),
  resetPassword: (phone, smsCode, password) => api.post('/auth/reset-password', { phone, sms_code: smsCode, password }),
  me: () => api.get('/auth/me'),
  tobAccounts: () => api.get('/auth/tob/accounts', { staff: true }),
  tobAccountCreate: (body) => api.post('/auth/tob/accounts', body, { staff: true }),
  tobAccountReset: (username, password) => api.post(`/auth/tob/accounts/${encodeURIComponent(username)}/reset`, { password }, { staff: true }),
  tobAccountDelete: (username) => api.delete(`/auth/tob/accounts/${encodeURIComponent(username)}`, { staff: true }),
}

/* ---------- RAG 知识问答（同步 ask + POST/SSE 流式 chat） ---------- */
export const ragApi = {
  ask: (message, topK = 3, tenantId) =>
    api.post('/rag/ask', { message, top_k: topK, tenant_id: tenantId || null }),
  chat: (message, topK = 3, tenantId, { onMeta, onToken, onDone, onError, signal } = {}) => {
    const token = localStorage.getItem(TOKEN_KEY)
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

/* ---------- 标品 → 行程（RAG 选品 + 组装器） ---------- */
export const composerApi = {
  listProducts: (params = {}) => api.get(`/composer/products${toQs(params)}`),
  searchProducts: (q, params = {}) => api.get(`/composer/search${toQs({ q, ...params })}`),
  compose: (body) => api.post('/composer/from-products', body),
  preview: (body) => api.post('/composer/preview', body),
}

/* ---------- 行程中标品替换 ---------- */
export const swapApi = {
  swap: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/swap-product`, body),
  inspect: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/swap-product/inspect`, body),
}

/* ---------- 标品覆盖率分析（工作台会话） ---------- */
export const coverageApi = {
  overview: (params = {}) => api.get(`/stats/product-coverage${toQs(params)}`, { staff: true }),
  trend: (params = {}) => api.get(`/stats/product-coverage/trend${toQs(params)}`, { staff: true }),
  missing: (params = {}) => api.get(`/stats/product-coverage/missing${toQs(params)}`, { staff: true }),
}

/* ---------- 评分沉淀 / 知识库 / 联网问答助手 ---------- */
export const assistApi = {
  getRating: (jobId) => api.get(`/plans/${encodeURIComponent(jobId)}/rating`),
  rate: (jobId, body) => api.post(`/plans/${encodeURIComponent(jobId)}/rating`, body),
  rateIngest: (jobId) => api.post(`/plans/${encodeURIComponent(jobId)}/rate-ingest`),
  rateListing: (jobId) => api.post(`/plans/${encodeURIComponent(jobId)}/rate-listing`),
  kbList: () => api.get('/kb/docs', { staff: true }),
  kbCreate: (body) => api.post('/kb/docs', body, { staff: true }),
  // 文档文件直传（PDF/DOCX 等）：二进制 body + 文件名/标签走 query，服务端 document_ingest 解析
  kbCreateFile: async (file, tags = []) => {
    const buf = await file.arrayBuffer()
    const qs = `?filename=${encodeURIComponent(file.name)}&tags=${encodeURIComponent(tags.join(','))}`
    return request('POST', `/kb/docs/file${qs}`, undefined, { staff: true, rawBody: buf })
  },
  kbDelete: (id) => api.delete(`/kb/docs/${encodeURIComponent(id)}`, { staff: true }),
  assistant: (message, topK = 3) => api.post('/rag/assistant', { message, top_k: topK }),
  // 数据智能闭环：反馈 / 缺口工单 / 引用统计
  ragFeedback: (query, verdict, jobIds) => api.post('/rag/feedback', { query, verdict, job_ids: jobIds }),
  ragGaps: () => api.get('/rag/gaps', { staff: true }),
  ragCitations: () => api.get('/rag/citations', { staff: true }),
  // 素材草稿（文档抽取 → 人工确认入库）
  kbDrafts: (status) => api.get(`/kb/drafts${status ? `?status=${status}` : ''}`, { staff: true }),
  kbDraftApprove: (id) => api.post(`/kb/drafts/${encodeURIComponent(id)}/approve`, undefined, { staff: true }),
  kbDraftReject: (id) => api.post(`/kb/drafts/${encodeURIComponent(id)}/reject`, undefined, { staff: true }),
}

/* ---------- 商业闭环：在售方案 / 标品素材 / 订单 / 收藏 ---------- */
export const planShopApi = {
  list: (params = {}) => api.get(`/plan-products${toQs(params)}`),
  categories: () => api.get('/plan-products/categories'),
  detail: (id) => api.get(`/plan-products/${encodeURIComponent(id)}`),
  featured: () => api.get('/plan-products/featured'),
  top: () => api.get('/plan-products/top'),
  manageList: (p = {}) => api.get(`/plan-products/manage${toQs(p)}`, { staff: true }),
  create: (d) => api.post('/plan-products', d, { staff: true }),
  update: (id, patch) => api.put(`/plan-products/${encodeURIComponent(id)}`, patch, { staff: true }),
  setStatus: (id, listed) => api.post(`/plan-products/${encodeURIComponent(id)}/status`, { listed }, { staff: true }),
  remove: (id) => api.delete(`/plan-products/${encodeURIComponent(id)}`, { staff: true }),
}
export const productsApi = {
  categories: () => api.get('/products/categories'),
  // POI 批量拉取（素材自动化）：按城市拉候选，人工勾选后走 create 入库
  poiCandidates: (city) => api.get(`/stats/poi-candidates?city=${encodeURIComponent(city)}`, { staff: true }),
  list: (p = {}) => api.get(`/products${toQs(p)}`),
  detail: (id) => api.get(`/products/${encodeURIComponent(id)}`),
  manageList: (p = {}) => api.get(`/products/manage${toQs(p)}`, { staff: true }),
  create: (d) => api.post('/products', d, { staff: true }),
  update: (id, patch) => api.put(`/products/${encodeURIComponent(id)}`, patch, { staff: true }),
  setStatus: (id, listed) => api.post(`/products/${encodeURIComponent(id)}/status`, { listed }, { staff: true }),
  remove: (id) => api.delete(`/products/${encodeURIComponent(id)}`, { staff: true }),
}

// 订单：toB 视图传 { staff: true } 走工作台会话看全量；toC 默认游客会话按账号隔离
export const ordersApi = {
  list: (params = {}, reqOpts) => api.get(`/orders${toQs(params)}`, reqOpts),
  detail: (id, reqOpts) => api.get(`/orders/${encodeURIComponent(id)}`, reqOpts),
  create: (payload) => api.post('/orders', payload),
  pay: (id, opts, reqOpts) => {
    const body = typeof opts === 'string' ? { method: opts } : (opts || {})
    return api.post(`/orders/${encodeURIComponent(id)}/pay`, body, reqOpts)
  },
  cancel: (id, reason, reqOpts) => api.post(`/orders/${encodeURIComponent(id)}/cancel`, reason ? { reason } : undefined, reqOpts),
  complete: (id, reqOpts) => api.post(`/orders/${encodeURIComponent(id)}/complete`, undefined, reqOpts),
  refund: (id, reqOpts) => api.post(`/orders/${encodeURIComponent(id)}/refund`, undefined, reqOpts),
  stats: (reqOpts) => api.get('/orders/stats', reqOpts),
}

export const favApi = {
  list: () => api.get('/favorites'),
  add: (id) => api.put(`/favorites/${encodeURIComponent(id)}`),
  remove: (id) => api.delete(`/favorites/${encodeURIComponent(id)}`),
  toggle: (id) => api.post(`/favorites/${encodeURIComponent(id)}/toggle`),
}

/* ---------- 标品路线模板 ---------- */
export const routeTemplatesApi = {
  list: async (params = {}) => {
    const data = await api.get(`/routes${toQs(params)}`)
    const items = (Array.isArray(data && data.routes) ? data.routes : [])
      .map(r => ({ ...r, id: r.route_id || r.id }))
    return { total: items.length, items }
  },
  detail: async (id) => {
    const data = await api.get(`/routes/${encodeURIComponent(id)}`)
    if (!data || !(data.route_id || data.id)) throw new Error('模板不存在')
    return { template: { ...data, id: data.route_id || data.id } }
  },
}

/* ---------- 标品知识背书（RAG grounding） ---------- */
export const catalogApi = {
  health: () => api.get('/catalog/health'),
  ground: (terms, tenantId) => api.post('/catalog/grounding', { terms, tenant_id: tenantId || null }),
}
