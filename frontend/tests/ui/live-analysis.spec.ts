import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { expect, test } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.use({
  launchOptions: {
    slowMo: process.env.CI ? 0 : 150,
  },
});

test('submits a live analysis through the UI and verifies PDF export', async ({ page, request }) => {
  test.setTimeout(900_000);

  const artifactsDir = path.resolve(__dirname, '../artifacts');
  fs.mkdirSync(artifactsDir, { recursive: true });

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'CardioXNet' })).toBeVisible();

  await page.locator('[role="combobox"]').first().click();
  await page.getByRole('option', { name: /Diabetic Cardiomyopathy/i }).click();

  await page.getByLabel('Enter or Paste Gene Symbols').fill('PIK3R1 ITGB1 SRC');
  await page.getByRole('button', { name: 'Add Genes' }).click();
  await expect(page.getByText(/validated successfully/i)).toBeVisible({ timeout: 60_000 });

  await page.getByRole('button', { name: 'Focused' }).click();
  await page.getByLabel('Evidence depth').click();
  await page.getByRole('option', { name: 'Fast screening' }).click();

  await page.screenshot({
    path: path.join(artifactsDir, 'live-ui-home-configured.png'),
    fullPage: true,
  });

  await page.getByRole('button', { name: /Start Analysis/i }).click();
  await expect(page).toHaveURL(/\/progress\/analysis_/, { timeout: 60_000 });

  const progressPath = path.join(artifactsDir, 'live-ui-progress.png');
  await page.waitForTimeout(3_000);
  await page.screenshot({ path: progressPath, fullPage: true });

  await expect(page).toHaveURL(/\/results\/analysis_/, { timeout: 900_000 });
  await expect(page.getByRole('heading', { name: 'Analysis Results', exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/Important Genes/i)).toBeVisible();

  const analysisMatch = page.url().match(/\/results\/([^/]+)/);
  expect(analysisMatch).not.toBeNull();
  const analysisId = analysisMatch![1];

  const pdfResponse = await request.get(`http://127.0.0.1:8000/api/v1/analysis/${analysisId}/report/pdf`);
  expect(pdfResponse.ok()).toBeTruthy();
  expect(pdfResponse.headers()['content-type'] || '').toContain('application/pdf');
  fs.writeFileSync(path.join(artifactsDir, `report-${analysisId}.pdf`), await pdfResponse.body());

  await page.screenshot({
    path: path.join(artifactsDir, 'live-ui-results.png'),
    fullPage: true,
  });
});
