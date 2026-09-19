import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// dev 时代理 /api 到本地 FastAPI（生产由后端把 frontend/dist 同源挂载在 /）
export default defineConfig({
  base: '/',
  plugins: [vue()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1500,
  },
})
