// 标品反解析器：把 `sources[i].content`（"【title】正文..."）解析成结构化标品卡
// 与后端 sync_rag_corpus.py::build_text 字段拼接规则对齐。
//
// 来源文本形态（build_text 输出）：
//   "{name}。位于{city} {address}。景区等级：{level}。开放时间：{open_time}。门票信息：{ticket}。{description}。"
//
// 输入形态（chunker 输出）：
//   "【title】chunk_text..."  ← title 是 ingest 时拼上的源文件名/标品名
//
// 设计：纯函数 + 零依赖；不抛异常（解析失败降级返回原始 content）

const CATEGORY_RULES = [
  { key: 'sight',  icon: '🏛', label: '景点',  match: ['景区', '景点', '博物馆', '公园', '寺庙', '文物', '古迹', '故居'] },
  { key: 'food',    icon: '🍜', label: '餐饮',  match: ['餐厅', '美食', '火锅', '小吃', '酒家', '饭店', '中餐厅', '日料', '咖啡'] },
  { key: 'hotel',   icon: '🏨', label: '住宿',  match: ['酒店', '宾馆', '民宿', '客栈', '招待所', '旅馆'] },
  { key: 'transit', icon: '🚄', label: '交通',  match: ['机场', '火车站', '高铁', '地铁', '公交', '出租', '航站楼', '汽车站'] },
  { key: 'shop',    icon: '🛍', label: '购物',  match: ['商场', '购物', '百货', '超市', '集市', '免税', '小店', '专卖店'] },
  { key: 'culture', icon: '📜', label: '文化',  match: ['历史', '文化', '非遗', '民俗', '节庆', '传说', '典故', '背景'] },
]

const FIELD_PATTERNS = [
  { key: 'city',        label: '所在城市', icon: '🌆', rx: /位于([^\s，。；]+(?:\s*[^\s，。；]+)*)/ },
  { key: 'address',     label: '地址',     icon: '📍', rx: null /* 从 city 后面继续拆 */ },
  { key: 'level',       label: '景区等级', icon: '⭐', rx: /景区等级[：:]\s*([^。]+?)(?=[。；]|$)/ },
  { key: 'open_time',   label: '开放时间', icon: '🕐', rx: /开放时间[：:]\s*([^。]+?)(?=[。；]|$)/ },
  { key: 'ticket',      label: '门票',     icon: '🎫', rx: /门票信息[：:]\s*([^。]+?)(?=[。；]|$)/ },
  { key: 'description', label: '简介',     icon: '📝', rx: null /* 默认正文剩余部分 */ },
]

// 标题前缀抽取：【xxx】
function extractTitle(raw) {
  if (!raw) return ''
  const m = String(raw).match(/^【(.+?)】/)
  return m ? m[1].trim() : ''
}

// 分类判定：先按 title 关键词，再回退到正文
function detectCategory(title, text) {
  const hay = (title + ' ' + text).toLowerCase()
  for (const rule of CATEGORY_RULES) {
    if (rule.match.some(kw => hay.includes(kw.toLowerCase()))) return rule
  }
  return { key: 'other', icon: '📦', label: '其他' }
}

// 解析单条 source → 标品卡
export function parseProduct(source) {
  if (!source || typeof source !== 'object') return null
  const rawContent = source.content || ''
  const distance = Number(source.distance ?? source.score ?? 1) || 1

  // 1. 标题
  const title = extractTitle(rawContent) || source.title || source.name || '未命名标品'
  const body  = extractTitle(rawContent) ? rawContent.replace(/^【.+?】/, '').trim() : rawContent

  // 2. 字段抽取
  const fields = {}
  for (const f of FIELD_PATTERNS) {
    if (!f.rx) continue
    const m = body.match(f.rx)
    if (m) fields[f.key] = m[1].trim()
  }

  // city / address 拆分：city 抓"位于X Y"→前段 X、后段 Y
  if (fields.city) {
    const locMatch = body.match(/位于([^\s，。；]+(?:\s+[^\s，。；]+)*)/)
    if (locMatch) {
      const segs = locMatch[1].trim().split(/\s+/)
      fields.city    = segs[0] || ''
      fields.address = segs.slice(1).join(' ') || ''
    }
  }

  // description：去掉所有已抽取字段后的剩余文本（截断）
  let descBody = body
  for (const f of FIELD_PATTERNS) {
    if (f.rx) descBody = descBody.replace(f.rx, '')
  }
  descBody = descBody.replace(/位于[^\s，。；]+(?:\s+[^\s，。；]+)*/, '').trim()
  descBody = descBody.replace(/^[。；,\s]+|[。；,\s]+$/g, '')
  if (descBody) fields.description = descBody

  // 3. 分类
  const category = detectCategory(title, body)

  // 4. 距离置信度（distance 越小越好）
  const confidence = distance < 0.35 ? 'high' : distance < 0.6 ? 'mid' : 'low'

  return {
    title,
    category,
    fields,
    confidence,
    distance,
    raw: rawContent,
    sourceMeta: source,
  }
}

// 批量解析并按分类聚合（给 toB 目录视图用）
export function parseAndGroup(sources = []) {
  const products = sources.map(parseProduct).filter(Boolean)
  const groups = {}
  for (const p of products) {
    if (!groups[p.category.key]) groups[p.category.key] = { ...p.category, items: [] }
    groups[p.category.key].items.push(p)
  }
  // 按 CATEGORY_RULES 顺序输出
  return CATEGORY_RULES
    .map(r => groups[r.key])
    .filter(Boolean)
    .concat(groups.other ? [groups.other] : [])
}

export const PRODUCT_CATEGORIES = CATEGORY_RULES