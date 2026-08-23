import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const outputDir = path.resolve(here, '..', 'docs', 'screenshots');
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8000';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1500, height: 950 },
  deviceScaleFactor: 3,
  colorScheme: 'light',
  locale: 'en-US',
});
const page = await context.newPage();

async function capture(name) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(100);
  await page.screenshot({
    path: path.join(outputDir, name),
    animations: 'disabled',
  });
}

await page.goto(`${baseURL}/`, { waitUntil: 'networkidle' });
await page.getByTestId('gene-input').fill('MYH7 TTN LMNA MYBPC3 TNNT2');
await page.getByTestId('disease-select').selectOption('cardiomyopathy');
await capture('09-manuscript-analysis-setup.png');

await page.goto(`${baseURL}/results/analysis_fixture`, { waitUntil: 'networkidle' });
await page.getByTestId('network').waitFor({ state: 'visible' });
await page.waitForTimeout(800);
await capture('10-manuscript-ranked-results.png');

const detailHref = await page.getByTestId('pathway-link').first().getAttribute('href');
if (!detailHref) throw new Error('Fixture did not provide a pathway detail link');
await page.goto(`${baseURL}${detailHref}`, { waitUntil: 'networkidle' });
await page.getByTestId('metrics').waitFor({ state: 'visible' });
await capture('11-manuscript-pathway-evidence.png');

await browser.close();
