/* ============================================================
   TOC 页面共享 mock 数据(静态演示)
   —— 行程书 / AI 任务 / 标品 / 服务大厅
   ============================================================ */

/* —— 品类元信息(浅色体系适配) —— */
export const CATS = {
  景点: { key: 'sight',   color: '#7B8DA0', soft: '#EEF2F6', emoji: '🏛' },
  餐饮: { key: 'food',    color: '#B08968', soft: '#F5EFE7', emoji: '🍜' },
  住宿: { key: 'hotel',   color: '#8B7A9E', soft: '#F0EDF4', emoji: '🏨' },
  交通: { key: 'transit', color: '#6B9A7E', soft: '#ECF3EE', emoji: '🚄' },
  购物: { key: 'shop',    color: '#C1857E', soft: '#F6EBE9', emoji: '🛍' },
  文化: { key: 'culture', color: '#6B7A5C', soft: '#EEF0EA', emoji: '📚' },
}
export const catMeta = (c) => CATS[c] || CATS.景点

/* —— 时段定义(24h 时间线用,分钟) —— */
export const SLOTS = {
  morning:   { label: '上午',   start: 8 * 60 + 30,  len: 180 },
  midday:    { label: '中午',   start: 11 * 60 + 30, len: 120 },
  afternoon: { label: '下午',   start: 14 * 60,      len: 210 },
  evening:   { label: '傍晚',   start: 17 * 60 + 30, len: 150 },
  night:     { label: '夜间',   start: 21 * 60,     len: 720 },
}

/* —— 标品(行程积木) —— */
export const STOPS = [
  { id: 'SKU-0001', name: '拙政园',            cat: '景点', city: '苏州', price: 78,  dwell: '2.5h', slot: 'morning',   rating: 4.8, x: 120.62, y: 31.325, note: '中国四大名园之首,建议早场入园避开人流' },
  { id: 'SKU-0002', name: '苏州博物馆',        cat: '文化', city: '苏州', price: 0,   dwell: '2h',   slot: 'morning',   rating: 4.7, x: 120.63, y: 31.330, note: '贝聿铭封山之作,需提前 7 天预约' },
  { id: 'SKU-0003', name: '平江路历史街区',    cat: '景点', city: '苏州', price: 0,   dwell: '2h',   slot: 'afternoon', rating: 4.6, x: 120.64, y: 31.318, note: '水陆并行双棋盘格局,傍晚灯笼亮起最有味道' },
  { id: 'SKU-0004', name: '松鹤楼 · 苏帮菜',   cat: '餐饮', city: '苏州', price: 158, dwell: '1.5h', slot: 'midday',    rating: 4.5, x: 120.65, y: 31.315, note: '松鼠鳜鱼发源老字号,人均 158' },
  { id: 'SKU-0005', name: '平江府精品民宿',    cat: '住宿', city: '苏州', price: 480, dwell: '8h',   slot: 'night',     rating: 4.8, x: 120.645, y: 31.320, note: '清代老宅改造,含早,闹中取静' },
  { id: 'SKU-0006', name: '虎丘山风景区',      cat: '景点', city: '苏州', price: 60,  dwell: '3h',   slot: 'morning',   rating: 4.6, x: 120.57, y: 31.335, note: '吴中第一名胜,虎丘塔为苏州地标' },
  { id: 'SKU-0007', name: '山塘街摇橹船',      cat: '体验', city: '苏州', price: 120, dwell: '1h',   slot: 'evening',   rating: 4.7, x: 120.60, y: 31.315, note: '七里山塘水上游,夜航灯光更佳' },
  { id: 'SKU-0008', name: '留园',              cat: '景点', city: '苏州', price: 45,  dwell: '2h',   slot: 'afternoon', rating: 4.7, x: 120.59, y: 31.322, note: '四大名园之一,建筑空间艺术典范' },
  { id: 'SKU-0009', name: '吴门人家 · 早茶',   cat: '餐饮', city: '苏州', price: 68,  dwell: '1h',   slot: 'morning',   rating: 4.4, x: 120.63, y: 31.325, note: '苏式头汤面 + 蟹壳黄,本地人早茶据点' },
  { id: 'SKU-0010', name: '诚品书店(苏州)',   cat: '购物', city: '苏州', price: 0,   dwell: '1.5h', slot: 'afternoon', rating: 4.5, x: 120.67, y: 31.310, note: '大陆首家诚品,文艺伴手礼一站购齐' },
  { id: 'SKU-0011', name: '网师园夜花园',      cat: '文化', city: '苏州', price: 100, dwell: '1.5h', slot: 'evening',   rating: 4.8, x: 120.63, y: 31.300, note: '古典园林夜游 + 昆曲评弹实景演出' },
]
CATS['体验'] = { key: 'exp', color: '#C4A87C', soft: '#F6F0E5', emoji: '🎯' }

