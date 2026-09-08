// 全局轻量 toast（挂 window.__toast 由 AppToast 组件渲染）
const listeners = new Set()

export function toast(msg, type = 'info') {
  listeners.forEach((fn) => fn({ msg: String(msg), type, id: Date.now() + Math.random() }))
}

export function onToast(fn) { listeners.add(fn); return () => listeners.delete(fn) }
