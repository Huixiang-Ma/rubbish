// 行程书校验规则（W2 双态编辑器 / 保存前置 / 健康提示共用）
// ---------------------------------------------------------------------------
// 设计原则：
//  - 纯函数、无副作用，输入当前 draft（{ days, meta }）即可复算；
//  - 返回 [{ level: 'error'|'warn', code, text }]，error 会阻止保存并高亮，
//    warn 仅提示不阻塞（给用户留“自由安排”的空间）；
//  - 规则针对 时段模型：day-slot(morning/midday/afternoon/evening) 与
//    night(夜宿) 不能倒挂、night 每夜至多一间、非返程日不允许断宿。
// ---------------------------------------------------------------------------

const DAY_SLOTS = ['morning', 'midday', 'afternoon', 'evening']

function dayIndex(days) {
  return (days || []).reduce((m, d) => { m[d.day] = d; return m }, {})
}

function dayOf(d) {
  return d && d.blocks ? d.blocks : []
}

/**
 * 校验一份行程草稿
 * @param {object} draft { days: [{day, blocks}], meta: { title } }
 * @returns {Array<{level:'error'|'warn', code:string, text:string}>}
 */
export function validateTripDraft({ days = [], meta = {} } = {}) {
  const issues = []
  const list = (days || []).slice().sort((a, b) => (a.day || 0) - (b.day || 0))
  const push = (level, code, text) => issues.push({ level, code, text })

  // V1 标题必填
  if (!String(meta.title || '').trim()) {
    push('error', 'V1_TITLE_REQUIRED', '行程名称必填，请先给行程书起个名字')
  }

  const dayCount = list.length
  if (!dayCount) {
    push('error', 'V8_NO_DAYS', '行程还没有任何天次，请返回编排补全')
    return issues
  }

  let hasAnyNight = false
  list.forEach(d => {
    const blocks = dayOf(d)
    const nth = `第 ${d.day} 天`

    if (!blocks.length) {
      push('warn', 'V6_EMPTY_DAY', `${nth}还没有任何停留（可留空自由安排，但保存前建议补一个）`)
      return
    }

    // V3 夜宿唯一：同一天最多一间住宿
    const nights = blocks.filter(b => b.period === 'night')
    if (nights.length > 1) {
      push('error', 'V3_NIGHT_DUP', `${nth}安排了 ${nights.length} 个夜宿停留，一晚只需一间住宿`)
    }
    if (nights.length) hasAnyNight = true

    // V4 夜宿置底：day-slot 不允许出现在 night 之后（时间线倒挂）
    const firstNight = blocks.findIndex(b => b.period === 'night')
    if (firstNight >= 0) {
      const after = blocks.slice(firstNight + 1).filter(b => b.period !== 'night')
      if (after.length) {
        const name = after[0].product && after[0].product.name
        push('error', 'V4_SLOT_AFTER_NIGHT', `${nth}在夜宿之后还排了「${name || after[0].period}」，白天行程应放在住宿之前`)
      }
    }

    // V5 同日重复标品
    const seen = {}
    blocks.forEach(b => {
      const id = b.product && b.product.id
      if (!id) return
      seen[id] = (seen[id] || 0) + 1
    })
    Object.keys(seen).forEach(id => {
      if (seen[id] > 1) {
        const b = blocks.find(x => x.product && x.product.id === id)
        push('warn', 'V5_DUP_POI', `${nth}重复安排了「${b.product.name}」${seen[id]} 次，考虑换成同城同类的其他标品`)
      }
    })

    // V2 断宿：非最后一天必须安排夜宿（住宿）
    const isLast = d.day === list[list.length - 1].day
    if (!isLast && !nights.length) {
      push('warn', 'V2_NO_NIGHT', `${nth}没有夜宿住宿 —— 跨天行程建议安排住宿，返程日除外`)
    }

    // V7 返程日留宿提醒（多住宿循环时可能出现）
    if (isLast && nights.length && dayCount > 1) {
      push('warn', 'V7_NIGHT_ON_LAST', `${nth}是最后一天仍安排了夜宿，会多算一晚住宿（可忽略或移除）`)
    }
  })

  // V9 多日行程全程无住宿（非一日游）
  if (dayCount > 1 && !hasAnyNight) {
    push('error', 'V9_NO_LODGING', '这份多日行程没有任何住宿，请至少为中间天次安排夜宿')
  }

  // V10 时段漂移：同一天 day-slot 出现两个同 slot（重叠锁：同一时段只放一个白天块）
  list.forEach(d => {
    const used = {}
    dayOf(d).forEach(b => {
      if (b.period === 'night' || !DAY_SLOTS.includes(b.period)) return
      used[b.period] = (used[b.period] || 0) + 1
    })
    const dup = Object.keys(used).find(k => used[k] > 1)
    if (dup) {
      push('warn', 'V10_SLOT_OVERLAP', `第 ${d.day} 天有多个停留落在同一时段（${dup}），时间会重叠，建议分散到不同时段`)
    }
  })

  return issues
}

/** 只取 error 级问题（用于按钮禁用 / toast 首个阻塞原因） */
export function blockingIssues(issues) {
  return (issues || []).filter(i => i.level === 'error')
}

/** 友好汇总：`2 个问题待处理 · 1 条建议` */
export function issueSummary(issues = []) {
  const err = issues.filter(i => i.level === 'error').length
  const warn = issues.length - err
  if (!issues.length) return ''
  const parts = []
  if (err) parts.push(`${err} 个问题待处理`)
  if (warn) parts.push(`${warn} 条建议`)
  return parts.join(' · ')
}
