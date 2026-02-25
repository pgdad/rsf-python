import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../src/rsf/editor/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/ws': {
        target: 'ws://127.0.0.1:8765',
        ws: true,
      },
      '/api/inspect': {
        target: 'http://127.0.0.1:8766',
      },
      '/api': {
        target: 'http://127.0.0.1:8765',
      },
    },
  },
})
