// 截图验证脚本：打开新前端各页面，输出截图与 console 错误
// 适配 W5 多页面架构：/plans + /trip/:id + /trip/:id/edit + /trip/:id/map
import { chromium } from 'playwright-core'
import path from 'node:path'
import { homedir } from 'node:os'

const EXE = path.join(homedir(), 'AppData', 'Local', 'ms-playwright', 'chromium-1234', 'chrome-win64', 'chrome.exe')
const BASE = process.argv[2] || 'http://127.0.0.1:8030/index.html'
const OUT = 'D:/Desktop/WL项目/frontend-v2/_shots'

const PAGES = [
  ['home', `${BASE}#/`],
  ['home-cat', `${BASE}#/?focus=cat`],
  ['home-rag', `${BASE}#/?focus=rag`],
  ['services', `${BASE}#/services`],
  ['auth', `${BASE}#/auth`],
  ['plans', `${BASE}#/plans`],
  ['plan-detail', `${BASE}#/plan/plan_fc10ea306638`],
  ['plan-rag', `${BASE}#/plan/plan_fc10ea306638?tab=rag`],
  ['plan-rag-swap', `${BASE}#/plan/plan_fc10ea306638?tab=rag`],
  ['share', `${BASE}#/s/plan_fc10ea306638`],
  ['tob-dashboard', `${BASE}#/b/dashboard`],
  ['tob-approvals', `${BASE}#/b/approvals`],
  ['tob-safety', `${BASE}#/b/safety`],
  ['tob-rag-lab', `${BASE}#/b/rag-lab`],
  ['tob-composer', `${BASE}#/b/composer`],
  ['tob-composer-result', `${BASE}#/b/composer`],
  ['tob-coverage', `${BASE}#/b/coverage`],
  // ===== 标品商城（C 端）=====
  ['malls', `${BASE}#/malls`],
  ['malls-category', `${BASE}#/malls/category/景点`],
  ['malls-detail', `${BASE}#/malls/product/p_zhuozhengyuan`],
  ['malls-search', `${BASE}#/malls/search?q=北京`],
  ['malls-empty', `${BASE}#/malls/search?q=火星`],
  // ===== 行程规划（W5 多页面）=====
  // P1 总览 + 新建弹层（深链）
  ['plans-new', `${BASE}#/plans?new=1`],                                  // 自动打开选模板弹层
  // P2 详情/编辑（localStorage 预置 lt_demo_suzhou）
  ['trip-detail', `${BASE}#/trip/lt_demo_suzhou`],                       // 只读详情
  ['trip-edit-day2', `${BASE}#/trip/lt_demo_suzhou/edit`],                // 编辑态 · 切到第 2 天
  ['trip-edit-confirm', `${BASE}#/trip/lt_demo_suzhou/edit`],             // 编辑态 · Stage2 确认（warn 不阻塞）
  ['trip-edit-saved', `${BASE}#/trip/lt_demo_suzhou/edit`],               // 编辑保存 → 回落只读
  // P3 地图
  ['trip-map', `${BASE}#/trip/lt_demo_suzhou/map`],                       // ECharts 路线图
  ['trip-map-tl', `${BASE}#/trip/lt_demo_suzhou/map`],                    // 24h 时间线视图
  // 兼容：历史 hash 自动 redirect（验证老链接不破）
  ['legacy-planner', `${BASE}#/planner`],                                 // → /plans
  ['legacy-planner-trip', `${BASE}#/planner/trip/lt_demo_suzhou`],        // → /trip/:id
]

