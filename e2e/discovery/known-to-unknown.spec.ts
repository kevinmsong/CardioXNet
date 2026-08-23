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

// The panel must be *grounded*: novelty is only interpretable when the seed genes
// themselves have a literature footprint in the chosen disease. The previous
// default, PIK3R1/ITGB1/SRC in diabetic_cardiomyopathy, has 14 PubMed records at
// that intersection -- below the 100-record threshold -- so every pathway was
// correctly tiered "Ungrounded" and the novelty assertions could never pass.
// VEGFA/MMP9/IL6 in heart failure has ~3,000.
const SEEDS = process.env.DISCOVERY_SEEDS || 'VEGFA MMP9 IL6';
const DISEASE = process.env.DISCOVERY_DISEASE || 'heart_failure';
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
  // Minimum permitted is 100: the empirical p cannot fall below 1/(n+1), so a
  // 0-permutation "test" is not a test. The fast preset disables the permutation
  // null outright, so this value is not exercised -- but it must be in range or
  // HTML5 validation silently blocks the submit and the click does nothing.
  await page.fill('#adv-n_permutations', '100');
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

  // "Novel for these seeds" was split into two distinct measurements, because
  // they were being conflated: Literature-novel is about how much has been
  // published at the pathway x seeds x disease intersection, Seed-independent is
  // a structural property of how the pathway was reached.
  // A grounded panel must not produce Ungrounded tiers. If it does, the novelty
  // numbers below are undefined rather than low, and reading them as findings is
  // exactly the mistake the grounding check exists to prevent.
  const ungrounded = await page.locator('span.badge.tier-novelty', { hasText: /ungrounded/i }).count();
  expect(ungrounded,
    'a seed panel with a real literature footprint must yield interpretable novelty').toBe(0);

  const literatureNovel = Number((await statValue(page, 'Literature-novel').textContent())?.trim());
  expect(literatureNovel, 'pathways under-reported for these seeds').toBeGreaterThan(0);

  const seedIndependent = Number((await statValue(page, 'Seed-independent').textContent())?.trim());
  expect(seedIndependent, 'pathways reached by expansion rather than carried by the seeds')
    .toBeGreaterThan(0);

  // Secondary expansion occurred (known → unknown).
  const expanded = Number((await statValue(page, 'From secondary expansion').textContent())?.trim());
  expect.soft(expanded, 'pathways reached via secondary literature expansion').toBeGreaterThan(0);

  await expect(page.getByTestId('pathway-row').first()).toBeVisible();
  await expect(page.getByTestId('novel-badge').first()).toBeVisible();

  // This run uses the fast preset, which disables the permutation null. The
  // scientifically load-bearing assertion is therefore not "something was
  // significant" but "nothing was fabricated": with the test switched off, every
  // pathway must report n/t rather than a q-value it never earned.
  const fdrSignificant = Number(
    (await statValue(page, 'Permutation FDR').textContent())?.trim());
  const permCells = await page.getByTestId('pathway-row')
    .evaluateAll((els) => els.map((e) => (e.querySelectorAll('td')[6]?.textContent || '').trim()));
  if (fdrSignificant === 0) {
    expect(permCells.every((c) => c === 'n/t'),
      'with the permutation null disabled, no q-value may be reported').toBeTruthy();
  } else {
    expect(permCells.some((c) => /[\d.]/.test(c)),
      'if pathways cleared FDR, their q-values must be shown').toBeTruthy();
  }

  // Every reported row must carry a Discovery Score, and the table must be
  // ordered by it -- that is the tool's primary output.
  const discovery = await page.getByTestId('pathway-row').evaluateAll((els) =>
    els.map((e) => parseFloat(e.getAttribute('data-discovery') || 'NaN')));
  expect(discovery.every((d) => Number.isFinite(d)),
    'every row exposes a Discovery Score').toBeTruthy();
  expect(discovery, 'rows are ranked by Discovery Score')
    .toEqual([...discovery].sort((a, b) => b - a));

  await page.screenshot({ path: 'artifacts/discovery-results.png', fullPage: true });

  // 5. Drill into a hypothesis: lineage + comprehensive literature.
  // Follow the href (avoids sticky-header click interception on the first row).
  const href = await page.getByTestId('pathway-link').first().getAttribute('href');
  await page.goto(href!);
  await expect(page).toHaveURL(/\/pathway\//);
  await expect(page.getByTestId('lineage')).toBeVisible();
  await expect(page.getByTestId('lineage')).toContainText('Secondary expansion');

  // The top hypothesis by Discovery Score is, by construction, the one with the
  // FEWEST records at the intersection -- often zero. That is the finding, not a
  // failure, so assert the page renders a coherent literature section either way.
  const citationCount = await page.getByTestId('citation').count();
  if (citationCount === 0) {
    await expect(page.getByText(/No literature citations were retrieved/i)).toBeVisible();
  }

  // The novelty call must be grounded: a real cardiovascular seed panel has a
  // literature footprint, so its pathways must never be tiered "Ungrounded".
  await expect(page.getByTestId('metrics')).not.toContainText('Ungrounded');

  await page.screenshot({ path: 'artifacts/discovery-pathway.png', fullPage: true });
});
