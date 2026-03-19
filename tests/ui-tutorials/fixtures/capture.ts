/**
 * capture fixture — Playwright fixture that provides a CaptureHelper for
 * recording tutorial steps as annotated screenshots with a manifest.
 *
 * Extends the rsf-server fixture so that `page` is already navigated to
 * the editor with the graph rendered.
 *
 * Each tutorial spec gets its own output directory under
 * `tests/ui-tutorials/.captures/<tutorial-name>/` with:
 *   - step-NN-<name>.png screenshots
 *   - manifest.json describing all captured steps
 *
 * The manifest.json is consumed downstream by annotate.sh and assemble.py.
 */

import { test as base, expect } from './rsf-server';
import type { Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, basename } from 'node:path';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HighlightSpec {
  selector: string;
  label: string;
}

interface HighlightCoords {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
}

interface StepOptions {
  title: string;
  description: string;
  highlight?: HighlightSpec;
  format?: 'screenshot' | 'gif-start' | 'gif-end';
}

interface ManifestStep {
  step: number;
  name: string;
  title: string;
  description: string;
  screenshot: string;
  timestamp_ms: number;
  highlight?: HighlightCoords;
  format: string;
}

interface Manifest {
  tutorial: string;
  steps: ManifestStep[];
}

// ---------------------------------------------------------------------------
// CaptureHelper
// ---------------------------------------------------------------------------

class CaptureHelper {
  private page: Page;
  private outputDir: string;
  private tutorialName: string;
  private manifest: Manifest;
  private stepCounter: number;

  constructor(page: Page, outputDir: string, tutorialName: string) {
    this.page = page;
    this.outputDir = outputDir;
    this.tutorialName = tutorialName;
    this.stepCounter = 0;
    this.manifest = {
      tutorial: tutorialName,
      steps: [],
    };

    // Ensure output directory exists
    mkdirSync(outputDir, { recursive: true });
  }

  async step(name: string, options: StepOptions): Promise<void> {
    this.stepCounter++;
    const paddedStep = String(this.stepCounter).padStart(2, '0');
    const screenshotFilename = `step-${paddedStep}-${name}.png`;
    const screenshotPath = resolve(this.outputDir, screenshotFilename);
    const format = options.format ?? 'screenshot';

    // Resolve highlight bounding box if specified
    let highlightCoords: HighlightCoords | undefined;
    if (options.highlight) {
      const locator = this.page.locator(options.highlight.selector);
      const box = await locator.boundingBox();
      if (box) {
        highlightCoords = {
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height,
          label: options.highlight.label,
        };
      }
    }

    // Take screenshot
    await this.page.screenshot({ path: screenshotPath });

    // Record step in manifest
    const manifestStep: ManifestStep = {
      step: this.stepCounter,
      name,
      title: options.title,
      description: options.description,
      screenshot: screenshotFilename,
      timestamp_ms: Date.now(),
      format,
    };

    if (highlightCoords) {
      manifestStep.highlight = highlightCoords;
    }

    this.manifest.steps.push(manifestStep);
  }

  writeManifest(): void {
    const manifestPath = resolve(this.outputDir, 'manifest.json');
    writeFileSync(manifestPath, JSON.stringify(this.manifest, null, 2) + '\n');
  }
}

// ---------------------------------------------------------------------------
// Derive tutorial name from test file
// ---------------------------------------------------------------------------

/**
 * Extracts the tutorial name from a spec filename.
 * e.g. "tutorial-01-hello-workflow.spec.ts" -> "tutorial-01"
 */
function deriveTutorialName(testFilePath: string): string {
  const filename = basename(testFilePath);
  // Match "tutorial-NN" prefix from the filename
  const match = filename.match(/^(tutorial-\d+)/);
  if (match) {
    return match[1];
  }
  // Fallback: use filename without extension
  return filename.replace(/\.spec\.ts$/, '');
}

// ---------------------------------------------------------------------------
// Fixture types
// ---------------------------------------------------------------------------

type CaptureFixtures = {
  capture: CaptureHelper;
};

// ---------------------------------------------------------------------------
// Captures base directory
// ---------------------------------------------------------------------------

const CAPTURES_DIR = resolve(import.meta.dirname, '..', '.captures');

// ---------------------------------------------------------------------------
// Fixture implementation
// ---------------------------------------------------------------------------

export const test = base.extend<CaptureFixtures>({
  capture: async ({ page }, use, testInfo) => {
    const tutorialName = deriveTutorialName(testInfo.file);
    const outputDir = resolve(CAPTURES_DIR, tutorialName);

    const helper = new CaptureHelper(page, outputDir, tutorialName);

    // Hand the capture helper to the test
    await use(helper);

    // Teardown: write the manifest
    helper.writeManifest();
  },
});

export { expect };
