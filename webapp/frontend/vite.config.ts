import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/puzzles': 'http://localhost:8000',
      '/simulate': 'http://localhost:8000'
    }
  }
})