/* —— 行程书(我编排的) —— */
export const TRIPS = [
  {
    id: 't001', title: '苏州园林三日 · 拙政留园', city: '苏州', days: 3,
    theme: '园林水巷', pace: '从容', people: 2, date: '2026-10-02', budget: 2680,
    stops: 11, cats: 6, template: '园林三日 · 拙政留园', delta: '+ ¥320(加订网师园夜游)',
    dayPlans: [
      {
        day: 1, title: '初见姑苏 · 园林与老街', summary: '落地苏州,先以拙政园与苏州博物馆进入园林语境,傍晚平江路散步收尾。',
        items: [
          { stop: STOPS[0], time: '08:30 - 11:00' },
          { stop: STOPS[1], time: '11:10 - 13:00' },
          { stop: STOPS[3], time: '12:10 - 13:40' },
          { stop: STOPS[2], time: '15:00 - 17:00' },
          { stop: STOPS[4], time: '夜间入住' },
        ],
      },
      {
        day: 2, title: '山塘寻塔 · 水巷夜航', summary: '上午虎丘访吴中第一名胜,下午留园赏空间艺术,夜里山塘街摇橹船看灯。',
        items: [
          { stop: STOPS[8], time: '08:30 - 09:30' },
          { stop: STOPS[5], time: '10:00 - 13:00' },
          { stop: STOPS[7], time: '14:00 - 16:00' },
          { stop: STOPS[6], time: '17:30 - 19:00' },
          { stop: STOPS[4], time: '夜间入住' },
        ],
      },
      {
        day: 3, title: '吴门余韵 · 夜园惊梦', summary: '早茶后诚品选伴手礼,下午自由活动,傍晚网师园夜花园作别苏州。',
        items: [
          { stop: STOPS[8], time: '08:30 - 09:30' },
          { stop: STOPS[9], time: '10:30 - 12:00' },
          { stop: STOPS[10], time: '17:30 - 19:00' },
        ],
      },
    ],
  },
  {
    id: 't002', title: '杭州西湖人文四日', city: '杭州', days: 4,
    theme: '湖山人文', pace: '标准', people: 3, date: '2026-11-06', budget: 4200,
    stops: 9, cats: 5, template: '西湖人文四日', delta: '- ¥180(减去灵隐索道)',
    dayPlans: [
      { day: 1, title: '湖滨初见', summary: '西湖东线漫步,断桥白堤看暮色。', items: [{ stop: STOPS[2], time: '15:00 - 17:30' }] },
      { day: 2, title: '灵隐问禅', summary: '灵隐寺 + 飞来峰,午后龙井茶园。', items: [{ stop: STOPS[1], time: '09:00 - 12:00' }] },
      { day: 3, title: '西溪泛舟', summary: '西溪湿地半日,傍晚河坊街。', items: [{ stop: STOPS[6], time: '14:00 - 16:00' }] },
      { day: 4, title: '运河收尾', summary: '拱宸桥运河畔,午后返程。', items: [{ stop: STOPS[9], time: '10:00 - 12:00' }] },
    ],
  },
]

export const tripById = (id) => TRIPS.find(t => t.id === id) || TRIPS[0]

/* —— AI 规划任务 —— */
export const PLAN_JOBS = [
  {
    id: 'job-20260907-1132', status: 'completed', version: 'v3',
    dest: '苏州', origin: '上海', days: 3, budget: 3000, people: 2, customer: '家庭亲子',
    created: '2026-09-07 11:32', currentAgent: 'Reporter', progress: 100,
    tripId: 't001', parent: null,
  },
  {
    id: 'job-20260908-0915', status: 'running', version: 'v2',
    dest: '杭州', origin: '南京', days: 4, budget: 4500, people: 3, customer: '银发慢游',
    created: '2026-09-08 09:15', currentAgent: 'Itinerary', progress: 62,
    tripId: 't002', parent: 'job-20260907-1132',
  },
  {
    id: 'job-20260909-2010', status: 'pending', version: 'v1',
    dest: '大理', origin: '成都', days: 5, budget: 6000, people: 4, customer: '年轻结伴',
    created: '2026-09-09 20:10', currentAgent: 'Intake', progress: 8,
    tripId: null, parent: null,
  },
]

