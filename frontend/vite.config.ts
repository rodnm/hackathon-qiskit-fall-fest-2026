import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, el proxy /api -> localhost:8000 (en producción lo hace Nginx: S4)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
