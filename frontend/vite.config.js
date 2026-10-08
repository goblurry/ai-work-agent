import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 배포 경로가 /<repo>/ 형태면 base 를 맞춰 준다.
export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE || '/',
  server: { port: 5173 },
})
