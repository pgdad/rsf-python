import { test, expect } from './fixtures/capture';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// Read the full order-processing workflow from the repo
const REPO_ROOT = resolve(import.meta.dirname, '..', '..');
const fullWorkflow = readFileSync(
  resolve(REPO_ROOT, 'examples', 'order-processing', 'workflow.yaml'),
  'utf-8',
);

// A simplified version for the first stage (core structure without Retry/Catch/Parallel details)
const BASIC_YAML = `rsf_version: "1.0"
Comment: "Order processing workflow"
StartAt: ValidateOrder

States:
  ValidateOrder:
    Type: Task
    Next: CheckOrderValue

  CheckOrderValue:
    Type: Choice
    Choices:
      - Variable: "$.validation.total"
        NumericGreaterThan: 1000
        Next: RequireApproval
    Default: ProcessOrder

  RequireApproval:
    Type: Task
    Next: ProcessOrder

  ProcessOrder:
    Type: Task
    Next: SendConfirmation

  SendConfirmation:
    Type: Task
    Next: OrderComplete

  OrderComplete:
    Type: Succeed

  OrderRejected:
    Type: Fail
    Error: "OrderRejected"
    Cause: "Order could not be processed"
`;

/** Helper to set YAML in Monaco editor */
async function setMonacoYaml(page: import('@playwright/test').Page, yaml: string): Promise<void> {
  const edited = await page.evaluate((y: string) => {
    const w = window as unknown as Record<string, unknown>;
    if (!w.monaco) return false;

    const monaco = w.monaco as {
      editor: {
        getModels: () => Array<{ setValue: (v: string) => void }>;
      };
    };

    const models = monaco.editor.getModels();
    if (models.length === 0) return false;

    models[0].setValue(y);
    return true;
  }, yaml);

  if (!edited) {
    const editorPane = page.locator('[data-testid="yaml-editor"]');
    await editorPane.click();
    await page.keyboard.press('Control+a');
    await page.waitForTimeout(200);
    await page.keyboard.type(yaml, { delay: 5 });
  }

  // Wait for YAML -> graph sync
  await page.waitForTimeout(3000);
}

test('Tutorial 5: Order Processing (Full Example)', async ({ page, capture }) => {
  // Step 1: Observe the starter workflow
  await capture.step('starter-workflow', {
    title: 'The starter workflow',
    description: 'Starting from the default rsf init workflow. We will build a full order processing workflow.',
  });

  // Step 2: Enter the basic structure first
  await setMonacoYaml(page, BASIC_YAML);

  // Verify core states appear
  await expect(page.locator('[data-testid="state-ValidateOrder"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckOrderValue"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessOrder"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderComplete"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderRejected"]')).toBeVisible();

  await capture.step('basic-structure', {
    title: 'Basic order processing structure',
    description: 'The simplified workflow shows the core flow: ValidateOrder → CheckOrderValue (Choice) → ProcessOrder → SendConfirmation → OrderComplete, with an OrderRejected fail state.',
  });

  // Step 3: Highlight the Choice state
  await capture.step('core-states-visible', {
    title: 'CheckOrderValue — the routing decision',
    description: 'The Choice state routes high-value orders (> $1000) to RequireApproval, and all others directly to ProcessOrder.',
    highlight: { selector: '[data-testid="state-CheckOrderValue"]', label: 'Choice state' },
  });

  // Step 4: Replace with the full workflow from file
  await setMonacoYaml(page, fullWorkflow);

  await capture.step('full-workflow-yaml', {
    title: 'Full order processing workflow loaded',
    description: 'Replaced the simplified YAML with the complete workflow from examples/order-processing/workflow.yaml, including Retry/Catch and Parallel states.',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'Full workflow YAML' },
  });

  // Step 5: Verify all 7 states are visible
  await expect(page.locator('[data-testid="state-ValidateOrder"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckOrderValue"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-RequireApproval"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessOrder"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-SendConfirmation"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderComplete"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderRejected"]')).toBeVisible();

  await capture.step('full-graph', {
    title: 'Complete graph with all 7 states',
    description: 'The full workflow graph shows all seven states with Choice branching, Parallel processing, Retry/Catch error handling, and terminal states.',
  });

  // Step 6: Click and expand ValidateOrder to show retry/catch config
  const validateNode = page.locator('[data-testid="state-ValidateOrder"]');
  await validateNode.click();
  await page.waitForTimeout(500);

  const validateExpandBtn = validateNode.locator('.node-expand-chevron');
  if (await validateExpandBtn.isVisible()) {
    await validateExpandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('validate-retry-catch', {
    title: 'ValidateOrder — Retry and Catch',
    description: 'Expanding ValidateOrder reveals retry config (3 attempts, exponential backoff for ValidationTimeout) and a Catch clause routing InvalidOrderError to OrderRejected.',
    highlight: { selector: '[data-testid="state-ValidateOrder"]', label: 'Retry + Catch' },
  });

  // Step 7: Click and expand ProcessOrder to show parallel branches
  const processNode = page.locator('[data-testid="state-ProcessOrder"]');
  await processNode.click();
  await page.waitForTimeout(500);

  const processExpandBtn = processNode.locator('.node-expand-chevron');
  if (await processExpandBtn.isVisible()) {
    await processExpandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('process-parallel', {
    title: 'ProcessOrder — Parallel branches',
    description: 'Expanding ProcessOrder reveals two parallel branches: ProcessPayment and ReserveInventory, each with their own retry configurations.',
    highlight: { selector: '[data-testid="state-ProcessOrder"]', label: 'Parallel branches' },
  });

  // Step 8: Final verification
  await expect(page.locator('[data-testid="state-ValidateOrder"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-CheckOrderValue"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-RequireApproval"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessOrder"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-SendConfirmation"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderComplete"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-OrderRejected"]')).toBeVisible();

  // Edges will vary due to catch edges — use greaterThanOrEqual
  const edges = page.locator('.react-flow__edge');
  expect(await edges.count()).toBeGreaterThanOrEqual(7);

  await capture.step('final-complete', {
    title: 'Order processing workflow — complete',
    description: 'The full order processing workflow demonstrates Task, Choice, Parallel, Succeed, and Fail states with Retry/Catch error handling. This is a production-ready pattern.',
  });
});
