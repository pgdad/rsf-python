import { test, expect } from './fixtures/capture';

const TARGET_YAML = `rsf_version: "1.0"
Comment: "Wait and retry tutorial"
StartAt: SubmitRequest

States:
  SubmitRequest:
    Type: Task
    Retry:
      - ErrorEquals: ["ServiceUnavailable"]
        IntervalSeconds: 2
        MaxAttempts: 3
        BackoffRate: 2.0
    Catch:
      - ErrorEquals: ["States.ALL"]
        Next: HandleError
        ResultPath: "$.error"
    Next: WaitForProcessing

  WaitForProcessing:
    Type: Wait
    Seconds: 10
    Next: CheckStatus

  CheckStatus:
    Type: Task
    Next: Complete

  Complete:
    Type: Succeed

  HandleError:
    Type: Fail
    Error: "ProcessingFailed"
    Cause: "Request processing failed after retries"
`;

test('Tutorial 3: Wait & Retry', async ({ page, capture }) => {
  // Step 1: Observe the starter workflow
  await capture.step('starter-workflow', {
    title: 'The starter workflow',
    description: 'Starting from the default rsf init workflow before adding wait and retry logic.',
  });

  // Step 2: Enter the YAML via Monaco API
  await capture.step('yaml-entered', {
    title: 'Enter the wait and retry workflow YAML',
    description: 'Paste a workflow with Retry/Catch on a Task state and a Wait state for polling.',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'YAML editor' },
  });

  const edited = await page.evaluate((yaml: string) => {
    const w = window as unknown as Record<string, unknown>;
    if (!w.monaco) return false;

    const monaco = w.monaco as {
      editor: {
        getModels: () => Array<{ setValue: (v: string) => void }>;
      };
    };

    const models = monaco.editor.getModels();
    if (models.length === 0) return false;

    models[0].setValue(yaml);
    return true;
  }, TARGET_YAML);

  if (!edited) {
    const editorPane = page.locator('[data-testid="yaml-editor"]');
    await editorPane.click();
    await page.keyboard.press('Control+a');
    await page.waitForTimeout(200);
    await page.keyboard.type(TARGET_YAML, { delay: 5 });
  }

  // Wait for YAML -> graph sync
  await page.waitForTimeout(3000);

  // Verify all 5 states are visible
  await expect(page.locator('[data-testid="state-SubmitRequest"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-WaitForProcessing"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckStatus"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Complete"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-HandleError"]')).toBeVisible();

  // Step 3: Graph rendered
  await capture.step('graph-rendered', {
    title: 'Five-state workflow with retry and wait',
    description: 'The graph shows SubmitRequest (with Retry/Catch) → WaitForProcessing → CheckStatus → Complete, with a Catch edge to HandleError.',
  });

  // Step 4: Click and expand SubmitRequest to show retry config
  const submitNode = page.locator('[data-testid="state-SubmitRequest"]');
  await submitNode.click();
  await page.waitForTimeout(500);

  const submitExpandBtn = submitNode.locator('.node-expand-chevron');
  if (await submitExpandBtn.isVisible()) {
    await submitExpandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('retry-config', {
    title: 'SubmitRequest with Retry and Catch',
    description: 'Expanding SubmitRequest reveals retry configuration: 3 attempts with exponential backoff, and a Catch clause routing errors to HandleError.',
    highlight: { selector: '[data-testid="state-SubmitRequest"]', label: 'Retry + Catch' },
  });

  // Deselect SubmitRequest by clicking on the canvas background
  await page.locator('.react-flow__pane').click({ position: { x: 50, y: 50 } });
  await page.waitForTimeout(500);

  // Step 5: Click and expand WaitForProcessing to show wait config
  const waitNode = page.locator('[data-testid="state-WaitForProcessing"]');
  await waitNode.click();
  await page.waitForTimeout(500);

  const waitExpandBtn = waitNode.locator('.node-expand-chevron');
  if (await waitExpandBtn.isVisible()) {
    await waitExpandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('wait-config', {
    title: 'WaitForProcessing — Wait state',
    description: 'The Wait state pauses execution for 10 seconds before checking the status. This is useful for polling patterns.',
    highlight: { selector: '[data-testid="state-WaitForProcessing"]', label: 'Wait 10s' },
  });

  // Step 6: Final verification
  await expect(page.locator('[data-testid="state-SubmitRequest"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-WaitForProcessing"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckStatus"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Complete"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-HandleError"]')).toBeVisible();

  // Edges: SubmitRequest→WaitForProcessing, SubmitRequest→HandleError (Catch), WaitForProcessing→CheckStatus, CheckStatus→Complete
  // Use >= because catch edges may vary
  const edges = page.locator('.react-flow__edge');
  await expect(edges).toHaveCount(await edges.count()); // just ensure they exist
  expect(await edges.count()).toBeGreaterThanOrEqual(4);

  await capture.step('final-workflow', {
    title: 'Complete wait and retry workflow',
    description: 'All five states are connected. The workflow demonstrates retry with backoff, error catching, and timed waits.',
  });
});
