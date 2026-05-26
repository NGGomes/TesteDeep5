import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  publicDir: 'public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/events': 'http://localhost:5000',
      '/health': 'http://localhost:5000',
      '/config': 'http://localhost:5000',
    },
  },
})
