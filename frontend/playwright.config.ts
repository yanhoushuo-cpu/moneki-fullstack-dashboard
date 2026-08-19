import { defineConfig, devices } from '@playwright/test';

const python = process.env.PYTHON_EXECUTABLE ?? 'python';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium-desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'chromium-mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: `npm run build && "${python}" -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000`,
        url: 'http://127.0.0.1:8000/api/v1/health',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
