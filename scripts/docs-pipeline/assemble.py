#!/usr/bin/env python3
"""assemble.py — Assemble tutorial documentation from captures and manifests.

Reads manifest.json from each tutorial's .captures/ directory,
copies annotated screenshots (or raw if no annotated/ subdir) to docs/tutorials/assets/,
copies GIF and MP4 files, and renders Jinja2 templates to produce markdown files.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
except ImportError:
    print("ERROR: jinja2 not found. Install with: pip install jinja2")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = (SCRIPT_DIR / "../..").resolve()
CAPTURES_DIR = REPO_ROOT / "tests/ui-tutorials/.captures"
DOCS_TUTORIALS_DIR = REPO_ROOT / "docs/tutorials"
ASSETS_DIR = DOCS_TUTORIALS_DIR / "assets"
TEMPLATES_DIR = SCRIPT_DIR / "templates"

# ---------------------------------------------------------------------------
# Tutorial metadata (authoritative list — order matters for prev/next nav)
# ---------------------------------------------------------------------------
TUTORIAL_METADATA: list[dict] = [
    {
        "id": "tutorial-00",
        "slug": "tutorial-00-smoke",
        "title": "Smoke Test — Capture Fixture",
        "difficulty": "Beginner",
        "time": "5 min",
        "description": "Verify the capture fixture works end-to-end.",
    },
    {
        "id": "tutorial-01",
        "slug": "tutorial-01-hello-workflow",
        "title": "Tutorial 1: Hello Workflow",
        "difficulty": "Beginner",
        "time": "10 min",
        "description": "Build your first RSF workflow with Task and Succeed states.",
    },
    {
        "id": "tutorial-02",
        "slug": "tutorial-02-branching-logic",
        "title": "Tutorial 2: Branching Logic",
        "difficulty": "Beginner",
        "time": "15 min",
        "description": "Add Choice states to route workflow execution based on conditions.",
    },
    {
        "id": "tutorial-03",
        "slug": "tutorial-03-wait-and-retry",
        "title": "Tutorial 3: Wait & Retry",
        "difficulty": "Intermediate",
        "time": "20 min",
        "description": "Use Wait states and retry policies for resilient workflows.",
    },
    {
        "id": "tutorial-04",
        "slug": "tutorial-04-parallel-processing",
        "title": "Tutorial 4: Parallel Processing",
        "difficulty": "Intermediate",
        "time": "20 min",
        "description": "Run multiple workflow branches concurrently with Parallel states.",
    },
    {
        "id": "tutorial-05",
        "slug": "tutorial-05-order-processing",
        "title": "Tutorial 5: Order Processing",
        "difficulty": "Advanced",
        "time": "30 min",
        "description": "Build a complete order processing pipeline as a full example.",
    },
]


def load_manifest(tutorial_dir: Path) -> dict | None:
    """Load manifest.json from a tutorial captures directory."""
    manifest_path = tutorial_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    with open(manifest_path) as f:
        return json.load(f)


def copy_asset(src: Path, dst_dir: Path) -> str:
    """Copy a file to dst_dir, returning the filename."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
        print(f"  Copied: {src.name}")
    else:
        print(f"  [skip] Up-to-date: {src.name}")
    return src.name


def resolve_screenshot(tutorial_dir: Path, screenshot_name: str) -> tuple[Path | None, str | None]:
    """Return (source_path, asset_name) for a screenshot, preferring annotated/."""
    annotated = tutorial_dir / "annotated" / screenshot_name
    raw = tutorial_dir / screenshot_name
    if annotated.exists():
        return annotated, screenshot_name
    if raw.exists():
        return raw, screenshot_name
    return None, None


def process_tutorial(
    meta: dict,
    prev_meta: dict | None,
    next_meta: dict | None,
    env: Environment,
) -> bool:
    """Process a single tutorial: copy assets and render markdown."""
    tutorial_id = meta["id"]
    tutorial_dir = CAPTURES_DIR / tutorial_id

    print(f"\nProcessing {tutorial_id}...")

    manifest = load_manifest(tutorial_dir)
    if manifest is None:
        print(f"  [skip] No manifest.json found in {tutorial_dir}")
        return False

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Build step data with resolved asset paths
    steps_data = []
    for step in manifest.get("steps", []):
        screenshot_name = step.get("screenshot")
        annotated_screenshot = None

        if screenshot_name:
            src, asset_name = resolve_screenshot(tutorial_dir, screenshot_name)
            if src:
                copy_asset(src, ASSETS_DIR)
                # Track whether this is annotated for template
                annotated_path = tutorial_dir / "annotated" / screenshot_name
                annotated_screenshot = screenshot_name if annotated_path.exists() else None
            else:
                print(f"  [warn] Screenshot not found: {screenshot_name}")

        step_data = dict(step)
        step_data["annotated_screenshot"] = annotated_screenshot
        steps_data.append(step_data)

    # Copy GIF if present
    gif_file = None
    gif_src = tutorial_dir / "demo.gif"
    if gif_src.exists():
        gif_file = copy_asset(gif_src, ASSETS_DIR)

    # Copy MP4 if present
    video_file = None
    mp4_src = tutorial_dir / "video.mp4"
    if mp4_src.exists():
        video_file = copy_asset(mp4_src, ASSETS_DIR)

    # Render tutorial markdown
    template = env.get_template("tutorial.md.j2")
    rendered = template.render(
        tutorial=meta,
        steps=steps_data,
        gif_file=gif_file,
        video_file=video_file,
        prev_tutorial=prev_meta,
        next_tutorial=next_meta,
    )

    out_path = DOCS_TUTORIALS_DIR / f"{meta['slug']}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered)
    print(f"  Written: {out_path.relative_to(REPO_ROOT)}")
    return True


def main() -> None:
    print(f"Assembling tutorial docs...")
    print(f"Captures: {CAPTURES_DIR}")
    print(f"Output:   {DOCS_TUTORIALS_DIR}")

    if not CAPTURES_DIR.exists():
        print(f"ERROR: Captures directory not found: {CAPTURES_DIR}")
        sys.exit(1)

    if not TEMPLATES_DIR.exists():
        print(f"ERROR: Templates directory not found: {TEMPLATES_DIR}")
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    DOCS_TUTORIALS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    processed = []
    for i, meta in enumerate(TUTORIAL_METADATA):
        prev_meta = TUTORIAL_METADATA[i - 1] if i > 0 else None
        next_meta = TUTORIAL_METADATA[i + 1] if i + 1 < len(TUTORIAL_METADATA) else None
        ok = process_tutorial(meta, prev_meta, next_meta, env)
        if ok:
            processed.append(meta)

    # Render index page
    print("\nRendering index page...")
    index_template = env.get_template("index.md.j2")
    index_rendered = index_template.render(tutorials=TUTORIAL_METADATA)
    index_path = DOCS_TUTORIALS_DIR / "index.md"
    index_path.write_text(index_rendered)
    print(f"  Written: {index_path.relative_to(REPO_ROOT)}")

    print(f"\nAssembly complete: {len(processed)}/{len(TUTORIAL_METADATA)} tutorials processed.")
    print(f"Assets in:    {ASSETS_DIR}")
    print(f"Docs in:      {DOCS_TUTORIALS_DIR}")


if __name__ == "__main__":
    main()
