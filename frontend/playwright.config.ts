import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const isCI = !!process.env.CI;

export default defineConfig({
  testDir: './tests',
  timeout: 900_000,
  expect: { timeout: 5000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.VITE_APP_URL || 'http://127.0.0.1:3000',
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: path.resolve(process.cwd(), '..'),
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !isCI,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 3000',
      cwd: process.cwd(),
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: !isCI,
    },
  ],
});
