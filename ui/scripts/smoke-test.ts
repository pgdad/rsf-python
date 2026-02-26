import { chromium } from '@playwright/test';

async function main() {
  console.log('Launching Chromium...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to https://example.com...');
  await page.goto('https://example.com');

  const title = await page.title();
  console.log(`Page title: ${title}`);

  if (!title.toLowerCase().includes('example')) {
    throw new Error(`Unexpected title: "${title}"`);
  }

  console.log('Title assertion passed.');
  await browser.close();
  console.log('Browser closed. Playwright smoke test PASSED.');
}

main().catch((err) => {
  console.error('Smoke test FAILED:', err);
  process.exit(1);
});
