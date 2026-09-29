import { defineConfig, devices } from '@playwright/test';

const CI = !!process.env.CI;

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: CI ? 1 : 0,
  reporter: CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure' },
  projects: [
    { name: 'mobile', use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 } }, grep: /@mobile/ },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } }, grep: /@desktop/ },
  ],
  webServer: [
    {
      command: 'cd ../backend && uv run python -m app.seed --reset && uv run uvicorn app.main:app --port 8000',
      url: 'http://127.0.0.1:8000/healthz',
      reuseExistingServer: !CI,
      env: { FP_DATABASE_URL: 'sqlite:///./e2e.db', FP_SCHEDULER_ENABLED: 'false' },
      timeout: 120_000,
    },
    { command: 'npx vite --host 127.0.0.1 --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: !CI },
  ],
});
