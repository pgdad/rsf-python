import { test, expect } from './fixtures/capture';

test('smoke: capture fixture records steps', async ({ page, capture }) => {
  await capture.step('initial-graph', {
    title: 'Starter workflow',
    description: 'The default two-state workflow from rsf init',
  });

  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();

  await capture.step('verify-nodes', {
    title: 'Verify starter states',
    description: 'HelloWorld and Done states are visible',
    highlight: { selector: '[data-testid="state-HelloWorld"]', label: 'Start state' },
  });
});
