// 统一 API 封装：同源相对路径（dev 由 Vite proxy 转发到 FastAPI）
const BASE = '/api'

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

/* ---------- 标品 → 行程（行程积木组装器） ---------- */
export const composerApi = {
  // 拉取标品目录（按分类），供 Composer 选择
  listProducts: (params = {}) => api.get('/composer/products', { params }),
  // 提交标品 ID 列表，生成行程模板
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
