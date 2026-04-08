import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  // Vitest 配置
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['tests/**/*.{test,spec}.{js,ts}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.{js,ts}',
        '**/dist/**'
      ]
    }
  },
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyDirBeforeWrite: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // 合并所有 index- 开头的 chunk 到一个文件中
          'index': ['./src/views/system/index.vue', './src/api/keyRotation.js']
        }
      }
    }
  },
  base: '/'
})
