import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发时代理到本地 FastAPI 后端
export default defineConfig({
  base: '/v2/',
  plugins: [vue()],
  server: {
    port: 5273,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    chunkSizeWarningLimit: 1500,
  },
})
