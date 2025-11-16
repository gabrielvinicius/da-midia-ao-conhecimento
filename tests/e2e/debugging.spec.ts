import { test, expect } from '@playwright/test';

test.describe('Debugging and Visual Validation Tests', () => {
  test('should capture screenshots for debugging', async ({ page }) => {
    // Navegar para a página de login
    await page.goto('/login');
    
    // Tirar screenshot da página de login
    await page.screenshot({ path: 'tests/e2e/screenshots/login-page.png', fullPage: true });
    
    // Preencher o formulário de login
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    
    // Tirar screenshot antes de submeter
    await page.screenshot({ path: 'tests/e2e/screenshots/login-filled.png' });
    
    // Submeter o formulário
    await page.click('button[type="submit"]');
    
    // Tirar screenshot da página de dashboard após login
    await page.waitForURL('**/dashboard');
    await page.screenshot({ path: 'tests/e2e/screenshots/dashboard.png', fullPage: true });
  });

  test('should validate page elements using snapshot', async ({ page }) => {
    // Navegar para a página de login
    await page.goto('/login');
    
    // Verificar se os elementos essenciais estão presentes
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.locator('text=Login')).toBeVisible();
    
    // Verificar o snapshot da página de login
    await expect(page).toHaveScreenshot('login-page.png', { 
      maxDiffPixels: 50,
      timeout: 5000 
    });
  });

  test('should check console errors during navigation', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', message => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text());
      }
    });

    // Navegar por diferentes páginas
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Aguardar redirecionamento para dashboard
    await page.waitForURL('**/dashboard');
    
    // Navegar para upload
    await page.click('text=Upload');
    await page.waitForURL('**/upload');
    
    // Verificar se houve erros no console
    expect(consoleErrors).toEqual([]);
  });

  test('should validate network requests', async ({ page }) => {
    // Habilitar rastreamento de requisições de rede
    const requests = [];
    page.on('request', request => {
      requests.push({
        url: request.url(),
        method: request.method(),
      });
    });

    // Navegar para a página de login
    await page.goto('/login');
    
    // Preencher e submeter formulário de login
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Aguardar redirecionamento
    await page.waitForURL('**/dashboard');
    
    // Verificar se as requisições esperadas foram feitas
    const hasLoginRequest = requests.some(req => req.url.includes('/auth/login') && req.method === 'POST');
    const hasDashboardRequest = requests.some(req => req.url.includes('/dashboard') && req.method === 'GET');
    
    expect(hasLoginRequest).toBeTruthy();
    expect(hasDashboardRequest).toBeTruthy();
  });

  test('should validate responsive design elements', async ({ page }) => {
    // Testar em diferentes tamanhos de tela
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto('/dashboard');
    
    // Verificar elementos em tela desktop
    await expect(page.locator('nav')).toBeVisible();
    await expect(page.locator('[data-testid="sidebar"]')).toBeVisible();
    
    // Mudar para tamanho de tela mobile
    await page.setViewportSize({ width: 375, height: 812 });
    await page.reload();
    
    // Verificar elementos em tela mobile
    const mobileMenuButton = page.locator('[data-testid="mobile-menu-toggle"]');
    if (await mobileMenuButton.count() > 0) {
      await expect(mobileMenuButton).toBeVisible();
    }
  });
});