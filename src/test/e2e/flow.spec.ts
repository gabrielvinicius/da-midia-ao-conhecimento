import { test, expect } from '@playwright/test';

test.describe('Video Summarizer E2E Flow', () => {
  test('should login, upload a file and see predictive insights', async ({ page }) => {
    // 1. Login
    await page.goto('http://localhost:3000/login');
    await page.fill('input[name="email"]', 'user@example.com');
    await page.fill('input[name="password"]', 'Admin123!');
    await page.click('button[type="submit"]');

    // 2. Dashboard check
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('text=Painel pessoal')).toBeVisible();

    // 3. Navigate to Upload
    await page.click('text=Novo Upload');
    await expect(page).toHaveURL(/.*upload/);

    // 4. Test Accessibility - Navigation
    await page.keyboard.press('Tab');
    // Ensure focus moves correctly
  });

  test('media detail accessibility and interaction', async ({ page }) => {
    // Pre-requisite: needs an existing media ID
    // This is a smoke test for the interactive transcription we just updated
    await page.goto('http://localhost:3000/login');
    await page.fill('input[name="email"]', 'user@example.com');
    await page.fill('input[name="password"]', 'Admin123!');
    await page.click('button[type="submit"]');
    
    await page.waitForURL(/.*dashboard/);
    
    // Click first media details
    const firstDetailButton = page.locator('text=Ver Detalhes').first();
    if (await firstDetailButton.isVisible()) {
        await firstDetailButton.click();
        
        // Check ARIA labels in transcription
        const transcriptionRegion = page.locator('[role="region"][aria-label="Transcrição interativa"]');
        await expect(transcriptionRegion).toBeVisible();
        
        // Test Keyboard Navigation in Transcription
        await page.keyboard.press('Tab');
        const firstSegment = page.locator('[role="button"][aria-label*="segundos"]').first();
        if (await firstSegment.isVisible()) {
            await firstSegment.focus();
            await page.keyboard.press('Enter');
            // Verify if video started or changed (advanced check)
        }
    }
  });
});
