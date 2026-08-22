import { test, expect } from '@playwright/test';

/**
 * LIVE end-to-end discovery test — "known → unknown".
 *
 * Runs the REAL pipeline against live STRING / g:Profiler / PubMed so you can
 * watch genuine novel-pathway discovery. Slow and network-dependent — run headed:
 *
 *   cd e2e && npx playwright test --headed discovery
 *
 * It proves the scientific claim: seed genes → primary pathways → secondary
 * literature-driven expansion → unreported pathways with citations and lineage.
 */

const SEEDS = process.env.DISCOVERY_SEEDS || 'PIK3R1 ITGB1 SRC';
const DISEASE = process.env.DISCOVERY_DISEASE || 'diabetic_cardiomyopathy';
const TIMEOUT_MS = Number(process.env.DISCOVERY_TIMEOUT_MS || 20 * 60 * 1000);

function statValue(page, label: string) {
  return page
    .locator('.stat', { has: page.locator('.k', { hasText: label }) })
    .locator('.v');
}

test('discovers unreported cardiac pathways from seed genes', async ({ page }) => {
  test.setTimeout(TIMEOUT_MS + 60_000);

  // 1. Configure the run on the home page.
  await page.goto('/');
  await page.getByTestId('gene-input').fill(SEEDS);
  await page.selectOption('[data-testid="disease-select"]', DISEASE);
  await page.locator('label[for="preset-fast"]').click(); // fastest preset for the demo

  // Open Advanced and trim breadth so a live run completes in a watchable window.
  // (These are the breadth-vs-speed levers; full defaults can take far longer on live APIs.)
  await page.getByTestId('advanced-toggle').click();
  await page.fill('#adv-string_neighbor_count', '25');
  await page.fill('#adv-primary_pathways_to_expand', '3');
  await page.fill('#adv-semantic_max_hypotheses_for_literature', '5');
  await page.fill('#adv-pubmed_max_results', '4');
  await page.fill('#adv-n_permutations', '0');
  await expect(page.getByTestId('start-btn')).toBeEnabled();

  // 2. Start → progress page.
  await page.getByTestId('start-btn').click();
  await page.waitForURL(/\/progress\//, { timeout: 60_000 });
  await expect(page.getByTestId('stage-timeline')).toBeVisible();
  // The pipeline should traverse the expansion stages.
  await expect(page.getByTestId('stage-timeline')).toContainText('secondary', { ignoreCase: true });

  // 3. Wait for completion → results (htmx HX-Redirect navigates here).
  await page.waitForURL(/\/results\//, { timeout: TIMEOUT_MS });
  await expect(page.getByRole('heading', { name: 'Discovery results' })).toBeVisible();

  // 4. Scientific assertions.
  const pathwayCount = Number((await statValue(page, 'Pathway hypotheses').textContent())?.trim());
  expect(pathwayCount, 'pipeline produced pathway hypotheses').toBeGreaterThan(0);

  const novelCount = Number((await statValue(page, 'Novel for these seeds').textContent())?.trim());
  expect(novelCount, 'discovered pathways novel for the seeds').toBeGreaterThan(0);

  // Secondary expansion occurred (known → unknown).
  const expanded = Number((await statValue(page, 'From secondary expansion').textContent())?.trim());
  expect.soft(expanded, 'pathways reached via secondary literature expansion').toBeGreaterThan(0);

  await expect(page.getByTestId('pathway-row').first()).toBeVisible();
  await expect(page.getByTestId('novel-badge').first()).toBeVisible();

  // Comprehensive literature search yielded citations across the result set.
  const totalCitations = Number((await statValue(page, 'Total citations').textContent())?.trim());
  expect(totalCitations, 'comprehensive literature search yielded citations').toBeGreaterThan(0);

  await page.screenshot({ path: 'artifacts/discovery-results.png', fullPage: true });

  // 5. Drill into a hypothesis: lineage + comprehensive literature.
  // Follow the href (avoids sticky-header click interception on the first row).
  const href = await page.getByTestId('pathway-link').first().getAttribute('href');
  await page.goto(href!);
  await expect(page).toHaveURL(/\/pathway\//);
  await expect(page.getByTestId('lineage')).toBeVisible();
  await expect(page.getByTestId('lineage')).toContainText('Secondary expansion');

  const citationCount = await page.getByTestId('citation').count();
  expect.soft(citationCount, 'top hypothesis has literature citations').toBeGreaterThan(0);

  await page.screenshot({ path: 'artifacts/discovery-pathway.png', fullPage: true });
});
