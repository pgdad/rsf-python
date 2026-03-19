import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'tutorial-*.spec.ts',
  timeout: 120_000, // 2 min per test — tutorials involve server startup
  retries: 0,
  workers: 1, // Sequential — each test starts its own rsf ui server
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    viewport: { width: 1280, height: 800 },
    video: 'on',
    screenshot: 'off', // We control screenshots via capture fixture
    trace: 'on-first-retry',
    browserName: 'chromium',
  },
  projects: [
    {
      name: 'tutorials',
      use: { browserName: 'chromium' },
    },
  ],
});
