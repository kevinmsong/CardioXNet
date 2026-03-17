import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('loads and shows gene input panel', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/CardioXNet/i);
    // Gene input textarea or field should be visible
    const geneInput = page.locator('textarea, input[placeholder*="gene"], input[placeholder*="Gene"]').first();
    await expect(geneInput).toBeVisible({ timeout: 10000 });
  });

  test('navigation links are present', async ({ page }) => {
    await page.goto('/');
    // Nav uses MUI Buttons, not <a> elements
    await expect(page.getByRole('button', { name: /documentation/i }).first()).toBeVisible();
  });

  test('shows configuration panel toggle', async ({ page }) => {
    await page.goto('/');
    // Configuration accordion should be visible
    const configPanel = page.locator('text=Advanced Configuration');
    await expect(configPanel).toBeVisible({ timeout: 10000 });
  });

  test('configuration panel expands and shows core settings', async ({ page }) => {
    await page.goto('/');
    // Click to expand the configuration panel
    await page.locator('text=Advanced Configuration').click();
    // Should show core settings (use first() to handle label+span duplicates in MUI)
    await expect(page.locator('text=STRING Neighbor Count').first()).toBeVisible();
    await expect(page.locator('text=FDR Threshold').first()).toBeVisible();
    // Database weights section should NOT be present (removed in MVP)
    await expect(page.locator('text=Database Quality Weights')).not.toBeVisible();
  });
});
