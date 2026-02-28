import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const root = path.resolve(__dirname, '..')
  const env = loadEnv(mode, root, '')
  const backendPort = env.BACKEND_PORT || '18000'
  const frontendPort = env.FRONTEND_PORT || '3001'

  return {
    plugins: [react()],
    server: {
      port: parseInt(frontendPort, 10),
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  }
})