/* —— 10-Agent 流水线 —— */
export const AGENT_FLOW = [
  { key: 'Intake',    label: '需求受理', desc: '解析预算 / 天数 / 人群偏好' },
  { key: 'Researcher',label: '目的地调研', desc: 'RAG 检索知识库与实时语料' },
  { key: 'Planner',   label: '框架规划', desc: '生成逐日主题与动线骨架' },
  { key: 'Itinerary', label: '行程编排', desc: '标品落位 / 时段校验' },
  { key: 'Budget',    label: '预算测算', desc: '逐项计价与预算对齐' },
  { key: 'Validator', label: '合规校验', desc: '营业时间 / 距离 / 政策' },
  { key: 'Sentiment', label: '情绪预演', desc: '虚拟游客情绪曲线推演' },
  { key: 'Debate',    label: '双辩博弈', desc: '规划方 vs 游客方辩论' },
  { key: 'Mood',      label: '节奏调优', desc: '张弛节奏与体力分配' },
  { key: 'Reporter',  label: '报告生成', desc: '行程书 + 动线图 + 预算表' },
]

/* —— 名导团 —— */
export const GUIDES = [
  { id: 'g1', name: '杜工部', persona: '唐代诗圣 · 人文路线', tone: '沉郁顿挫,引经据典', review: '4.9 · 1.2k 次同行', avatar: '杜', color: '#7B8DA0',
    hello: '「君到姑苏见,人家尽枕河。」苏州的水,要从诗里读起。且随我从盘门说起。' },
  { id: 'g2', name: '苏小馋', persona: '本地美食侦探 · 舌尖路线', tone: '活泼嘴甜,三句不离吃', review: '4.8 · 2.3k 次同行', avatar: '馋', color: '#B08968',
    hello: '来苏州不吃头汤面等于白来!明早六点半,我带你去吃本地人排队的那家~' },
  { id: 'g3', name: '沈园长', persona: '亲子游规划师 · 遛娃路线', tone: '耐心细致,安全第一', review: '4.9 · 860 次同行', avatar: '亲', color: '#6B7A5C',
    hello: '带娃游苏州,节奏要慢、点位要少。我推荐每天只安排两个核心点,午睡雷打不动。' },
]

/* —— 虚拟游客踩点(Swarm) —— */
export const SWARM_REPORTS = [
  { persona: '65 岁退休教师 · 慢节奏', style: '银发慢游', day: 'Day 1', theme: '初见姑苏', verdict: '偏累', tip: 'Day1 拙政园+博物馆连走 4.5h,中途缺一次长休息,建议博物馆后加 30 分钟茶歇。' },
  { persona: '28 岁独自旅行 · 快节奏', style: '特种兵', day: 'Day 2', theme: '山塘寻塔', verdict: '合适', tip: '虎丘-留园动线顺,午间可在山塘街解决,不用折返。' },
  { persona: '带 6 岁娃家庭', style: '亲子', day: 'Day 1', theme: '初见姑苏', verdict: '偏累', tip: '博物馆讲解对孩子偏深,建议换成丝绸博物馆亲子场。' },
]

export const COUNTERFACTS = [
  { giveup: '金鸡湖夜景(往返 26km)', got: '网师园夜花园(园林内)', reason: '跨城折返 1.5h 打断 Day1 节奏,夜花园就在古城区内。', cost: '省 ¥40 车费,少 1.5h 通勤' },
  { giveup: '周庄一日游', got: '山塘街 + 摇橹船', reason: '周庄单程 1.5h,三日行程容不下整日外线。', cost: '省 3h 通勤,体验密度更高' },
]

