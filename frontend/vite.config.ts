/// <reference types="vitest/config" />
import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    // tests/e2e é do Playwright (precisa do sistema rodando): npm run test:e2e
    exclude: ["**/node_modules/**", "**/dist/**", "tests/e2e/**"],
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    // Só as bibliotecas que mudam pouco ficam em pedaços fixos (o navegador
    // os guarda entre versões); as telas ficam com a divisão automática pelos
    // imports dinâmicos. Medido com a API simulada, o JavaScript baixado caiu
    // em todas as telas (login de 704 para 267 kB) em relação aos grupos por
    // funcionalidade que havia antes.
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: "vendor", test: /node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/ },
            { name: "ui", test: /node_modules[\\/](@tanstack[\\/]react-(query|table)|lucide-react)[\\/]/ },
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
