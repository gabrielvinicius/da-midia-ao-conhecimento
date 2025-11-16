import { test, expect } from '@playwright/test';

test.describe('Media Details Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Primeiro fazer login para acessar os detalhes da mídia
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Aguardar redirecionamento para dashboard
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('should display media details page', async ({ page }) => {
    // Simular que há um vídeo na lista e clicar nele
    // Primeiro criar/upload um vídeo para garantir existência
    await page.click('text=Upload');
    await expect(page).toHaveURL(/.*upload/);

    // Simular upload de um vídeo
    const fileName = 'test-video.mp4';
    const fileContent = Buffer.from('fake video content');
    
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
    await expect(page.locator('text=Upload iniciado')).toBeVisible();

    // Voltar para o dashboard
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/.*dashboard/);

    // Clicar no primeiro item de mídia para ver detalhes
    const firstMediaItem = page.locator('[data-testid="media-item"]').first();
    if (await firstMediaItem.count() > 0) {
      await firstMediaItem.click();
      
      // Aguardar carregamento da página de detalhes
      await expect(page).toHaveURL(/.*media\/.*/);
      
      // Verificar se os detalhes do vídeo estão visíveis
      await expect(page.locator('[data-testid="media-title"]')).toBeVisible();
      await expect(page.locator('[data-testid="media-transcription"]')).toBeVisible();
      await expect(page.locator('[data-testid="media-summary"]')).toBeVisible();
    }
  });

  test('should show processing status while media is being processed', async ({ page }) => {
    // Navegar diretamente para uma página de detalhes de mídia (simulando uma existente)
    // Este teste assume que há um vídeo com status de processamento
    
    // Navegar para o dashboard e selecionar um vídeo com status de processamento
    await page.click('text=Upload');
    await expect(page).toHaveURL(/.*upload/);

    // Simular upload de um vídeo
    const fileName = 'processing-video.mp4';
    const fileContent = Buffer.from('fake video content for processing');
    
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
    await expect(page.locator('text=Upload iniciado')).toBeVisible();

    // Voltar para o dashboard
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/.*dashboard/);

    // Clicar no item de mídia recém-criado
    const mediaItem = page.locator(`text=${fileName}`).first();
    if (await mediaItem.count() > 0) {
      await mediaItem.click();
      
      // Verificar se o status de processamento está visível
      await expect(page.locator('text=Processando')).toBeVisible();
      
      // Aguardar até que o processamento seja concluído (ou até o timeout)
      await expect(page.locator('text=Concluído').or(page.locator('text=Erro'))).toBeVisible({ timeout: 60000 });
    }
  });

  test('should allow downloading media summary', async ({ page }) => {
    // Teste assume que há um vídeo processado disponível
    // Primeiro garantir que temos um vídeo processado
    
    // Navegar para o dashboard
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/.*dashboard/);

    // Clicar no primeiro item de mídia (assumindo que está processado)
    const firstMediaItem = page.locator('[data-testid="media-item"]').first();
    if (await firstMediaItem.count() > 0) {
      await firstMediaItem.click();
      
      // Aguardar carregamento da página de detalhes
      await expect(page).toHaveURL(/.*media\/.*/);
      
      // Clicar no botão de download do resumo
      const downloadPromise = page.waitForEvent('download');
      await page.click('text=Download Summary');
      const download = await downloadPromise;
      
      // Verificar se o download foi iniciado
      expect(download.suggestedFilename()).toContain('summary');
    }
  });
});