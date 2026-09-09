// 标品模板 → 逐日行程编排（唯一事实来源）
// ---------------------------------------------------------------------------
// 编排逻辑从 PlannerView.buildDays 抽出为纯函数：
//   - PlannerView（向导逐步编排）与「一键加入我的行程」共用同一实现；
//   - 后续「行程书编辑双态」将整体迁移到本工厂 + 校验器之上。
// 输入：模板 tpl（含 product_ids[]）+ 全量商品（数组或 Map id→item）
// 输出：dayPlans = [{ day, blocks:[{ key, period, start, tag, product }] }]
// ---------------------------------------------------------------------------

/** 默认出发日（演示 / 截图环境稳定；接入后端后由用户日期决定） */
export const DEFAULT_START_DATE = '2026-09-20'

const DAY_SLOTS = ['morning', 'midday', 'afternoon', 'evening']
const PERIOD_START = {
  morning: '08:30', midday: '11:30', afternoon: '14:00',
  evening: '17:30', night: '21:00',
}

/** 标品 → 行程块内嵌快照（含坐标，供地图页直接使用） */
export function snapshotProduct(p) {
  if (!p) return p
  return {
    id: p.id, name: p.name, category: p.category, city: p.city,
    cover: p.cover, badges: p.badges || [], tags: p.tags || [],
    price_min: p.price_min || 0, rating: p.rating, sales: p.sales, level: p.level,
    coords: (Array.isArray(p.coords) && p.coords.length === 2) ? p.coords.slice() : null,
  }
}

/** 统一成 Map<id, item> */
export function toProdMap(products) {
  return products instanceof Map ? products : new Map((products || []).map(p => [p.id, p]))
}

/** 同一批 POI 的时段分配：餐饮尽量占午餐位，其余按空位顺序 */
function slotFor(slice, i) {
  const pool = DAY_SLOTS.slice()
  const foodIdx = slice.findIndex(p => p.category === '餐饮')
  const used = {}
  const slots = slice.map((p, ix) => {
    let s
    if (p.category === '餐饮' && ix === foodIdx && !used.midday) s = 'midday'
    else s = pool.find(x => !used[x]) || pool[pool.length - 1]
    used[s] = true
    return s
  })
  return slots[i] || 'afternoon'
}

function mkBlock(p, period, start, tag) {
  return {
    key: 'b_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 7),
    period, start, tag,
    product: snapshotProduct(p),
  }
}

/**
 * 核心编排：把模板 product_ids + 可选种子商品排成逐日块
 * @param {object} tpl     路线模板 { id, days, product_ids[] }
 * @param {Array|Map} products  全量标品（用于解析 product_ids）
 * @param {object} [seed]  种子标品（从商品详情「用模板排行程」进入时预置，插到首日）
 * @returns {Array} dayPlans
 */
export function buildDaysFromTemplate(tpl, products, seed) {
  const map = toProdMap(products)
  if (!tpl) return []
  let ids = (tpl.product_ids || []).filter(id => map.has(id))
  if (seed && !ids.includes(seed.id)) ids = [seed.id, ...ids]
  const picks = ids.map(id => map.get(id))

  const hotels = picks.filter(p => p.category === '住宿')
  const trans = picks.filter(p => p.category === '交通')
  const dayItems = picks.filter(p => p.category !== '住宿' && p.category !== '交通')
  const perDay = Math.max(2, Math.min(4, Math.ceil(dayItems.length / (tpl.days || 1))))

  const days = []
  let idx = 0
  for (let d = 1; d <= (tpl.days || 1); d++) {
    const slice = dayItems.slice(idx, idx + perDay)
    idx += perDay
    const blocks = []
    if (d === 1 && trans.length) blocks.push(mkBlock(trans[0], 'morning', '08:00', '去程'))
    slice.forEach((p, i) => blocks.push(mkBlock(p, slotFor(slice, i), PERIOD_START[slotFor(slice, i)], '')))
    if (d === tpl.days && trans.length > 1) {
      blocks.push(mkBlock(trans[trans.length - 1], 'evening', '18:30', '返程'))
    }
    const h = hotels.length ? hotels[(d - 1) % hotels.length] : null
    if (h) blocks.push(mkBlock(h, 'night', PERIOD_START.night, d === tpl.days && hotels.length > 1 ? '退房' : '入住'))
    days.push({ day: d, blocks })
  }
  return days
}
