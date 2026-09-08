import { ref, onUnmounted } from 'vue'

/**
 * 任务状态轮询：QUEUED/RUNNING/WAITING_* 期间每 intervalMs 轮询一次，
 * 进入终态（COMPLETED/FAILED/...）自动停止并触发回调
 */
export function useJobPolling(fetchFn, intervalMs = 2000) {
  const data = ref(null)
  const polling = ref(false)
  const error = ref('')
  let timer = null

  const TERMINAL = ['COMPLETED', 'FAILED', 'CORRUPTED', 'RECOVERY_REQUIRED', 'REPLAN_REQUIRED']

  function stop() {
    polling.value = false
    if (timer) { clearInterval(timer); timer = null }
  }

  async function tick(onTerminal) {
    try {
      data.value = await fetchFn()
      error.value = ''
      if (TERMINAL.includes(data.value?.status)) {
        stop()
        onTerminal && onTerminal(data.value)
      }
    } catch (e) {
      error.value = e.message
    }
  }

  function start(onTerminal, immediate = true) {
    stop()
    polling.value = true
    if (immediate) tick(onTerminal)
    timer = setInterval(() => tick(onTerminal), intervalMs)
  }

  onUnmounted(stop)
  return { data, polling, error, start, stop }
}