/* —— 辩论实录 —— */
export const DEBATES = [
  {
    topic: 'Day 2 是否保留虎丘?',
    plan: '虎丘是吴中第一名胜,历史价值高,列为 Day 2 上午锚点,配合留园形成山塘一线。',
    traveler: '游客反馈虎丘商业氛围渐浓,且亲子家庭对塔院兴趣一般,建议换成更松弛的西园寺。',
    verdict: '保留虎丘,但在导览词中弱化购物区动线;亲子客户自动替换为西园寺方案。',
    pro: 68,
  },
  {
    topic: '每日安排 4 个点位是否过密?',
    plan: '标准游客每日 3-4 点位是行业惯例,苏州城区通勤短,可以支撑。',
    traveler: '情绪曲线显示 Day1 下午满意度下滑 18%,疲劳累积早于预期。',
    verdict: '默认节奏调为每日 3 点位 + 1 个弹性点,由 Mood 智能体按人群画像微调。',
    pro: 82,
  },
]

/* —— 商城方案(详情/收藏共用) —— */
export const MALL_PLANS = [
  {
    id: 'p101', name: '园林三日 · 拙政留园', category: '园林水巷', city: '苏州', days: 3,
    pace: '从容', rating: 4.9, poi: 11, sold: 1286, perPrice: 1280, oldPrice: 1480,
    emoji: '🏛', gradient: 'linear-gradient(135deg,#A8B7C4,#7B8DA0)',
    badges: ['电子票', '随买随用', '企业核验'],
    dates: [
      { d: '10-02 周五', left: 4, tight: true }, { d: '10-16 周六', left: 9, tight: false },
      { d: '11-01 周日', left: 6, tight: false }, { d: '11-14 周六', left: 8, tight: false },
    ],
    intro: '以拙政园、留园两大名园为骨架,串联平江路与山塘街水巷,三日读懂苏州园林的空间哲学。',
    include: ['全程 4 晚民宿(含早)', '拙政园 / 留园 / 虎丘门票', '松鹤楼苏帮菜正餐 ×3', '山塘街摇橹船夜航', '全程管家微信响应'],
    exclude: ['往返苏州大交通', '个人消费与保险'],
    dayLines: [
      { day: 1, title: '初见姑苏', spots: ['拙政园', '苏州博物馆', '松鹤楼午宴', '平江路', '平江府民宿'] },
      { day: 2, title: '山塘寻塔', spots: ['吴门早茶', '虎丘', '留园', '山塘街摇橹船'] },
      { day: 3, title: '吴门余韵', spots: ['诚品书店', '网师园夜花园', '返程'] },
    ],
    grounding: ['苏州文旅 2026Q3 官方票价', '平江府民宿 · 谈价备忘 0901', '松鹤楼大众点评 4.5 分(2.1万)'],
  },
  {
    id: 'p102', name: '西湖人文四日', category: '湖山人文', city: '杭州', days: 4,
    pace: '标准', rating: 4.8, poi: 9, sold: 946, perPrice: 1680, oldPrice: null,
    emoji: '🌊', gradient: 'linear-gradient(135deg,#9CA8B5,#5C7A9D)',
    badges: ['电子票', '可改期'],
    dates: [{ d: '11-06 周五', left: 7, tight: false }, { d: '11-20 周五', left: 5, tight: true }],
    intro: '湖东漫步、灵隐问禅、西溪泛舟、运河收尾,四日走完杭州的人文剖面。',
    include: ['3 晚精品酒店(含早)', '灵隐寺 + 飞来峰联票', '西溪湿地船票'],
    exclude: ['往返大交通'],
    dayLines: [
      { day: 1, title: '湖滨初见', spots: ['断桥', '白堤', '湖滨晚茶'] },
      { day: 2, title: '灵隐问禅', spots: ['灵隐寺', '飞来峰', '龙井茶园'] },
    ],
    grounding: ['杭州文旅局 2026 景区目录'],
  },
  {
    id: 'p103', name: '苍洱五日 · 白族家访', category: '湖山人文', city: '大理', days: 5,
    pace: '从容', rating: 4.9, poi: 14, sold: 634, perPrice: 2280, oldPrice: 2580,
    emoji: '🏔', gradient: 'linear-gradient(135deg,#B8C5A8,#6B7A5C)',
    badges: ['电子票', '小团出行'],
    dates: [{ d: '12-04 周五', left: 6, tight: false }],
    intro: '环洱海慢行五日,住进白族院子,赶一次三月街集市。',
    include: ['4 晚海景民宿', '洱海生态骑行装备', '白族家访体验'],
    exclude: ['往返大交通'],
    dayLines: [{ day: 1, title: '古城安顿', spots: ['大理古城', '人民路夜市'] }],
    grounding: ['大理文旅 2026 民宿白名单'],
  },
  {
    id: 'p104', name: '美食四日 · 熊猫基地', category: '美食烟火', city: '成都', days: 4,
    pace: '标准', rating: 4.7, poi: 12, sold: 1520, perPrice: 1880, oldPrice: null,
    emoji: '🌶', gradient: 'linear-gradient(135deg,#C9B299,#B08968)',
    badges: ['电子票'],
    dates: [{ d: '10-23 周五', left: 8, tight: false }],
    intro: '从火锅到苍蝇馆子,四日吃透成都,顺便看完熊猫。',
    include: ['3 晚酒店', '熊猫基地门票', '川菜私厨课堂'],
    exclude: ['往返大交通'],
    dayLines: [{ day: 1, title: '玉林开局', spots: ['玉林路', '小酒馆', '火锅'] }],
    grounding: ['成都发布 · 2026 餐饮推荐榜'],
  },
  {
    id: 'p105', name: '鼓浪屿三日 · 骑楼海岛', category: '海岛度假', city: '厦门', days: 3,
    pace: '慢节奏', rating: 4.6, poi: 8, sold: 980, perPrice: 1480, oldPrice: 1680,
    emoji: '🏝', gradient: 'linear-gradient(135deg,#A8C5D6,#7B8DA0)',
    badges: ['亲子推荐'],
    dates: [{ d: '10-19 周一', left: 6, tight: false }],
    intro: '鼓浪屿 + 骑楼老街 + 沙坡尾,三日把厦门海岛、市井与文创一次走完。',
    include: ['2 晚鼓浪屿民宿', '轮渡船票', '闽南私房菜午餐'],
    exclude: ['往返大交通', '景点大门票以外费用'],
    dayLines: [{ day: 1, title: '鼓浪屿', spots: ['龙头路', '日光岩', '菽庄花园'] }],
    grounding: ['厦门文旅局 · 鼓浪屿游览守则'],
  },
  {
    id: 'p106', name: '长安古都四日 · 兵马俑汉服', category: '古都历史', city: '西安', days: 4,
    pace: '标准', rating: 4.8, poi: 11, sold: 1340, perPrice: 1580, oldPrice: null,
    emoji: '🏯', gradient: 'linear-gradient(135deg,#C5B392,#8C7460)',
    badges: ['人气王', '电子票'],
    dates: [{ d: '10-22 周四', left: 4, tight: false }],
    intro: '兵马俑 + 华清宫 + 永兴坊 + 大唐不夜城,四日穿越长安十二时辰。',
    include: ['3 晚市中心酒店', '兵马俑门票', '汉服体验 1 次'],
    exclude: ['往返大交通'],
    dayLines: [{ day: 1, title: '古城初见', spots: ['永兴坊', '钟鼓楼', '回民街'] }],
    grounding: ['西安文旅 · 博物馆预约指南'],
  },
]

