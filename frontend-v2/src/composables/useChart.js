import { ref, onMounted, onUnmounted, shallowRef } from 'vue'
import * as echarts from 'echarts'

/**
 * ECharts 封装：自动 init / resize / dispose
 * option 为 ref 或 getter
 */
export function useChart(elRef, optionGetter, theme) {
  const chart = shallowRef(null)
  let ro = null

  function render() {
    if (!elRef.value) return
    if (!chart.value) {
      chart.value = echarts.init(elRef.value, theme)
      ro = new ResizeObserver(() => chart.value?.resize())
      ro.observe(elRef.value)
    }
    chart.value.setOption(optionGetter())
  }

  onMounted(render)
  onUnmounted(() => {
    ro?.disconnect()
    chart.value?.dispose()
  })

  return { chart, render }
}
