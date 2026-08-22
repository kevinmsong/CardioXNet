import { test, expect } from '@playwright/test';

test.describe('Navigation & static pages', () => {
  test('documentation page renders the methodology', async ({ page }) => {
    await page.goto('/documentation');
    await expect(page.getByRole('heading', { name: 'Documentation' })).toBeVisible();
    await expect(page.getByText('The known → unknown pipeline')).toBeVisible();
  });

  test('API reference lists endpoints', async ({ page }) => {
    await page.goto('/api-reference');
    await expect(page.getByRole('heading', { name: 'API reference' })).toBeVisible();
    await expect(page.getByText('/api/v1/analysis/run').first()).toBeVisible();
  });

  test('top navigation links work', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('main-nav').getByRole('link', { name: 'Documentation', exact: true }).click();
    await expect(page).toHaveURL(/\/documentation$/);
    await page.getByTestId('main-nav').getByRole('link', { name: 'API', exact: true }).click();
    await expect(page).toHaveURL(/\/api-reference$/);
  });

  test('unknown route returns 404', async ({ page }) => {
    const resp = await page.goto('/this-route-does-not-exist');
    expect(resp?.status()).toBe(404);
  });

  test('static CSS and vendored libs are served', async ({ request }) => {
    expect((await request.get('/static/css/app.css')).status()).toBe(200);
    expect((await request.get('/static/vendor/htmx.min.js')).status()).toBe(200);
    expect((await request.get('/static/vendor/alpine.min.js')).status()).toBe(200);
  });
});
