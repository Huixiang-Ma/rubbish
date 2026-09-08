// 截图验证脚本：打开新前端各页面，输出截图与 console 错误
import { chromium } from 'playwright-core'
import path from 'node:path'
import { homedir } from 'node:os'

const EXE = path.join(homedir(), 'AppData', 'Local', 'ms-playwright', 'chromium-1234', 'chrome-win64', 'chrome.exe')
const BASE = process.argv[2] || 'http://127.0.0.1:8030/v2/index.html'
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
]

const browser = await chromium.launch({ executablePath: EXE, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()

// 拦截 /api/rag/*：本地 Ollama 在演示环境不可达，用 mock 数据渲染前端
// mock 数据按后端 build_text() 形态构造，让前端 productParser 能解析出标品字段
await page.addInitScript(() => {
  const originalFetch = window.fetch
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input?.url || '')
    if (url.includes('/api/rag/ask')) {
      const body = JSON.parse(init?.body || '{}')
      const q = body.message || ''
      const mock = {
        mode: 'llm',
        answer: `依据知识库检索结果，关于「${q}」的答复如下：\n\n拙政园门票淡旺季价格根据 2019 年 14 号文调整，淡季（10 月 31 日 - 次年 4 月 15 日）门票 70 元/位，旺季（4 月 16 日 - 10 月 30 日）门票 90 元/位，符合学生/老人证件可享半价优惠 [1][2]。建议提前一天通过"苏州园林旅游"公众号预约 [3]。`,
        sources: [
          { content: '【苏发改服价〔2019〕14 号】文件规定：拙政园位于江苏 苏州 姑苏区东北街178号。景区等级：AAAAA。开放时间：07:30-17:30。门票信息：淡季70元/旺季90元。江南古典园林代表，分东中西三部分，与苏州博物馆相距约 600 米。', distance: 0.123, doc_id: '苏发改服价2019_14号', tenant_id: 'public' },
          { content: '【zhuozhengyuan_intro】拙政园位于江苏 苏州 姑苏区东北街178号。景区等级：AAAAA。开放时间：07:30-17:30。门票信息：淡季70元/旺季90元。半价优惠：在校学生、6-18 岁未成年人、60-70 周岁老人凭有效证件可购买半价票。最佳游览时长 2-3 小时。', distance: 0.287, doc_id: 'zhuozhengyuan_intro', tenant_id: 'public' },
          { content: '【北京_天安门广场】天安门广场位于北京 东城区 东长安街。景区等级：国家级。开放时间：周一至周日 05:00-22:00。门票信息：免费。类型：风景名胜；城市广场；红色景区；评分 4.9。', distance: 0.421, doc_id: 'corpus:beijing', tenant_id: 'public' },
          { content: '【北京_奥华餐厅老张记】奥华餐厅老张记(台基厂店)位于北京 北京城区台基厂大街18-3号。开放时间：周一至周日 10:30-21:30。类型：餐饮服务；中餐厅；评分 4.6。招牌菜：张记酱爆肘子、北京烤鸭套餐。', distance: 0.534, doc_id: 'corpus:beijing', tenant_id: 'public' },
          { content: '【北京_天安门】天安门位于北京 东城区 长安街北侧。景区等级：国家级景点。开放时间：周一至周日 05:00-20:15。门票信息：免费。', distance: 0.683, doc_id: 'corpus:beijing', tenant_id: 'public' },
        ],
        sub_questions: ['拙政园淡季门票价格？', '拙政园旺季门票价格？', '是否有优惠？', '预约方式？'],
      }
      return new Response(JSON.stringify(mock), { headers: { 'Content-Type': 'application/json' } })
    }
    if (url.includes('/api/rag/chat')) {
      // 模拟 SSE 流式
      const body = JSON.parse(init?.body || '{}')
      const q = body.message || ''
      const metaEvt = {
        type: 'meta',
        sources: [
          { content: '【苏发改服价〔2019〕14 号】文件规定：拙政园位于江苏 苏州 姑苏区东北街178号。景区等级：AAAAA。开放时间：07:30-17:30。门票信息：淡季70元/旺季90元。江南古典园林代表。', distance: 0.123, doc_id: '苏发改服价2019_14号' },
          { content: '【zhuozhengyuan_intro】拙政园位于江苏 苏州 姑苏区东北街178号。景区等级：AAAAA。开放时间：07:30-17:30。门票信息：淡季70元/旺季90元。半价优惠：在校学生、6-18 岁未成年人、60-70 周岁老人。', distance: 0.287, doc_id: 'zhuozhengyuan_intro' },
          { content: '【北京_天安门广场】天安门广场位于北京 东城区 东长安街。景区等级：国家级。开放时间：周一至周日 05:00-22:00。门票信息：免费。', distance: 0.421, doc_id: 'corpus:beijing' },
        ],
        sub_questions: [q + '（子问1）', q + '（子问2）'],
      }
      const tokens = '关于您的问题，依据检索资料答复：\n\n拙政园门票淡季 70 元，旺季 90 元 [1][2]。'.split('')
      const enc = new TextEncoder()
      const stream = new ReadableStream({
        start(ctrl) {
          ctrl.enqueue(enc.encode(`data: ${JSON.stringify(metaEvt)}\n\n`))
          ;(async () => {
            for (let i = 0; i < tokens.length; i++) {
              await new Promise(r => setTimeout(r, 25))
              ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type: 'token', text: tokens[i] })}\n\n`))
            }
            ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type: 'done', mode: 'llm', answer: '关于您的问题，依据检索资料答复：\\n\\n拙政园门票淡季 70 元，旺季 90 元 [1][2]。', sources: metaEvt.sources })}\n\n`))
            ctrl.close()
          })()
        }
      })
      return new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } })
    }

    // ====== Composer：从标品生成行程 ======
    if (url.includes('/api/composer/products')) {
      return new Response(JSON.stringify({
        total: 19,
        categories: ['景点', '餐饮', '住宿', '交通', '购物', '文化'],
        products: [
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
          { id: 'p_forbidden',      name: '故宫博物院', category: '景点', city: '北京', level: '5A', open: '08:30-16:00', ticket: '淡 40 / 旺 60', typical_dwell: '4h', best_slot: 'morning', coords: [116.397, 39.916], tags: ['博物馆', '世界遗产'], demand: 0.98 },
          { id: 'p_temple_heaven',  name: '天坛公园', category: '景点', city: '北京', level: '5A', open: '06:00-22:00', ticket: '联票 34', typical_dwell: '3h', best_slot: 'morning', coords: [116.411, 39.882], tags: ['古建'], demand: 0.8 },
          { id: 'p_summer_palace',  name: '颐和园', category: '景点', city: '北京', level: '5A', open: '06:30-18:00', ticket: '淡 30 / 旺 60', typical_dwell: '4h', best_slot: 'morning', coords: [116.275, 39.999], tags: ['园林'], demand: 0.86 },
          { id: 'p_nanluoguxiang',  name: '南锣鼓巷', category: '景点', city: '北京', level: '-', open: '全天', ticket: '免费', typical_dwell: '2h', best_slot: 'afternoon', coords: [116.403, 39.937], tags: ['胡同', '美食'], demand: 0.82 },
          { id: 'p_quanjude',       name: '全聚德(前门店)', category: '餐饮', city: '北京', level: '老字号', open: '11:00-21:00', ticket: '人均 180', typical_dwell: '1.5h', best_slot: 'midday', coords: [116.397, 39.898], tags: ['烤鸭'], demand: 0.92 },
          { id: 'p_hutong_r',       name: '胡同民宿(南锣店)', category: '住宿', city: '北京', level: '民宿', open: '全天', ticket: '¥ 680/晚', typical_dwell: '8h', best_slot: 'night', coords: [116.404, 39.937], tags: ['民宿'], demand: 0.65 },
        ],
      }), { headers: { 'Content-Type': 'application/json' } })
    }
    if (url.includes('/api/composer/from-products')) {
      const body = JSON.parse(init?.body || '{}')
      const ids = body.product_ids || []
      const itinerary = []
      const slots = ['morning', 'midday', 'afternoon', 'evening']
      for (let d = 1; d <= (body.days || 2); d++) {
        const day = { day: d, blocks: [] }
        for (let s = 0; s < 4 && (d - 1) * 4 + s < ids.length; s++) {
          const id = ids[(d - 1) * 4 + s]
          day.blocks.push({
            slot: slots[s],
            start: slots[s] === 'morning' ? '08:30' : slots[s] === 'midday' ? '11:30' : slots[s] === 'afternoon' ? '14:00' : '17:30',
            duration: ['2.5h', '1.5h', '2h', '1.5h'][s],
            product_id: id,
            title: id.replace('p_', '').replace(/_/g, ' '),
            type: ['景点', '景点', '景点', '餐饮'][s],
            note: '苏州 · 园林、世界遗产',
          })
        }
        itinerary.push(day)
      }
      return new Response(JSON.stringify({
        job_id: 'compose_' + Math.random().toString(36).slice(2, 10),
        itinerary,
        budget_estimate: { transport: 80, lodging: 880, food: 360, tickets: 200, total: 1520 },
        coverage_score: 0.95,
        missing_slots: 0,
        warnings: [],
      }), { headers: { 'Content-Type': 'application/json' } })
    }

    // ====== Swap：替换行程中标品 ======
    if (url.includes('/api/plans/') && url.includes('/swap-product') && !url.includes('inspect')) {
      return new Response(JSON.stringify({
        ok: true,
        job_id: 'plan_demo',
        day: 1,
        slot_index: 0,
        old_product_id: 'p_lion_woods',
        new_product_id: 'p_zhuozhengyuan',
        diff: { time_delta: '+1.0h', cost_delta: 50, distance_delta: '420 m', warnings: [] },
        warnings: [],
        swap_id: 'swap_' + Math.random().toString(36).slice(2, 8),
      }), { headers: { 'Content-Type': 'application/json' } })
    }

    // ====== Coverage：标品覆盖率 ======
    if (url.includes('/api/stats/product-coverage/trend')) {
      const trend = []
      for (let i = 0; i < 14; i++) {
        const d = new Date(); d.setDate(d.getDate() - (13 - i))
        trend.push({
          date: ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2),
          hit_rate: +(0.7 + Math.sin(i / 3) * 0.07 + Math.random() * 0.04).toFixed(3),
          refusal_rate: +(0.10 + Math.cos(i / 4) * 0.03 + Math.random() * 0.02).toFixed(3),
          empty_rate: +(0.08 + Math.sin(i / 5) * 0.03 + Math.random() * 0.02).toFixed(3),
        })
      }
      return new Response(JSON.stringify({ trend }), { headers: { 'Content-Type': 'application/json' } })
    }
    if (url.includes('/api/stats/product-coverage')) {
      return new Response(JSON.stringify({
        total_plans: 124,
        rag_hit_plans: 98,
        rag_miss_plans: 26,
        hit_rate: 0.79,
        refusal_rate: 0.12,
        empty_rate: 0.09,
        avg_distance: 0.342,
        coverage_by_category: { 景点: 0.92, 餐饮: 0.78, 住宿: 0.65, 交通: 0.83, 购物: 0.41, 文化: 0.56 },
        top_missing: [
          { name: '宠物友好酒店', count: 14 },
          { name: '无障碍设施', count: 11 },
          { name: '高铁站 24h 接送', count: 9 },
          { name: '凌晨航班住宿', count: 7 },
          { name: '小众文化体验', count: 6 },
        ],
      }), { headers: { 'Content-Type': 'application/json' } })
    }

    return originalFetch.apply(this, arguments)
  }
})

