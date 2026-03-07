const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ANALYSIS_ID = process.env.ANALYSIS_ID || 'fast_analysis_20251017_070137';
const HOST = process.env.FRONTEND_HOST || 'http://localhost:3000';
const URL = `${HOST}/results/${ANALYSIS_ID}`;
const defaultOutPath = path.resolve(__dirname, '../tests/artifacts/manual-results-screenshot.png');
const OUT_PATH = process.env.OUT_PATH || defaultOutPath;

(async () => {
  console.log(`Opening ${URL}`);
  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  try {
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForSelector('text=Analysis Results', { timeout: 10000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: OUT_PATH, fullPage: true });
    console.log('Screenshot saved to', OUT_PATH);
  } catch (err) {
    console.error('Failed to capture screenshot:', err);
    process.exitCode = 2;
  } finally {
    await browser.close();
  }
})();
