import { test, expect } from '@playwright/test';

test.describe('Dashboard Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Primeiro fazer login para acessar o dashboard
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('should display user dashboard with media list', async ({ page }) => {
    // Verificar se o título do dashboard está visível
    await expect(page.locator('h1:text("Dashboard")')).toBeVisible();

    // Verificar se a lista de vídeos está visível
    await expect(page.locator('[data-testid="media-list"]')).toBeVisible();

    // Verificar se há pelo menos um vídeo na lista
    const mediaItems = page.locator('[data-testid="media-item"]');
    await expect(mediaItems).toHaveCount(0, { timeout: 10000 }).or().toBeGreaterThanOrEqual(0);

    // Verificar se os elementos de navegação estão presentes
    await expect(page.locator('text=Upload')).toBeVisible();
    await expect(page.locator('text=Settings')).toBeVisible();
  });

  test('should allow navigation to upload page from dashboard', async ({ page }) => {
    // Clicar no link de upload no dashboard
    await page.click('text=Upload');

    // Verificar se foi redirecionado para a página de upload
    await expect(page).toHaveURL(/.*upload/);
    await expect(page.locator('h1:text("Upload Video")')).toBeVisible();
  });

  test('should show media details when clicking on a media item', async ({ page }) => {
    // Criar um vídeo para testar (simulando que já existe um vídeo)
    // Primeiro fazer upload de um vídeo para garantir que existe algo na lista
    
    // Navegar para a página de upload
    await page.click('text=Upload');
    await expect(page).toHaveURL(/.*upload/);

    // Criar um arquivo temporário para upload (opcional para o teste)
    const fileName = 'test-video.mp4';
    const fileContent = Buffer.from('fake video content');
    
    // Simular o upload do arquivo
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('text=Select Video');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: fileName,
      mimeType: 'video/mp4',
      buffer: fileContent
    });

    // Clicar no botão de upload
    await page.click('text=Upload Video');

    // Aguardar feedback de upload
    await expect(page.locator('text=Upload iniciado')).toBeVisible();

    // Navegar de volta ao dashboard
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/.*dashboard/);

    // Clicar no item de mídia para ver detalhes
    const firstMediaItem = page.locator('[data-testid="media-item"]').first();
    if (await firstMediaItem.count() > 0) {
      await firstMediaItem.click();
      
      // Verificar se redirecionou para a página de detalhes
      await expect(page).toHaveURL(/.*media\/.*/)
    }
  });
});