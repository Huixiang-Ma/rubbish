// 前端 mock：3 个新接口的数据契约
// 后端后续接入时只需在 backend/app/api/ 暴露同名路由即可

const CATEGORIES = {
  景点:   { emoji: '🏛', color: '#0EA5E9' },
  餐饮:   { emoji: '🍜', color: '#F59E0B' },
  住宿:   { emoji: '🏨', color: '#8B5CF6' },
  交通:   { emoji: '🚄', color: '#10B981' },
  购物:   { emoji: '🛍', color: '#EC4899' },
  文化:   { emoji: '📚', color: '#6366F1' },
}

// 标品目录：用于 Composer 选品
const PRODUCT_CATALOG = [
  // 苏州
  { id: 'p_zhuozhengyuan', name: '拙政园', category: '景点', city: '苏州', level: '5A', open: '07:30-17:30', ticket: '淡 70 / 旺 90', typical_dwell: '2.5h', best_slot: 'morning', coords: [120.629, 31.324], tags: ['园林', '世界遗产'], demand: 0.95 },
  { id: 'p_lion_woods',     name: '狮子林', category: '景点', city: '苏州', level: '4A', open: '07:30-17:00', ticket: '40', typical_dwell: '1.5h', best_slot: 'morning', coords: [120.624, 31.327], tags: ['园林', '假山'], demand: 0.7 },
  { id: 'p_museum_suz',     name: '苏州博物馆', category: '景点', city: '苏州', level: '免费', open: '09:00-17:00', ticket: '免费(预约)', typical_dwell: '2h', best_slot: 'midday', coords: [120.626, 31.325], tags: ['博物馆', '贝聿铭'], demand: 0.88 },
  { id: 'p_pingjiang_road', name: '平江路历史街区', category: '景点', city: '苏州', level: '-', open: '全天', ticket: '免费', typical_dwell: '2h', best_slot: 'afternoon', coords: [120.633, 31.323], tags: ['历史街区', '美食'], demand: 0.82 },
  { id: 'p_shantang',       name: '山塘街', category: '景点', city: '苏州', level: '-', open: '全天', ticket: '免费', typical_dwell: '2h', best_slot: 'evening', coords: [120.610, 31.319], tags: ['历史街区', '夜景'], demand: 0.78 },
  { id: 'p_food_1',         name: '松鹤楼(观前街店)', category: '餐饮', city: '苏州', level: '老字号', open: '10:30-20:30', ticket: '人均 120', typical_dwell: '1.5h', best_slot: 'midday', coords: [120.628, 31.318], tags: ['苏帮菜'], demand: 0.85 },
  { id: 'p_food_2',         name: '哑巴生煎(临顿路店)', category: '餐饮', city: '苏州', level: '名店', open: '06:30-19:00', ticket: '人均 30', typical_dwell: '0.5h', best_slot: 'midday', coords: [120.628, 31.321], tags: ['小吃'], demand: 0.65 },
  { id: 'p_hotel_1',        name: '南园宾馆', category: '住宿', city: '苏州', level: '园林酒店', open: '全天', ticket: '¥ 880/晚', typical_dwell: '8h', best_slot: 'night', coords: [120.625, 31.320], tags: ['园林', '五星'], demand: 0.6 },
  { id: 'p_hotel_2',        name: '桔子精品(观前街店)', category: '住宿', city: '苏州', level: '商务酒店', open: '全天', ticket: '¥ 480/晚', typical_dwell: '8h', best_slot: 'night', coords: [120.628, 31.319], tags: ['商务'], demand: 0.7 },
  { id: 'p_train_1',        name: 'G7068 上海→苏州', category: '交通', city: '上海→苏州', level: '高铁', open: '08:00-08:25', ticket: '¥ 39.5', typical_dwell: '0.5h', best_slot: 'morning', coords: [121.0, 31.1], tags: ['高铁'], demand: 0.9 },
  { id: 'p_train_2',        name: 'G7219 苏州→上海', category: '交通', city: '苏州→上海', level: '高铁', open: '18:30-18:55', ticket: '¥ 39.5', typical_dwell: '0.5h', best_slot: 'evening', coords: [121.0, 31.1], tags: ['高铁'], demand: 0.9 },

  // 北京
  { id: 'p_forbidden',      name: '故宫博物院', category: '景点', city: '北京', level: '5A', open: '08:30-16:00', ticket: '淡 40 / 旺 60', typical_dwell: '4h', best_slot: 'morning', coords: [116.397, 39.916], tags: ['博物馆', '世界遗产'], demand: 0.98 },
  { id: 'p_temple_heaven',  name: '天坛公园', category: '景点', city: '北京', level: '5A', open: '06:00-22:00', ticket: '联票 34', typical_dwell: '3h', best_slot: 'morning', coords: [116.411, 39.882], tags: ['古建'], demand: 0.8 },
  { id: 'p_summer_palace',  name: '颐和园', category: '景点', city: '北京', level: '5A', open: '06:30-18:00', ticket: '淡 30 / 旺 60', typical_dwell: '4h', best_slot: 'morning', coords: [116.275, 39.999], tags: ['园林'], demand: 0.86 },
  { id: 'p_nanluoguxiang',  name: '南锣鼓巷', category: '景点', city: '北京', level: '-', open: '全天', ticket: '免费', typical_dwell: '2h', best_slot: 'afternoon', coords: [116.403, 39.937], tags: ['胡同', '美食'], demand: 0.82 },
  { id: 'p_quanjude',       name: '全聚德(前门店)', category: '餐饮', city: '北京', level: '老字号', open: '11:00-21:00', ticket: '人均 180', typical_dwell: '1.5h', best_slot: 'midday', coords: [116.397, 39.898], tags: ['烤鸭'], demand: 0.92 },
  { id: 'p_hutong_r',       name: '胡同民宿(南锣店)', category: '住宿', city: '北京', level: '民宿', open: '全天', ticket: '¥ 680/晚', typical_dwell: '8h', best_slot: 'night', coords: [116.404, 39.937], tags: ['民宿'], demand: 0.65 },
  { id: 'p_beijing_ktm',    name: '北京西站→上海虹桥 G1', category: '交通', city: '北京→上海', level: '高铁', open: '09:00-13:28', ticket: '¥ 553', typical_dwell: '4.5h', best_slot: 'morning', coords: [116.32, 39.89], tags: ['高铁'], demand: 0.85 },
]

