import { test, expect } from '@playwright/test';

test('homepage loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/CardioXNet/i);
});

test('documentation page loads', async ({ page }) => {
  await page.goto('/documentation');
  await expect(page.locator('h1, h2, h3, h4, h5, h6').first()).toBeVisible();
});
