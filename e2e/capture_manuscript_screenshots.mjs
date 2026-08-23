import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const here = path.dirname(fileURLToPath(import.meta.url));
const outputDir = path.resolve(here, '..', 'docs', 'screenshots');
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8000';
fs.mkdirSync(outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1280, height: 1000 },
  deviceScaleFactor: 4,
  colorScheme: 'light',
  locale: 'en-US',
  reducedMotion: 'reduce',
});
const page = await context.newPage();
const capturedPaths = [];

async function prepareCapture() {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(100);
}

async function capture(name) {
  await prepareCapture();
  const outputPath = path.join(outputDir, name);
  await page.screenshot({
    path: outputPath,
    animations: 'disabled',
  });
  capturedPaths.push(outputPath);
}

async function captureElement(name, locator) {
  await prepareCapture();
  await locator.scrollIntoViewIfNeeded();
  const outputPath = path.join(outputDir, name);
  await locator.screenshot({
    path: outputPath,
    animations: 'disabled',
  });
  capturedPaths.push(outputPath);
}

await page.goto(`${baseURL}/`, { waitUntil: 'networkidle' });
await page.getByTestId('gene-input').fill('MYH7 TTN LMNA MYBPC3 TNNT2');
await page.getByTestId('disease-select').selectOption('cardiomyopathy');
await capture('09-manuscript-analysis-setup.png');

await page.goto(`${baseURL}/results/analysis_fixture`, { waitUntil: 'networkidle' });
await page.getByTestId('network').waitFor({ state: 'visible' });
await page.waitForTimeout(800);
await page.addStyleTag({ content: `
  main.container { max-width: 1180px !important; }
  [data-testid="hypotheses-card"] .table-wrap { overflow: visible !important; }
  #results-table { font-size: 1.08rem !important; }
  #results-table thead th { font-size: .88rem !important; }
  #results-table .pw-id, #results-table .small { font-size: .82rem !important; }
  #results-table th:nth-child(n+8), #results-table td:nth-child(n+8) { display: none; }
` });
await captureElement(
  '10-manuscript-ranked-results.png',
  page.getByTestId('hypotheses-card'),
);

const detailHref = await page.getByTestId('pathway-link').first().getAttribute('href');
if (!detailHref) throw new Error('Fixture did not provide a pathway detail link');
await page.goto(`${baseURL}${detailHref}`, { waitUntil: 'networkidle' });
await page.getByTestId('metrics').waitFor({ state: 'visible' });
await page.addStyleTag({ content: `
  main.container { max-width: 1180px !important; }
  .grid-2 { grid-template-columns: 1fr !important; max-width: 1120px !important; }
  [data-testid="metrics-card"] { font-size: 1.05rem !important; }
  [data-testid="metrics-card"] .pw-id,
  [data-testid="metrics-card"] .small { font-size: .88rem !important; }
` });
await page.getByTestId('metrics-card').locator('details').evaluateAll((details) => {
  for (const detail of details) detail.open = true;
});
await captureElement(
  '11-manuscript-pathway-evidence.png',
  page.getByTestId('metrics-card'),
);

await browser.close();

// Chromium writes high-pixel-density screenshots with screen-resolution PNG
// metadata. Retag the lossless pixels at the publication resolution required
// by the manuscript workflow so the capture is reproducible end to end.
const dpiTagger = [
  'from PIL import Image',
  'import sys',
  'for path in sys.argv[1:]:',
  '    with Image.open(path) as source:',
  '        image = source.copy()',
  '    image.save(path, dpi=(600, 600))',
].join('\n');
const tagged = spawnSync('python', ['-c', dpiTagger, ...capturedPaths], {
  encoding: 'utf8',
});
if (tagged.status !== 0) {
  throw new Error(`Could not tag manuscript screenshots at 600 dpi: ${tagged.stderr}`);
}