const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(`[${page.url()}] ${m.text()}`) })
page.on('pageerror', (e) => errors.push(`[pageerror] ${e.message}`))

for (const [name, url] of PAGES) {
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 })
  } catch { /* */ }
  await page.waitForTimeout(800)

  // 特定页面：先做交互再截图
  if (name === 'plan-rag') {
    // 点击 RAG tab
    const ragTab = await page.$('button.tab:has-text("AI 导游问答")')
    if (ragTab) await ragTab.click()
    await page.waitForTimeout(400)
    const ta = await page.$('.tab-body textarea')
    if (ta) {
      await ta.fill('苏州拙政园门票淡旺季分别是多少？老人有优惠吗？')
      const submit = await page.$('.tab-body button.btn-primary')
      if (submit) await submit.click()
      await page.waitForTimeout(2500) // 等流式完成
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
    // 再跑一次拒答问题，演示多种 mode
    const ta2 = await page.$('.rl-pane textarea')
    if (ta2) {
      await ta2.fill('火星上有哪些五星酒店？')
      const btn = await page.$('.rl-pane button.btn-primary')
      if (btn) await btn.click()
      await page.waitForTimeout(800)
    }
  }
  if (name === 'home-cat') {
    // 滚到分类导航 + 点景点类
    await page.evaluate(() => document.getElementById('ask-rag')?.scrollIntoView({ block: 'center' }))
    await page.waitForTimeout(400)
    const cat = await page.$('.cat-card:has-text("景点")')
    if (cat) {
      await cat.click()
      await page.waitForTimeout(1200)
    }
  }

  // Composer 行程组装器：选 4 个标品后生成
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
  // 替换行程 swap 弹窗演示
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
      // 确认替换
      const confirm = await page.$('.modal-foot .btn-primary')
      if (confirm) await confirm.click()
      await page.waitForTimeout(600)
    }
  }

  await page.waitForTimeout(800)
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true })
  console.log(`ok: ${name}`)
}

console.log(errors.length ? `CONSOLE ERRORS (${errors.length}):\n` + errors.slice(0, 20).join('\n') : 'NO CONSOLE ERRORS')
await browser.close()
