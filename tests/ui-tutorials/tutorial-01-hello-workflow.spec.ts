import { test, expect } from './fixtures/capture';

const TARGET_YAML = `rsf_version: "1.0"
Comment: "Hello Workflow tutorial"
StartAt: HelloWorld

States:
  HelloWorld:
    Type: Task
    Next: ProcessData

  ProcessData:
    Type: Task
    Next: Done

  Done:
    Type: Succeed
`;

test('Tutorial 1: Hello Workflow', async ({ page, capture }) => {
  // Step 1: Observe the starter workflow
  await capture.step('starter-workflow', {
    title: 'The starter workflow',
    description: 'After rsf init, you have a two-state workflow: HelloWorld (Task) → Done (Succeed)',
  });

  // Verify starter states exist
  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();

  // Step 2: Show the palette where a Task state can be dragged from
  await capture.step('drag-task-start', {
    title: 'Drag a Task state from the palette',
    description: 'Drag the Task item from the palette onto the canvas to add a new state',
    highlight: { selector: '[data-testid="palette-task"]', label: 'Drag from here' },
    format: 'gif-start',
  });

  // Note: HTML5 drag-and-drop with custom dataTransfer ('application/rsf-state-type')
  // is not reliably reproducible with Playwright's dragTo(). Instead, we demonstrate
  // the equivalent workflow by editing the YAML directly — which is the primary editing
  // method shown in the tutorial anyway.

  // Step 3: Edit the YAML to add the ProcessData state
  await capture.step('yaml-editor', {
    title: 'Rename the state in the YAML editor',
    description: 'Edit the YAML to add a "ProcessData" state and connect it between HelloWorld and Done',
    highlight: { selector: '[data-testid="yaml-editor"]', label: 'Edit YAML here' },
  });

  // Use Monaco's JavaScript API to set the editor content.
  // Monaco exposes itself as window.monaco in browser context.
  // We replace the full model content using ITextModel.setValue().
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
    // Fallback: click the editor and type via keyboard
    const editorPane = page.locator('[data-testid="yaml-editor"]');
    await editorPane.click();
    // Monaco uses a hidden textarea for input
    await page.keyboard.press('Control+a');
    await page.waitForTimeout(200);
    await page.keyboard.type(TARGET_YAML, { delay: 5 });
  }

  // Wait for YAML → graph sync (parsing + graph update + ELK layout)
  await page.waitForTimeout(3000);

  // Verify the new state appears
  await expect(page.locator('[data-testid="state-ProcessData"]')).toBeVisible();

  // Step 4: Show the new state after YAML edit (equiv. to "task-added")
  await capture.step('task-added', {
    title: 'New Task state appears on the canvas',
    description: 'A new Task state "ProcessData" has been added by editing the YAML.',
    format: 'gif-end',
  });

  // Step 5: Show the complete workflow
  await capture.step('workflow-complete', {
    title: 'Complete three-state workflow',
    description: 'The workflow now has three states: HelloWorld → ProcessData → Done',
    highlight: { selector: '[data-testid="state-ProcessData"]', label: 'New state' },
  });

  // Step 6: Verify the graph structure
  await expect(page.locator('[data-testid="state-HelloWorld"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-ProcessData"]')).toBeVisible();
  await expect(page.locator('[data-testid="state-Done"]')).toBeVisible();

  // Verify edges: should have 2 edges (HelloWorld→ProcessData, ProcessData→Done)
  const edges = page.locator('.react-flow__edge');
  await expect(edges).toHaveCount(2);

  await capture.step('final-verification', {
    title: 'Verify the completed workflow',
    description: 'All three states are connected: HelloWorld → ProcessData → Done. The workflow is valid.',
  });
});
