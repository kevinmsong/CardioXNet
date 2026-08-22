import { test, expect } from '@playwright/test';

// Renders the committed deterministic fixture analysis (outputs/analysis_fixture)
// through the real server load path — no external APIs, no live pipeline.
const FIXTURE = 'analysis_fixture';

test.describe('Results (fixture)', () => {
  test('summary, table, novelty, network and top genes render', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);

    await expect(page.getByRole('heading', { name: 'Discovery results' })).toBeVisible();
    await expect(page.getByTestId('summary-stats')).toBeVisible();

    // Four hypotheses in the fixture; three reached by expansion (seed-independent).
    const rows = page.getByTestId('pathway-row');
    await expect(rows).toHaveCount(4);
    await expect(page.getByTestId('novel-badge').first()).toBeVisible();
    expect(await page.getByTestId('novel-badge').count()).toBe(3);

    await expect(page.getByTestId('results-table')).toBeVisible();
    await expect(page.getByTestId('network')).toBeVisible();
    await expect(page.getByTestId('top-genes-table')).toBeVisible();
  });

  test('column sort reorders rows', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const firstBefore = await page.getByTestId('pathway-row').first().getAttribute('data-pps');
    await page.locator('th.sortable[data-col="pps"]').click(); // ascending
    const firstAfter = await page.getByTestId('pathway-row').first().getAttribute('data-pps');
    expect(firstBefore).not.toEqual(firstAfter);
  });

  test('drilling into a pathway shows lineage, metrics and citations', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    // Follow the first hypothesis link (href navigation avoids sticky-header click interception).
    const href = await page.getByTestId('pathway-link').first().getAttribute('href');
    expect(href).toContain('/pathway/');
    await page.goto(href!);
    await expect(page).toHaveURL(/\/pathway\//);

    await expect(page.getByTestId('pathway-title')).toBeVisible();
    await expect(page.getByTestId('lineage')).toBeVisible();
    await expect(page.getByTestId('metrics')).toBeVisible();
    await expect(page.getByTestId('evidence-genes')).toBeVisible();

    const citations = page.getByTestId('citation');
    expect(await citations.count()).toBeGreaterThan(0);

    // Abstract is hidden until expanded.
    const firstCite = citations.first();
    await firstCite.getByRole('button', { name: /Abstract/ }).click();
    await expect(firstCite.locator('.cite-abstract')).toBeVisible();
  });

  test('CSV export is downloadable', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByTestId('export-csv').click(),
    ]);
    expect(download.suggestedFilename()).toContain('.csv');
  });
});
