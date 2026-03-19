import { test, expect } from './fixtures/capture';

const TARGET_YAML = `rsf_version: "1.0"
Comment: "Parallel processing tutorial"
StartAt: PrepareData

States:
  PrepareData:
    Type: Task
    Next: ProcessBranches

  ProcessBranches:
    Type: Parallel
    Branches:
      - StartAt: EnrichData
        States:
          EnrichData:
            Type: Task
            End: true
      - StartAt: ValidateData
        States:
          ValidateData:
            Type: Task
            End: true
    Next: MergeResults

  MergeResults:
    Type: Task
    Next: Done

  Done:
    Type: Succeed
`;

test('Tutorial 4: Parallel Processing', async ({ page, capture }) => {
  // Step 1: Observe the starter workflow
  await capture.step('starter-workflow', {
    title: 'The starter workflow',
    description: 'Starting from the default rsf init workflow before adding parallel processing.',
  });

  // Step 2: Enter the YAML via Monaco API
  await capture.step('yaml-entered', {
    title: 'Enter the parallel processing workflow YAML',
    description: 'Paste a workflow with a Parallel state that runs two branches concurrently.',
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

  // Verify all 4 main states are visible
  await expect(page.locator('[data-testid="state-PrepareData"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessBranches"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-MergeResults"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();

  // Step 3: Graph rendered — highlight the Parallel state
  await capture.step('graph-rendered', {
    title: 'Four-state workflow with Parallel processing',
    description: 'The graph shows PrepareData → ProcessBranches (Parallel) → MergeResults → Done.',
    highlight: { selector: '[data-testid="state-ProcessBranches"]', label: 'Parallel state' },
  });

  // Step 4: Click and expand ProcessBranches to reveal parallel branches
  const parallelNode = page.locator('[data-testid="state-ProcessBranches"]');
  await parallelNode.click();
  await page.waitForTimeout(500);

  const expandBtn = parallelNode.locator('.node-expand-chevron');
  if (await expandBtn.isVisible()) {
    await expandBtn.click();
    await page.waitForTimeout(500);
  }

  await capture.step('parallel-expanded', {
    title: 'Parallel state expanded',
    description: 'Expanding ProcessBranches reveals two concurrent branches: EnrichData and ValidateData, both running as Task states.',
    highlight: { selector: '[data-testid="state-ProcessBranches"]', label: 'Parallel branches' },
  });

  // Step 5: Final verification
  await expect(page.locator('[data-testid="state-PrepareData"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessBranches"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-MergeResults"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();

  await capture.step('final-workflow', {
    title: 'Complete parallel processing workflow',
    description: 'All four main states are connected. The workflow demonstrates parallel execution with two concurrent branches that merge results.',
  });
});
