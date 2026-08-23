import { test, expect } from '@playwright/test';

// Renders the committed deterministic fixture analysis (outputs/analysis_fixture)
// through the real server load path - no external APIs, no live pipeline.
const FIXTURE = 'analysis_fixture';

test.describe('Results (fixture)', () => {
  test('summary, table, novelty, network and top genes render', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);

    await expect(page.getByRole('heading', { name: 'Cardiovascular pathway hypotheses' })).toBeVisible();
    await expect(page.getByTestId('summary-stats')).toBeVisible();

    // Four hypotheses in the fixture, all reached by expansion (seed-independent).
    const rows = page.getByTestId('pathway-row');
    await expect(rows).toHaveCount(4);
    await expect(page.getByTestId('novel-badge').first()).toBeVisible();
    expect(await page.getByTestId('novel-badge').count()).toBe(4);

    // The Discovery Score is the primary ranking and must actually reach the
    // page. It previously did not: stage_3 was snapshotted before the scoring
    // stage ran, so results.json carried none of these fields.
    const first = rows.first();
    await expect(first).toHaveAttribute('data-discovery', /^[0-9]/);
    const discovery = await rows.evaluateAll((els) =>
      els.map((e) => parseFloat(e.getAttribute('data-discovery') || '0')));
    expect(discovery).toEqual([...discovery].sort((a, b) => b - a));
    expect(discovery[0]).toBeGreaterThan(0);

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

  test('drilling into a pathway shows lineage and metrics', async ({ page }) => {
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
  });

  test('citations render and expand for a pathway that has them', async ({ page }) => {
    // Deliberately NOT the first row. Rows rank by Discovery Score, and the
    // top-ranked hypothesis is the one with the *fewest* PubMed records at the
    // pathway x seeds x disease intersection -- frequently zero, which is the
    // finding, not a failure. Pick a row that actually carries citations.
    await page.goto(`/results/${FIXTURE}`);
    const rows = page.getByTestId('pathway-row');
    const counts = await rows.evaluateAll((els) =>
      els.map((e) => Number(e.getAttribute('data-lit') || '0')));
    const index = counts.findIndex((c) => c > 0);
    expect(index, 'fixture must contain at least one cited pathway').toBeGreaterThanOrEqual(0);

    const href = await rows.nth(index).getByTestId('pathway-link').getAttribute('href');
    await page.goto(href!);

    const citations = page.getByTestId('citation');
    expect(await citations.count()).toBeGreaterThan(0);

    // Abstract is hidden until expanded.
    const firstCite = citations.first();
    await firstCite.getByRole('button', { name: /Abstract/ }).click();
    await expect(firstCite.locator('.cite-abstract')).toBeVisible();
  });

  test('a pathway with no citations shows the empty state, not a blank', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const rows = page.getByTestId('pathway-row');
    const counts = await rows.evaluateAll((els) =>
      els.map((e) => Number(e.getAttribute('data-lit') || '0')));
    const index = counts.findIndex((c) => c === 0);
    test.skip(index < 0, 'fixture has no zero-citation pathway');

    const href = await rows.nth(index).getByTestId('pathway-link').getAttribute('href');
    await page.goto(href!);
    await expect(page.getByText(/No literature citations were retrieved/i)).toBeVisible();
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
