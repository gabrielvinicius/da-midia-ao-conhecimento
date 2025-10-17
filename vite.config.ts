/// <reference types="vitest" />
import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
// import tailwindcss from "@tailwindcss/vite";
import autoprefixer from "autoprefixer";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(),autoprefixer()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
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
          vendor: ["react", "react-dom", "react-router-dom"],

          // UI libraries chunk
          ui: ["@tanstack/react-query", "@tanstack/react-table", "lucide-react"],

          // Feature chunks (code splitting by feature)
          auth: [
            "./src/features/authentication/components/LoginForm.tsx",
            "./src/features/authentication/components/RegisterForm.tsx",
            "./src/features/authentication/hooks/useAuthMutations.ts",
          ],

          admin: [
            "./src/features/admin/pages/AdminDashboardPage.tsx",
            "./src/features/admin/pages/AdminUsersPage.tsx",
            "./src/features/admin/pages/AdminAllMediaPage.tsx",
          ],

          media: [
            "./src/features/media/components/MediaCard.tsx",
            "./src/features/media/components/MediaPlayer.tsx",
            "./src/features/media/components/UploadForm.tsx",
          ],

          analysis: [
            "./src/features/sentiment_analysis/components/SentimentResultPanel.tsx",
            "./src/features/topic_modeling/components/TopicModelingResultPanel.tsx",
          ],
        },
      },
    },
    // Performance optimizations
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.logs in production
        drop_debugger: true,
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  // Dev optimizations
  server: {
    hmr: {
      overlay: false, // Disable overlay for better performance
    },
  },
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "@tanstack/react-query",
      "axios",
      "lucide-react",
    ],
  },
});
