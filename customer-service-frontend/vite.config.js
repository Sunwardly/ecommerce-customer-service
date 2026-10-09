import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端代理规则（开发服务器 server 和打包预览服务器 preview 共用同一份）
const proxy = {
  '/api': {
    target: 'http://127.0.0.1:18082',
    changeOrigin: true,
    xfwd: true,
  },
  '/ws': {
    target: 'ws://127.0.0.1:18082',
    changeOrigin: true,
    ws: true,
    xfwd: true,
  },
  '/commerce': {
    target: 'http://127.0.0.1:18082',
    changeOrigin: true,
    xfwd: true,
  },
  '/health': {
    target: 'http://127.0.0.1:18082',
    changeOrigin: true,
  },
}

// 允许通过哪些外部域名访问（内网穿透时必需，否则 Vite 6 会返回 403）
const allowedHosts = ['12lh9932zk192.vicp.fun']

export default defineConfig({
  plugins: [vue()],
  // 本地开发用：npm run dev
  server: {
    host: '0.0.0.0',
    port: 5174,
    allowedHosts,
    proxy,
  },
  // 对外演示用：npm run preview（先 npm run build）
  // 端口故意保持一致，这样花生壳的端口映射不用改
  preview: {
    host: '0.0.0.0',
    port: 5174,
    allowedHosts,
    proxy,
  },
})
