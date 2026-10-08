import { defineConfig, devices } from '@playwright/test';

/**
 * Fumaça de ponta a ponta do frontend: o build de produção servido pelo
 * `vite preview`, com a API simulada em `tests/e2e/mockApi.ts`. Os fluxos com o
 * backend real (fila, worker, WebSocket) são testados no repositório do backend.
 */
const PORT = 4173;

export default defineConfig({
  testDir: './tests/e2e',
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? 'line' : 'list',
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'retain-on-failure',
    // Navegador já instalado na máquina (opcional).
    launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run build && npx vite preview --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