const browser = await chromium.launch({ executablePath: EXE, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()

// 预置一条「本地编排行程书」，供 /trip/lt_demo_suzhou 与 /plans 行程书分栏渲染
await page.addInitScript(() => {
  const KEY = 'trailmind.local_trips_v1'
  const cover = (emoji, g1, g2) => ({ emoji, gradient: `linear-gradient(135deg,${g1} 0%,${g2} 100%)` })
  const P = {
    train_1:   { id: 'p_train_1',       name: 'G7068 上海→苏州',   category: '交通', city: '上海→苏州', level: '高铁',   cover: cover('🚄', '#86EFAC', '#22D3EE'), tags: ['高铁'],       price_min: 40,  rating: 4.8, sales: 22520, coords: [121.0, 31.1] },
    zzy:       { id: 'p_zhuozhengyuan', name: '拙政园',           category: '景点', city: '苏州',       level: '5A',    cover: cover('🏛', '#60A5FA', '#A78BFA'), tags: ['园林', '世界遗产'], price_min: 70,  rating: 4.9, sales: 17520, coords: [120.629, 31.324] },
    food2:     { id: 'p_food_2',        name: '哑巴生煎(临顿路店)', category: '餐饮', city: '苏州',     level: '名店',   cover: cover('🥟', '#FCD34D', '#F472B6'), tags: ['小吃'],       price_min: 88,  rating: 4.5, sales: 1620, coords: [120.628, 31.321] },
    lion:      { id: 'p_lion_woods',    name: '狮子林',           category: '景点', city: '苏州',       level: '4A',    cover: cover('🏛', '#60A5FA', '#A78BFA'), tags: ['园林', '假山'], price_min: 40,  rating: 4.6, sales: 3120, coords: [120.624, 31.327] },
    hotel1:    { id: 'p_hotel_1',       name: '南园宾馆',         category: '住宿', city: '苏州',       level: '园林酒店', cover: cover('🏨', '#C4B5FD', '#818CF8'), tags: ['园林', '五星'], price_min: 880, rating: 4.7, sales: 720, coords: [120.625, 31.320] },
    museum:    { id: 'p_museum_suz',    name: '苏州博物馆',       category: '景点', city: '苏州',       level: '免费',   cover: cover('🏛', '#60A5FA', '#A78BFA'), tags: ['博物馆', '贝聿铭'], price_min: 0, rating: 4.8, sales: 8800, coords: [120.626, 31.325] },
    pingjiang: { id: 'p_pingjiang_road', name: '平江路历史街区',   category: '景点', city: '苏州',     level: '-',      cover: cover('🏮', '#FCD34D', '#F472B6'), tags: ['历史街区', '美食'], price_min: 0, rating: 4.7, sales: 3936, coords: [120.633, 31.323] },
  }
  const bk = (k, period, start, tag, p) => ({ key: k, period, start, tag, product: { ...P[p] } })
  const demo = {
    id: 'lt_demo_suzhou',
    template_id: 'rt_suzhou_2d',
    source: 'planner',
    title: '和爸妈的苏州园林 2 日慢游',
    city: '苏州',
    days: 2,
    pace: 'standard',
    theme: '园林 · 文化',
    audience: '银发爸妈',
    season: '春秋',
    cover: cover('🌸', '#F472B6', '#FB923C'),
    travelers: 3,
    budget: 2000,
    start_date: '2026-09-20',
    note: '妈妈腿脚慢，节奏放软；D1 午餐换成哑巴生煎，省下的预算留给平江路买糕点。',
    base_total: 1798,
    delta: -128,
    dayPlans: [
      { day: 1, blocks: [
        bk('b01', 'morning',   '08:00', '去程', 'train_1'),
        bk('b02', 'morning',   '08:30', '',      'zzy'),
        bk('b03', 'midday',    '11:30', '已换',  'food2'),
        bk('b04', 'afternoon', '14:00', '',      'lion'),
        bk('b05', 'night',     '21:00', '入住',  'hotel1'),
      ] },
      { day: 2, blocks: [
        bk('b06', 'morning',   '09:00', '',     'museum'),
        bk('b07', 'afternoon', '14:00', '逛吃', 'pingjiang'),
        bk('b08', 'night',     '21:00', '退房', 'hotel1'),
      ] },
    ],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
  try {
    if (!localStorage.getItem(KEY)) localStorage.setItem(KEY, JSON.stringify([demo]))
  } catch { /* 隐私模式：忽略 */ }
})

const errors = []
let cur = ''
page.on('console', (m) => { if (m.type() === 'error') errors.push(`[${cur}|${page.url()}] ${m.text()}`) })
page.on('pageerror', (e) => errors.push(`[pageerror ${cur}|${page.url()}] ${e.message}\n    ${(e.stack || '').split('\n').slice(1, 4).join('\n    ')}`))

async function waitSel(sel, timeout = 7000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    try { if (await page.$(sel)) return true } catch { /* */ }
    await page.waitForTimeout(150)
  }
  return false
}

for (const [name, url] of PAGES) {
  cur = name
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 })
  } catch { /* */ }
  await page.waitForTimeout(800)

  // 行程系列独立状态：整页刷新（但 plans-new 依赖 ?new=1 触发弹层，不能 reload）
  if (name.startsWith('trip-') || name.startsWith('legacy-')) {
    await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => {})
    await page.waitForTimeout(1100)
  }

  if (name === 'plans-new') {
    await waitSel('.drawer-mask', 3500)
    await page.waitForTimeout(700)
  }

  if (name === 'plan-rag') {
    const ragTab = await page.$('button.tab:has-text("AI 导游问答")')
    if (ragTab) await ragTab.click()
    await page.waitForTimeout(400)
    const ta = await page.$('.tab-body textarea')
    if (ta) {
      await ta.fill('苏州拙政园门票淡旺季分别是多少？老人有优惠吗？')
      const submit = await page.$('.tab-body button.btn-primary')
      if (submit) await submit.click()
      await page.waitForTimeout(2500)
    }
  }
  if (name === 'home-rag') {
    await page.evaluate(() => document.getElementById('ask-rag')?.scrollIntoView({ block: 'center' }))
    await page.waitForTimeout(400)
    const ta = await page.$('.rag-home-card textarea')
    if (ta) {
      await ta.fill('拙政园门票淡旺季分别多少？苏州雨天备选有哪些？')
      const btn = await page.$('.rag-home-card .btn-primary')
      if (btn) await btn.click()
      await page.waitForTimeout(1200)
    }
  }
  if (name === 'tob-rag-lab') {
    const ta = await page.$('.rl-pane textarea')
    if (ta) {
      await ta.fill('北京 5A 景区有哪些？门票多少钱？')
      const btn = await page.$('.rl-pane button.btn-primary')
      if (btn) await btn.click()
      await page.waitForTimeout(1200)
    }
    const ta2 = await page.$('.rl-pane textarea')
    if (ta2) {
      await ta2.fill('火星上有哪些五星酒店？')
      const btn = await page.$('.rl-pane button.btn-primary')
      if (btn) await btn.click()
      await page.waitForTimeout(800)
    }
  }
  if (name === 'home-cat') {
    await page.evaluate(() => document.getElementById('ask-rag')?.scrollIntoView({ block: 'center' }))
    await page.waitForTimeout(400)
    const cat = await page.$('.cat-card:has-text("景点")')
    if (cat) {
      await cat.click()
      await page.waitForTimeout(1200)
    }
  }

  if (name === 'tob-composer-result') {
    await page.waitForTimeout(800)
    const adds = await page.$$('article.product .p-toggle')
    if (adds && adds.length >= 4) {
      for (let i = 0; i < 4; i++) await adds[i].click()
      await page.waitForTimeout(200)
    }
    const gen = await page.$('button.btn-primary.btn-block')
    if (gen) await gen.click()
    await page.waitForTimeout(1500)
  }
  if (name === 'plan-rag-swap') {
    const ragTab = await page.$('button.tab:has-text("AI 导游问答")')
    if (ragTab) await ragTab.click()
    await page.waitForTimeout(400)
    const ta = await page.$('.tab-body textarea')
    if (ta) {
      await ta.fill('苏州拙政园门票淡旺季分别是多少？老人有优惠吗？')
      const submit = await page.$('.tab-body button.btn-primary')
      if (submit) await submit.click()
      await page.waitForTimeout(2200)
    }
    const swapBtn = await page.$('.swap-btn')
    if (swapBtn) {
      await swapBtn.click()
      await page.waitForTimeout(500)
      const confirm = await page.$('.modal-foot .btn-primary')
      if (confirm) await confirm.click()
      await page.waitForTimeout(600)
    }
  }

  // ========== W5 多页面截图分流 ==========

  // P1 总览 + 新建弹层自动开
  if (name === 'plans-new') {
    // 等弹层出现（来自 ?new=1 触发）
    await waitSel('.app-drawer, .picker, .tpl-card, [data-picker]', 3500)
    await page.waitForTimeout(600)
  }

  // P2 详情只读
  if (name === 'trip-detail') {
    await waitSel('.book-hero, .trip-detail-hero, .td-hero, h1')
    await page.waitForTimeout(400)
  }

  // P2 编辑态：从只读点"编辑" → 进编辑页
  if (name === 'trip-edit-day2' || name === 'trip-edit-confirm' || name === 'trip-edit-saved') {
    await waitSel('.tde .edit-head, .tde-day-nav, .edit-head')
    if (name === 'trip-edit-day2') {
      const d2 = await page.$('.day-nav .day-pill:has-text("第 2 天")')
      if (d2) { await d2.click(); await page.waitForTimeout(350) }
    }
    if (name === 'trip-edit-confirm' || name === 'trip-edit-saved') {
      const next = await page.$('.tde .eh-actions button:has-text("下一步")')
      if (next) { await next.click(); await waitSel('.tde .confirm-actions') }
    }
    if (name === 'trip-edit-saved') {
      const save = await page.$('.tde .confirm-actions button.btn-primary')
      if (save) { await save.click(); await waitSel('.book-hero, .td-hero') }
    }
  }

  // P3 地图
  if (name === 'trip-map') {
    await waitSel('.mp-canvas')
    await page.waitForTimeout(1200)
  }
  if (name === 'trip-map-tl') {
    await waitSel('.mp-canvas')
    await page.waitForTimeout(800)
    const tl = await page.$('.mp-tabs button:has-text("时间线")')
    if (tl) { await tl.click(); await waitSel('.tl-bar'); await page.waitForTimeout(400) }
  }

  // 老 hash 自动 redirect（验证不破）
  if (name === 'legacy-planner') {
    await page.waitForTimeout(600)
  }
  if (name === 'legacy-planner-trip') {
    await waitSel('.book-hero, h1')
  }

  await page.waitForTimeout(700)
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true })
  console.log(`ok: ${name}`)
}

console.log(errors.length ? `CONSOLE ERRORS (${errors.length}):\n` + errors.slice(0, 20).join('\n') : 'NO CONSOLE ERRORS')
await browser.close()
