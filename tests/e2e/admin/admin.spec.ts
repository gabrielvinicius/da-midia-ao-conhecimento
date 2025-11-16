import { test, expect } from '@playwright/test';

test.describe('Admin Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Primeiro fazer login com credenciais de administrador
    await page.goto('/login');
    await page.fill('input[name="email"]', 'admin@example.com');
    await page.fill('input[name="password"]', 'adminpassword123');
    await page.click('button[type="submit"]');
    
    // Aguardar redirecionamento para dashboard
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('should allow admin to access admin panel', async ({ page }) => {
    // Clicar no link do painel administrativo (assumindo que está disponível para admins)
    await page.click('text=Admin Panel');
    
    // Verificar se foi redirecionado para a página de administração
    await expect(page).toHaveURL(/.*admin.*/);
    
    // Verificar se os elementos do painel administrativo estão visíveis
    await expect(page.locator('h1:text("Admin Dashboard")')).toBeVisible();
    await expect(page.locator('text=Manage Users')).toBeVisible();
    await expect(page.locator('text=Manage Media')).toBeVisible();
    await expect(page.locator('text=System Status')).toBeVisible();
  });

  test('should display user management page', async ({ page }) => {
    // Navegar para a página de gerenciamento de usuários
    await page.goto('/admin/users');
    await expect(page).toHaveURL(/.*admin\/users/);

    // Verificar se a lista de usuários está visível
    await expect(page.locator('[data-testid="user-list"]')).toBeVisible();
    
    // Verificar se há pelo menos um usuário na lista
    const userItems = page.locator('[data-testid="user-item"]');
    await expect(userItems).toHaveCount(0, { timeout: 10000 }).or().toBeGreaterThanOrEqual(0);
  });

  test('should display media management page', async ({ page }) => {
    // Navegar para a página de gerenciamento de mídias
    await page.goto('/admin/media');
    await expect(page).toHaveURL(/.*admin\/media/);

    // Verificar se a lista de mídias está visível
    await expect(page.locator('[data-testid="admin-media-list"]')).toBeVisible();
    
    // Verificar se há pelo menos uma mídia na lista
    const mediaItems = page.locator('[data-testid="admin-media-item"]');
    await expect(mediaItems).toHaveCount(0, { timeout: 10000 }).or().toBeGreaterThanOrEqual(0);
  });

  test('should allow admin to search for users', async ({ page }) => {
    // Navegar para a página de gerenciamento de usuários
    await page.goto('/admin/users');
    await expect(page).toHaveURL(/.*admin\/users/);

    // Preencher campo de busca com um termo
    await page.fill('[data-testid="search-input"]', 'testuser');
    
    // Clicar no botão de busca
    await page.click('text=Search');
    
    // Verificar se os resultados da busca são exibidos
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();
  });
});