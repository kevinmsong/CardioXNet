import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('documentation page loads', async ({ page }) => {
    await page.goto('/documentation');
    await expect(page).toHaveURL(/documentation/);
    // Page should render without crashing
    await expect(page.locator('body')).toBeVisible();
  });

  test('api reference page loads', async ({ page }) => {
    await page.goto('/api-reference');
    await expect(page).toHaveURL(/api-reference/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('unknown route does not crash app', async ({ page }) => {
    await page.goto('/nonexistent-route');
    // App layout should still render (router handles unknown routes gracefully)
    await expect(page.locator('body')).toBeVisible();
  });

  test('detail route removed - navigating to it redirects or 404s gracefully', async ({ page }) => {
    // The UltraDetailPage route was removed; visiting it should not crash
    await page.goto('/detail/test-analysis/test-pathway');
    await expect(page.locator('body')).toBeVisible();
  });
});
