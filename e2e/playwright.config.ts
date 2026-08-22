import { defineConfig, devices } from '@playwright/test';
import path from 'path';

// Single-port app: FastAPI serves the UI and the API on :8000.
const PORT = process.env.PORT || '8000';
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${PORT}`;
const REPO_ROOT = path.resolve(__dirname, '..');

export default defineConfig({
  testDir: '.',
  timeout: 60_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  reporter: [['list'], ['html', { open: 'never' }]],
  outputDir: 'artifacts',
  use: {
    baseURL: BASE_URL,
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  // Launch the Python app (no Node build). Reuse an already-running server if present.
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: `python -m uvicorn app.main:app --port ${PORT}`,
        cwd: REPO_ROOT,
        url: `${BASE_URL}/health`,
        timeout: 180_000,
        reuseExistingServer: true,
        stdout: 'pipe',
        stderr: 'pipe',
      },
});
