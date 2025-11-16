import { test, expect } from '@playwright/test';

test.describe('Authentication Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navegar para a página de login antes de cada teste
    await page.goto('/login');
  });

  test('should allow a user to log in with valid credentials', async ({ page }) => {
    // Preencher o formulário de login com credenciais válidas
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');

    // Clicar no botão de login
    await page.click('button[type="submit"]');

    // Aguardar redirecionamento para o dashboard
    await expect(page).toHaveURL(/.*dashboard/);
    
    // Verificar se o usuário está autenticado (verificando se o botão de logout está visível)
    await expect(page.locator('text=Logout')).toBeVisible();
  });

  test('should show error message with invalid credentials', async ({ page }) => {
    // Preencher o formulário de login com credenciais inválidas
    await page.fill('input[name="email"]', 'invalid@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');

    // Clicar no botão de login
    await page.click('button[type="submit"]');

    // Aguardar mensagem de erro
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });

  test('should allow a user to log out', async ({ page }) => {
    // Primeiro fazer login com credenciais válidas
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // Clicar no botão de logout
    await page.click('text=Logout');

    // Aguardar redirecionamento para a página de login
    await expect(page).toHaveURL(/.*login/);
    
    // Verificar se o usuário está deslogado (verificando se o botão de login está visível)
    await expect(page.locator('text=Login')).toBeVisible();
  });
});