import { test, expect } from '@playwright/test';

// Fast, deterministic — no external APIs. Validation is route-mocked.
test.describe('Home / discovery form', () => {
  test('renders the gene-input form with presets and a disabled start button', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('gene-input')).toBeVisible();
    await expect(page.getByTestId('disease-select')).toBeVisible();
    await expect(page.getByTestId('preset-group')).toBeVisible();
    // Start is disabled until genes are entered (Alpine reactive).
    await expect(page.getByTestId('start-btn')).toBeDisabled();
  });

  test('enables start once genes are entered', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('gene-input').fill('PIK3R1 ITGB1 SRC');
    await expect(page.getByTestId('start-btn')).toBeEnabled();
  });

  test('validate button swaps in the validation fragment (mocked)', async ({ page }) => {
    await page.route('**/ui/validate', (route) =>
      route.fulfill({
        contentType: 'text/html; charset=utf-8',
        body:
          '<div class="alert alert-success" data-testid="validation-success"><strong>✓ 3 genes validated.</strong></div>' +
          '<div class="chips"><span class="chip">PIK3R1</span><span class="chip">ITGB1</span><span class="chip">SRC</span></div>',
      })
    );
    await page.goto('/');
    await page.getByTestId('gene-input').fill('PIK3R1 ITGB1 SRC');
    await page.getByTestId('validate-btn').click();
    await expect(page.getByTestId('validation-success')).toBeVisible();
    await expect(page.locator('.chip', { hasText: 'PIK3R1' })).toBeVisible();
  });
});