export const planById = (id) => MALL_PLANS.find(p => p.id === id) || MALL_PLANS[0]

/* —— 订单 —— */
export const ORDERS = [
  {
    id: 'SO-20260901-4417', status: 'PAID', statusZh: '待出行', placed: '2026-09-01 21:14',
    planId: 'p101', name: '园林三日 · 拙政留园', category: '园林水巷', city: '苏州', days: 3,
    people: 2, perPrice: 1280, paid: 2560, code: 'HX-8829-4417',
    date: '2026-10-02', fee: '一价全包 · 无隐藏费用', meet: '苏州站东广场 · 全程管家对接', contact: '王女士 138****6621',
  },
  {
    id: 'SO-20260812-3308', status: 'UNPAID', statusZh: '待支付', placed: '2026-08-12 10:02',
    planId: 'p103', name: '苍洱五日 · 白族家访', category: '湖山人文', city: '大理', days: 5,
    people: 2, perPrice: 2280, paid: 0, code: null,
    date: '2026-12-04', fee: '定金制 · 尾款出行前 7 日支付', meet: '大理古城南门 · 司机接机', contact: '王女士 138****6621',
  },
  {
    id: 'SO-20260502-1102', status: 'USED', statusZh: '已完成', placed: '2026-05-02 15:40',
    planId: 'p104', name: '美食四日 · 熊猫基地', category: '美食烟火', city: '成都', days: 4,
    people: 3, perPrice: 1880, paid: 5640, code: null,
    date: '2026-05-28', fee: '一价全包', meet: '成都双流机场接机', contact: '王女士 138****6621',
  },
  {
    id: 'SO-20260401-0917', status: 'CANCELLED', statusZh: '已取消', placed: '2026-04-01 09:17',
    planId: 'p102', name: '西湖人文四日', category: '湖山人文', city: '杭州', days: 4,
    people: 2, perPrice: 1680, paid: 0, code: null,
    date: '2026-04-30', fee: '取消全退 · 已原路退回', meet: '—', contact: '王女士 138****6621',
  },
]

