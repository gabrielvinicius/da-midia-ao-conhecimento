/// <reference types="vitest" />
import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Core vendor chunk
          vendor: ['react', 'react-dom', 'react-router-dom'],
          
          // UI libraries chunk
          ui: ['@tanstack/react-query', '@tanstack/react-table', 'lucide-react'],
          
          // Feature chunks (code splitting por feature)
          auth: [
            './src/features/authentication/components/LoginForm.tsx',
            './src/features/authentication/components/RegisterForm.tsx',
            './src/features/authentication/hooks/useAuthMutations.ts'
          ],
          
          admin: [
            './src/features/admin/pages/AdminDashboardPage.tsx',
            './src/features/admin/pages/AdminUsersPage.tsx',
            './src/features/admin/pages/AdminAllMediaPage.tsx'
          ],
          
          media: [
            './src/features/media/components/MediaCard.tsx',
            './src/features/media/components/MediaPlayer.tsx',
            './src/features/media/components/UploadForm.tsx'
          ],
          
          analysis: [
            './src/features/sentiment_analysis/components/SentimentResultPanel.tsx',
            './src/features/topic_modeling/components/TopicModelingResultPanel.tsx'
          ]
        }
      }
    },
    // Otimizações de performance
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remover console.logs em produção
        drop_debugger: true,
      },
    },
    // Configurar tamanho de chunk
    chunkSizeWarningLimit: 1000,
  },
  // Otimizações para desenvolvimento
  server: {
    hmr: {
      overlay: false, // Desabilitar overlay de erro para melhor performance
    },
  },
  // Pre-bundling otimizado
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      'axios',
      'lucide-react'
    ],
  },
})
