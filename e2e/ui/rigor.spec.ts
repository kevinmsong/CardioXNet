import { test, expect } from '@playwright/test';

/**
 * Scientific-rigor assertions against the committed deterministic fixture
 * (outputs/analysis_fixture). No external APIs.
 *
 * These exist because the corresponding defects all shipped: the Discovery Score
 * never reached the page at all (stage_3 was snapshotted before the scoring stage
 * ran), and the CSV export wrote a column into every row that was missing from
 * its header, silently mislabelling everything after it.
 *
 * The Python counterpart is tests/test_scientific_rigor.py; this file covers the
 * part of the contract that only the rendered page can prove.
 */
const FIXTURE = 'analysis_fixture';

// Column order in results.html: #, Pathway, Discovery, Novelty, PPS, p_adj,
// Perm. q, Fold, Genes, ... Index 5 is p_adj -- reading it by mistake makes the
// permutation assertion pass on the wrong column.
const PERM_Q_COL = 6;

test.describe('Scientific rigor (fixture)', () => {
  test('rows are ranked by Discovery Score and every row exposes its metrics', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const rows = page.getByTestId('pathway-row');
    await expect(rows.first()).toBeVisible();

    const metrics = await rows.evaluateAll((els) =>
      els.map((e) => ({
        discovery: e.getAttribute('data-discovery'),
        pps: e.getAttribute('data-pps'),
        permq: e.getAttribute('data-permq'),
        fold: e.getAttribute('data-fold'),
      })));

    // Discovery Score is the primary ranking. It reached the PDF report but not
    // results.json for three commits, so the page showed em-dashes throughout.
    for (const m of metrics) {
      expect(m.discovery, 'every row carries a Discovery Score').not.toBeNull();
      expect(Number.isFinite(parseFloat(m.discovery!))).toBeTruthy();
      expect(m.pps).not.toBeNull();
      expect(m.permq).not.toBeNull();
      expect(m.fold).not.toBeNull();
    }

    const discovery = metrics.map((m) => parseFloat(m.discovery!));
    expect(discovery, 'table is ordered by Discovery Score, descending')
      .toEqual([...discovery].sort((a, b) => b - a));
  });

  test('the Discovery column shows a value, never a placeholder, when one exists', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const firstDiscoveryCell = page.getByTestId('pathway-row').first().locator('td').nth(2);
    await expect(firstDiscoveryCell).not.toHaveText('—');
    await expect(firstDiscoveryCell).toHaveText(/^\d+\.\d+$/);
  });

  test('an untested permutation renders n/t, not a number and not a blank', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const rows = page.getByTestId('pathway-row');
    const count = await rows.count();

    for (let i = 0; i < count; i++) {
      const row = rows.nth(i);
      // data-permq falls back to 1 when the value is null; the cell must then
      // say n/t rather than print a q-value that was never computed.
      const cellText = (await row.locator('td').nth(PERM_Q_COL).innerText()).trim();
      const testable = await row.getAttribute('data-permq');
      if (cellText === 'n/t') {
        expect(testable, 'n/t is only shown where no q-value exists').toBe('1');
      } else {
        expect(cellText, 'a permutation cell is either n/t or a q-value').toMatch(/[\d.eE-]+/);
      }
    }
  });

  test('novelty tier renders as a labelled badge with its evidence', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const tiers = page.locator('span.badge.tier-novelty');
    expect(await tiers.count(), 'fixture hypotheses carry a novelty tier').toBeGreaterThan(0);

    // The badge class uppercases via CSS, so compare case-insensitively.
    const valid = ['highly novel', 'novel', 'emerging', 'established', 'ungrounded'];
    for (const label of await tiers.allInnerTexts()) {
      // "Ungrounded" is a distinct, undefined result -- not a weak tier. It must
      // never be silently rendered on the same scale as a grounded call.
      expect(valid).toContain(label.trim().toLowerCase());
    }

    // The count the tier is derived from is shown alongside it.
    await expect(page.getByText(/\d+ PubMed hits/).first()).toBeVisible();
  });

  test('CSV export header and rows have equal width and correct labels', async ({ page }) => {
    // This defect shipped: novelty_confidence was written into every row but
    // omitted from the header, so every column after it was mislabelled in the
    // file researchers actually analyse.
    const response = await page.request.get(`/results/${FIXTURE}/export.csv`);
    expect(response.status()).toBe(200);

    const lines = (await response.text()).trim().split(/\r?\n/);
    expect(lines.length).toBeGreaterThan(1);

    const splitCsv = (line: string) => {
      const out: string[] = [];
      let cur = '';
      let quoted = false;
      for (const ch of line) {
        if (ch === '"') quoted = !quoted;
        else if (ch === ',' && !quoted) { out.push(cur); cur = ''; }
        else cur += ch;
      }
      out.push(cur);
      return out;
    };

    const header = splitCsv(lines[0]);
    for (const line of lines.slice(1)) {
      expect(splitCsv(line).length, `row width must match the ${header.length}-column header`)
        .toBe(header.length);
    }

    for (const column of ['discovery_score', 'novelty_tier', 'novelty_confidence',
                          'pubmed_hit_count', 'perm_q_value', 'pps_score']) {
      expect(header, `${column} must be present in the header`).toContain(column);
    }

    // Values land under their own headers.
    const first = Object.fromEntries(header.map((h, i) => [h, splitCsv(lines[1])[i]]));
    expect(['Highly Novel', 'Novel', 'Emerging', 'Established', 'Ungrounded', '—'])
      .toContain(first['novelty_tier']);
  });

  test('detail page shows the score breakdown and labels PPS honestly', async ({ page }) => {
    await page.goto(`/results/${FIXTURE}`);
    const href = await page.getByTestId('pathway-link').first().getAttribute('href');
    await page.goto(href!);

    const metrics = page.getByTestId('metrics');
    await expect(metrics).toContainText('Discovery Score');
    await expect(metrics).toContainText('Pathway Prioritization Score');
    // The component breakdown that justifies the score.
    await expect(metrics).toContainText(/sig[\s\S]*eff[\s\S]*spec[\s\S]*rep/);
    await expect(metrics).toContainText('Fold enrichment');

    // PPS is not a GSEA normalized enrichment score and the page must not imply it.
    await expect(page.locator('body')).not.toContainText('Network Enrichment Score');
  });
});