/* —— 服务大厅数据 —— */
export const TRAINS = [
  { no: 'G7315', from: '上海虹桥', to: '苏州', dep: '07:15', arr: '08:02', dur: '47分', price: 39.5, left: '有' },
  { no: 'G7317', from: '上海虹桥', to: '苏州', dep: '08:32', arr: '09:19', dur: '47分', price: 39.5, left: '紧张' },
  { no: 'G102',  from: '上海',     to: '苏州', dep: '09:05', arr: '09:56', dur: '51分', price: 41,   left: '有' },
  { no: 'G7319', from: '上海虹桥', to: '苏州', dep: '10:48', arr: '11:35', dur: '47分', price: 39.5, left: '充足' },
]
export const FLIGHTS = [
  { no: 'MU5137', from: '上海虹桥 SHA', to: '苏南硕放 WUX', dep: '08:20', arr: '09:35', dur: '1h15m', price: 320, discount: '4.8折' },
  { no: 'CZ3907', from: '浦东 PVG',     to: '苏南硕放 WUX', dep: '13:10', arr: '14:30', dur: '1h20m', price: 380, discount: '5.6折' },
]
export const HOTELS = [
  { name: '平江府精品民宿', tier: '舒适型 · 园林老宅', dist: 1.2, nights: '10-02 至 10-05 · 3 晚', price: '¥480/晚起', url: '#' },
  { name: '苏州吴宫泛太平洋', tier: '高档型 · 盘门景区', dist: 2.8, nights: '10-02 至 10-05 · 3 晚', price: '¥820/晚起', url: '#' },
  { name: '全季(观前街店)', tier: '经济连锁', dist: 0.9, nights: '10-02 至 10-05 · 3 晚', price: '¥310/晚起', url: '#' },
]
export const ATTRACTIONS = [
  { name: '拙政园', tags: ['世界遗产', '四大名园'], price: 78, mins: 150, open: '07:30-17:30', addr: '姑苏区东北街178号', url: '#' },
  { name: '虎丘山风景区', tags: ['5A', '吴中第一名胜'], price: 60, mins: 180, open: '07:30-18:00', addr: '姑苏区山塘街虎丘山门内', url: '#' },
  { name: '网师园夜花园', tags: ['夜游', '昆曲实景'], price: 100, mins: 90, open: '19:30-22:00', addr: '姑苏区带城桥路阔家头巷11号', url: '#' },
]
export const MERCHANTS = [
  { name: '松鹤楼(观前店)', cat: '苏帮菜', dist: 0.6, hint: '人均 ¥158', addr: '姑苏区太监弄72号' },
  { name: '吴门人家', cat: '苏式面点', dist: 1.1, hint: '人均 ¥68', addr: '姑苏区西北街151号' },
  { name: '得月楼', cat: '苏帮菜', dist: 0.8, hint: '人均 ¥142', addr: '姑苏区太监弄43号' },
]
export const ENTERTAINMENTS = [
  { name: '网师园古典夜游', type: '园林实景', time: '19:30-22:00', loc: '网师园', price: '¥100' },
  { name: '山塘街昆曲书场', type: '曲艺', time: '20:00-21:30', loc: '山塘街', price: '¥60' },
]
export const CITY_PHOTO = { url: '/covers/c1043.jpg', name: '苏州 · 平江路' }
