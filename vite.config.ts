import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src/frontend')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
        // No rewrite - keep /api prefix
      },
      '/speech': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      '/llm': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
