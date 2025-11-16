import { test, expect } from '@playwright/test';

test.describe('Media Upload Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Primeiro fazer login para acessar a funcionalidade de upload
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('should allow a user to upload a media file', async ({ page }) => {
    // Navegar para a página de upload
    await page.click('text=Upload');
    await expect(page).toHaveURL(/.*upload/);

    // Criar um arquivo temporário para upload (usando um pequeno arquivo de teste)
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

    // Alternativamente, se o elemento de upload for conhecido, podemos usar:
    // await page.locator('input[type="file"]').setFiles({
    //   name: fileName,
    //   mimeType: 'video/mp4',
    //   buffer: fileContent
    // });

    // Clicar no botão de upload
    await page.click('text=Upload Video');

    // Aguardar feedback de upload
    await expect(page.locator('text=Upload iniciado')).toBeVisible();

    // Verificar se o vídeo aparece na lista de mídias recentes
    await expect(page.locator(`text=${fileName}`)).toBeVisible();
  });

  test('should show error when trying to upload invalid file type', async ({ page }) => {
    // Navegar para a página de upload
    await page.goto('/upload');

    // Tentar fazer upload de um arquivo inválido
    const invalidFile = 'document.txt';
    const fileContent = Buffer.from('fake document content');
    
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('text=Select Video');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: invalidFile,
      mimeType: 'text/plain',
      buffer: fileContent
    });

    // Clicar no botão de upload
    await page.click('text=Upload Video');

    // Aguardar mensagem de erro
    await expect(page.locator('text=Tipo de arquivo não suportado')).toBeVisible();
  });
});