// 模拟生成算法：根据选中的标品，按 best_slot + 地理就近 + 行程节奏排
function buildItinerary(selectedProducts, days, pace) {
  const slots = ['morning', 'midday', 'afternoon', 'evening']
  const perDay = pace === 'tight' ? 5 : pace === 'relaxed' ? 3 : 4
  const result = []
  let usedIdx = 0
  for (let d = 1; d <= days; d++) {
    const day = { day: d, blocks: [] }
    for (let s = 0; s < perDay && usedIdx < selectedProducts.length; s++) {
      const p = selectedProducts[usedIdx++]
      const start = slots[s] === 'morning' ? '08:30' : slots[s] === 'midday' ? '11:30' : slots[s] === 'afternoon' ? '14:00' : '17:30'
      day.blocks.push({
        slot: slots[s],
        start,
        duration: p.typical_dwell,
        product_id: p.id,
        title: p.name,
        type: p.category,
        note: `${p.city} · ${p.tags.join('、') || '推荐打卡'}`,
      })
    }
    result.push(day)
  }
  const used = result.flatMap(d => d.blocks).length
  const missing = Math.max(0, selectedProducts.length - used)
  return { itinerary: result, missing_slots: missing }
}

// 模拟替换影响计算
function calcSwapImpact(oldP, newP, slot) {
  if (!oldP || !newP) return null
  const dwellOld = parseFloat(oldP.typical_dwell) || 2
  const dwellNew = parseFloat(newP.typical_dwell) || 2
  return {
    time_delta: (dwellNew - dwellOld).toFixed(1) + 'h',
    cost_delta: (parseInt(newP.ticket) || 0) - (parseInt(oldP.ticket) || 0),
    distance_delta: Math.round(Math.hypot(
      (newP.coords?.[0] || 0) - (oldP.coords?.[0] || 0),
      (newP.coords?.[1] || 0) - (oldP.coords?.[1] || 0),
    ) * 100) + ' m',
    warnings: newP.best_slot !== slot ? [`最佳时段不匹配（库内建议 ${newP.best_slot}，当前为 ${slot}）`] : [],
  }
}

