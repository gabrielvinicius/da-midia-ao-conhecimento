import { expect, test } from '@playwright/test';

import { mockApi, USER } from './mockApi';

test('visitante vê o login sem aviso de sessão expirada', async ({ page }) => {
  const calls = await mockApi(page);
  await page.goto('/dashboard');

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText('Entrar').first()).toBeVisible();
  await expect(page.getByText('Sessão expirada')).toHaveCount(0);
  expect(calls).not.toContain('GET /auth/me');
});

test('login leva ao painel com as contagens da API', async ({ page }) => {
  await mockApi(page);
  await page.goto('/login');

  await page.getByLabel('Email').fill(USER.email);
  await page.getByLabel('Senha').fill('segredo123');
  await page.getByRole('button', { name: 'Entrar' }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole('heading', { name: `Bem-vindo de volta, ${USER.email}` })).toBeVisible();
});

test('aba nova recupera a sessão pelo cookie; endereço inexistente mostra 404', async ({ page }) => {
  const calls = await mockApi(page, { loggedIn: true });
  await page.goto('/nao-existe');

  await expect(page.getByText('Página não encontrada')).toBeVisible();
  expect(calls.filter((c) => c === 'POST /auth/refresh')).toHaveLength(1);
});
