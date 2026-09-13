import { defineConfig, devices } from '@playwright/test';
import { resolve } from 'node:path';

const projectRoot = resolve(__dirname, '..');

export default defineConfig({
  testDir: '.',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [['list'], ['html', { outputFolder: 'test-results/frontend-report', open: 'never' }]],
  webServer: {
    command: `node "${resolve(__dirname, 'static-server.cjs')}"`,
    port: 4173,
    reuseExistingServer: true,
    timeout: 30_000,
  },
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});