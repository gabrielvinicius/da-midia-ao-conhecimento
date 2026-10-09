/// <reference types="vitest" />
import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    // tests/e2e é do Playwright (precisa do sistema rodando): npm run test:e2e
    exclude: ["**/node_modules/**", "**/dist/**", "tests/e2e/**"],
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
          vendor: ["react", "react-dom", "react-router-dom"],
          ui: ["@tanstack/react-query", "@tanstack/react-table", "lucide-react"],
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
            "./src/features/media/components/MediaRow.tsx",
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
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  server: {
    hmr: {
      overlay: false,
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
