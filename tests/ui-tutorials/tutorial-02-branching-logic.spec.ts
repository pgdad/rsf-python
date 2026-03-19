import { test, expect } from './fixtures/capture';

const TARGET_YAML = `rsf_version: "1.0"
Comment: "Branching logic tutorial"
StartAt: ValidateInput

States:
  ValidateInput:
    Type: Task
    Next: CheckResult

  CheckResult:
    Type: Choice
    Choices:
      - Variable: "$.valid"
        BooleanEquals: true
        Next: ProcessItem
    Default: InvalidInput

  ProcessItem:
    Type: Task
    Next: Success

  Success:
    Type: Succeed

  InvalidInput:
    Type: Fail
    Error: "ValidationError"
    Cause: "Input validation failed"
`;

test('Tutorial 2: Branching Logic', async ({ page, capture }) => {
  // Step 1: Observe the starter workflow
  await capture.step('starter-workflow', {
    title: 'The starter workflow',
    description: 'Starting from the default rsf init workflow before adding branching logic.',
  });

  // Step 2: Enter the YAML via Monaco API
  await capture.step('yaml-entered', {
    title: 'Enter the branching workflow YAML',
    description: 'Paste a workflow with a Choice state that branches based on validation results.',
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
  await expect(page.locator('[data-testid="state-ValidateInput"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckResult"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessItem"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Success"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-InvalidInput"]')).toBeVisible();

  // Step 3: Graph rendered — highlight the Choice state
  await capture.step('graph-rendered', {
    title: 'Five-state workflow with Choice branching',
    description: 'The graph shows ValidateInput → CheckResult (Choice) branching to ProcessItem or InvalidInput.',
    highlight: { selector: '[data-testid="state-CheckResult"]', label: 'Choice state' },
  });

  // Step 4: Click and expand CheckResult
  const checkResultNode = page.locator('[data-testid="state-CheckResult"]');
  await checkResultNode.click();
  await page.waitForTimeout(500);

  const expandBtn = checkResultNode.locator('.node-expand-chevron');
  if (await expandBtn.isVisible()) {
    await expandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('choice-expanded', {
    title: 'Choice state expanded',
    description: 'Expanding CheckResult reveals its branching rules: if $.valid is true, go to ProcessItem; otherwise, go to InvalidInput.',
    highlight: { selector: '[data-testid="state-CheckResult"]', label: 'Expanded Choice' },
  });

  // Step 5: Final verification
  // Re-verify all states
  await expect(page.locator('[data-testid="state-ValidateInput"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckResult"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessItem"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Success"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-InvalidInput"]')).toBeVisible();

  // Verify edges: ValidateInput→CheckResult, CheckResult→ProcessItem, CheckResult→InvalidInput, ProcessItem→Success = 4
  const edges = page.locator('.react-flow__edge');
  await expect(edges).toHaveCount(4);

  await capture.step('final-workflow', {
    title: 'Complete branching logic workflow',
    description: 'All five states are connected with proper Choice branching. The workflow validates input and routes to success or failure.',
  });
});
