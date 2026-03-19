import { test, expect } from './fixtures/rsf-server';

test('smoke: rsf ui starts and graph renders', async ({ page }) => {
  // The fixture navigates to the editor and waits for readiness
  await expect(page.locator('.react-flow__node')).toHaveCount(2); // HelloWorld + Done
  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();
});
