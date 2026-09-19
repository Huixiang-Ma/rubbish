# -*- coding: utf-8 -*-
"""第二批死按钮修复 v2（按实际 markup 修正）（跑完即删）"""
import io, re

def patch(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for old, new, tag in pairs:
        assert old in s, f'{path} NOT FOUND: {tag}'
        s = s.replace(old, new, 1)
    io.open(path, 'w', encoding='utf-8').write(s)
    print('patched', path)

# 1. AuditView 导出 CSV（btn-primary）
patch('views/tob/AuditView.vue', [
    ("""<button class="btn btn-primary btn-sm"><TobIcon name="download" :size="14" />导出全量审计 CSV</button>""",
     """<button class="btn btn-primary btn-sm" @click="exportCsv"><TobIcon name="download" :size="14" />导出全量审计 CSV</button>""", 'export csv'),
], )

# 2. KnowledgeView 下载导入模板
patch('views/tob/KnowledgeView.vue', [
    ("""          <button type="button" class="btn btn-text"
                  @click.stop>""",
     """          <button type="button" class="btn btn-text"
                  @click.stop="downloadTemplate">""", 'template btn'),
    ("""function onDragOver(e) { e.preventDefault(); dragOver.value = true }""",
     """function onDragOver(e) { e.preventDefault(); dragOver.value = true }

/* 下载导入模板：示例 Markdown，含分段规范 */
function downloadTemplate() {
  const md = ['# 知识库导入模板', '', '第一段：景点介绍、门票价格、开放时间等事实信息（空行分段，每段会被独立分块）。', '', '第二段：预约方式、注意事项、常见问题解答。', '', '第三段：推荐动线、游玩建议、雨天备选方案。', '', '> 提示：保存为 .md / .txt 后通过上方上传区批量导入。'].join('\\n\\n')
  const blob = new Blob([md], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = '知识库导入模板.md'
  a.click()
  URL.revokeObjectURL(a.href)
}""", 'downloadTemplate fn'),
], )

# 3. ProductDetailView 分享按钮
patch('views/toc/ProductDetailView.vue', [
    ("""            <button class="pb-sub">↗ 分享</button>""",
     """            <button class="pb-sub" @click="shareLink">↗ {{ shareTip || '分享' }}</button>""", 'share btn'),
    ("""function order() {""",
     """/* 分享：复制方案链接 */
function shareLink() {
  const url = `${location.origin}${location.pathname}#/malls/product/${plan.value.id}`
  navigator.clipboard?.writeText(url).then(() => {}, () => {})
  shareTip.value = '链接已复制'
  setTimeout(() => { shareTip.value = '' }, 2000)
}

function order() {""", 'share fn'),
    ("""const liked = ref(false)
const step = ref(1)   // 三步流程高亮""",
     """const liked = ref(false)
const shareTip = ref('')
const step = ref(1)   // 三步流程高亮""", 'shareTip ref'),
], )

# 4. MyOrdersView 收银台支付方式可选 + 订单分享
patch('views/toc/MyOrdersView.vue', [
    ("""const paying = ref(null)
const payBusy = ref(false)""",
     """const paying = ref(null)
const payBusy = ref(false)
const payMethod = ref('wechat')""", 'payMethod ref'),
    ("""          <button class="on"><span class="pm-ico">💚</span>微信支付</button>
          <button><span class="pm-ico">🔷</span>支付宝</button>""",
     """          <button :class="{ on: payMethod === 'wechat' }" @click="payMethod = 'wechat'"><span class="pm-ico">💚</span>微信支付</button>
          <button :class="{ on: payMethod === 'alipay' }" @click="payMethod = 'alipay'"><span class="pm-ico">🔷</span>支付宝</button>""", 'pay methods'),
    ("""    await ordersApi.pay(paying.value.id, { method: 'wechat' })""",
     """    await ordersApi.pay(paying.value.id, { method: payMethod.value === 'alipay' ? '支付宝' : '微信支付' })""", 'pay pass'),
    ("""<button class="btn btn-ghost btn-sm">↗ 分享</button>""",
     """<button class="btn btn-ghost btn-sm" @click="shareOrder(o)">↗ 分享</button>""", 'share order'),
    ("""/* 补付/支付：POST /api/orders/{id}/pay */""",
     """/* 订单分享：复制订单页链接 */
function shareOrder(o) {
  const url = `${location.origin}${location.pathname}#/orders`
  navigator.clipboard?.writeText(`我的订单 ${o.no}：${url}`).then(() => {}, () => {})
}

/* 补付/支付：POST /api/orders/{id}/pay */""", 'shareOrder fn'),
], )

# 5. ServicesView：各 tab 预订按钮埋点（flight/hotel/ticket/merchant/show）
patch('views/toc/ServicesView.vue', [
    ("""              <td><button class="btn btn-ghost btn-sm">预订</button></td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 住宿 -->""",
     """              <td><button class="btn btn-ghost btn-sm" @click="booking('flight')">预订</button></td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- 住宿 -->""", 'flight'),
    ("""            <button class="btn btn-primary btn-sm">预订</button>
          </div>
        </div>
      </section>

      <!-- 门票 -->""",
     """            <button class="btn btn-primary btn-sm" @click="booking('hotel')">预订</button>
          </div>
        </div>
      </section>

      <!-- 门票 -->""", 'hotel'),
    ("""          <button class="btn btn-primary btn-sm t-btn">购买门票</button>""",
     """          <button class="btn btn-primary btn-sm t-btn" @click="booking('attraction')">购买门票</button>""", 'ticket'),
    ("""            <button class="btn btn-ghost btn-sm">预订餐位</button>""",
     """            <button class="btn btn-ghost btn-sm" @click="booking('merchant')">预订餐位</button>""", 'merchant'),
    ("""            <button class="btn btn-ghost btn-sm">预订演出</button>""",
     """            <button class="btn btn-ghost btn-sm" @click="booking('entertainment')">预订演出</button>""", 'show'),
], )

# 6. RagLabView 导出调用日志
patch('views/tob/RagLabView.vue', [
    ("""        <button class="btn btn-ghost btn-sm"><TobIcon name="download" :size="14" />导出调用日志</button>""",
     """        <button class="btn btn-ghost btn-sm" @click="exportLog"><TobIcon name="download" :size="14" />导出调用日志</button>""", 'export log'),
    ("""function distColor(d) {""",
     """/* 导出调用日志：history/chunks → JSON 下载 */
function exportLog() {
  const blob = new Blob([JSON.stringify({ history: history.value, chunks: chunks.value }, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `rag-log-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

function distColor(d) {""", 'exportLog fn'),
], )

# 7. ContentOpsView 导出排期表
s = io.open('views/tob/ContentOpsView.vue', encoding='utf-8').read()
if '@click="exportSchedule"' not in s:
    s = re.sub(r'(<button[^>]*?)>(\s*)导出排期表', r"\1 @click=\"exportSchedule\">\2导出排期表", s, count=1)
if 'function exportSchedule' not in s:
    s = s.replace("""const statusMeta = {""", """/* 导出排期表：当前频道内容 → JSON 下载 */
function exportSchedule() {
  const blob = new Blob([JSON.stringify({ channel: channel.value, items: rows.value }, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `content-${channel.value}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

const statusMeta = {""", 1)
io.open('views/tob/ContentOpsView.vue', 'w', encoding='utf-8').write(s)
print('ContentOps ok')

# 8. NearbyOpsView：登记 POI / 同步开放平台 → 提示（演示页）
s = io.open('views/tob/NearbyOpsView.vue', encoding='utf-8').read()
if 'demoTip' not in s:
    s = re.sub(r'(<button[^>]*?)>(\s*)(登记 POI|同步开放平台)', lambda m: m.group(1) + ' @click="demoTip(\'' + m.group(3) + '\')">' + m.group(2) + m.group(3), s, count=2)
    s = s.replace("""/* ============ POI 库 ============ */""", """/* 演示占位：开放平台对接未开放 */
function demoTip(label) {
  window.alert(label + '：开放平台对接为规划中能力,当前演示环境未开放')
}

/* ============ POI 库 ============ */""", 1)
io.open('views/tob/NearbyOpsView.vue', 'w', encoding='utf-8').write(s)
print('NearbyOps ok')

# 9. PlanDetailView：名导团兜底 id 对话本地模拟
patch('views/toc/PlanDetailView.vue', [
    ("""/* —— 名导团（GET /plans/{id}/guides + POST dialogue） —— */
const GUIDES_LIST = ref(GUIDES)""",
     """/* —— 名导团（GET /plans/{id}/guides + POST dialogue） ——
 * guidesSource: real=后端角色（dialogue 可用）；fallback=内置演示角色（本地模拟回复）
 */
const GUIDES_LIST = ref(GUIDES)
const guidesSource = ref('fallback')""", 'guidesSource'),
    ("""      GUIDES_LIST.value = rows.map((g, i) => ({""",
     """      guidesSource.value = 'real'
      GUIDES_LIST.value = rows.map((g, i) => ({""", 'guidesSource set'),
], )

s = io.open('views/toc/PlanDetailView.vue', encoding='utf-8').read()
old = """  thinking.value = true
  try {
    const res = await expApi.dialogue(jobId.value, {"""
new = """  thinking.value = true
  // 演示名导（后端无此角色）：本地模拟回复,避免"未找到该角色"
  if (guidesSource.value !== 'real') {
    setTimeout(() => {
      thinking.value = false
      chat.value.push({ role: 'guide', text: `（演示模式）关于「${message.slice(0, 16)}」——这条线的取舍我认可,细节可以继续问我。` })
    }, 900)
    draft.value = ''
    return
  }
  try {
    const res = await expApi.dialogue(jobId.value, {"""
assert old in s, 'dialogue block not found'
s = s.replace(old, new, 1)
io.open('views/toc/PlanDetailView.vue', 'w', encoding='utf-8').write(s)
print('PlanDetail guides ok')

print('batch2 v2 ALL DONE')