export const composerMock = {
  // GET /composer/products?category=&city=
  listProducts(params = {}) {
    let list = PRODUCT_CATALOG
    if (params.category) list = list.filter(p => p.category === params.category)
    if (params.city) list = list.filter(p => p.city.includes(params.city))
    return Promise.resolve({
      total: list.length,
      categories: Object.keys(CATEGORIES),
      products: list,
    })
  },

  // POST /composer/from-products
  compose(body) {
    const ids = body.product_ids || []
    const selected = PRODUCT_CATALOG.filter(p => ids.includes(p.id))
    const days = body.days || 2
    const pace = body.pace || 'standard'
    const { itinerary, missing_slots } = buildItinerary(selected, days, pace)
    const total = selected.reduce((s, p) => s + (parseInt(p.ticket) || 0), 0)
    const budget_estimate = {
      transport: Math.round(total * 0.18),
      lodging: Math.round(total * 0.32),
      food: Math.round(total * 0.28),
      tickets: total,
      total: Math.round(total * 1.78),
    }
    const coverage_score = selected.length > 0 ? Math.min(1, selected.length / (days * 4)) : 0
    return Promise.resolve({
      job_id: 'compose_' + Math.random().toString(36).slice(2, 10),
      itinerary,
      budget_estimate,
      coverage_score: +coverage_score.toFixed(2),
      missing_slots,
      warnings: missing_slots > 0 ? [`仍有 ${missing_slots} 个标品未排入，建议增加天数或减少节奏密度`] : [],
    })
  },

  // POST /composer/preview
  preview(body) {
    const conflicts = body.slots?.filter(s => s.warning).length || 0
    return Promise.resolve({
      conflicts,
      estimated_duration: body.slots?.reduce((s, x) => s + (parseFloat(x.duration) || 0), 0).toFixed(1) + 'h',
      total_distance: '估算中',
    })
  },
}

export const swapMock = {
  // POST /plans/{jobId}/swap-product
  swap(jobId, body) {
    const newP = PRODUCT_CATALOG.find(p => p.id === body.new_product_id)
    // 模拟：从缓存拿旧产品（实际应从 itinerary 里查）
    const oldP = PRODUCT_CATALOG[Math.floor(Math.random() * 5)]
    const impact = calcSwapImpact(oldP, newP, 'morning')
    return Promise.resolve({
      ok: true,
      job_id: jobId,
      day: body.day,
      slot_index: body.slot_index,
      old_product_id: oldP?.id,
      new_product_id: body.new_product_id,
      diff: impact,
      warnings: impact?.warnings || [],
      swap_id: 'swap_' + Math.random().toString(36).slice(2, 8),
    })
  },

  inspect(jobId, body) {
    return this.swap(jobId, body)
  },
}

export const coverageMock = {
  // GET /stats/product-coverage
  overview(params = {}) {
    return Promise.resolve({
      total_plans: 124,
      rag_hit_plans: 98,
      rag_miss_plans: 26,
      hit_rate: 0.79,
      refusal_rate: 0.12,
      empty_rate: 0.09,
      avg_distance: 0.342,
      coverage_by_category: {
        景点: 0.92, 餐饮: 0.78, 住宿: 0.65, 交通: 0.83, 购物: 0.41, 文化: 0.56,
      },
      top_missing: [
        { name: '宠物友好酒店', count: 14 },
        { name: '无障碍设施', count: 11 },
        { name: '高铁站 24h 接送', count: 9 },
        { name: '凌晨航班住宿', count: 7 },
        { name: '小众文化体验', count: 6 },
      ],
    })
  },

  // GET /stats/product-coverage/trend
  trend(params = {}) {
    const days = 14
    const arr = []
    for (let i = 0; i < days; i++) {
      const d = new Date()
      d.setDate(d.getDate() - (days - 1 - i))
      arr.push({
        date: d.toISOString().slice(5, 10),
        hit_rate: +(0.7 + Math.sin(i / 3) * 0.07 + Math.random() * 0.04).toFixed(3),
        refusal_rate: +(0.10 + Math.cos(i / 4) * 0.03 + Math.random() * 0.02).toFixed(3),
        empty_rate: +(0.08 + Math.sin(i / 5) * 0.03 + Math.random() * 0.02).toFixed(3),
      })
    }
    return Promise.resolve({ trend: arr })
  },

  // GET /stats/product-coverage/missing
  missing(params = {}) {
    return Promise.resolve({
      total: 47,
      items: this.overview().then(r => r.top_missing),
    })
  },
}

// 导出供前端直接引用
export { PRODUCT_CATALOG, CATEGORIES }