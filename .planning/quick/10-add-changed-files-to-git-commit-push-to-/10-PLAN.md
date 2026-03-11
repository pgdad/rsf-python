---
phase: quick-10
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - .gitignore
  - .planning/config.json
  - .planning/quick/1-add-mit-license-to-this-project-and-push/1-PLAN.md
  - .planning/quick/2-continue-fixing-all-integration-tests-ba/2-PLAN.md
  - src/rsf/editor/static/index.html
  - src/rsf/editor/static/assets/index-BigKWUMt.js
  - src/rsf/editor/static/assets/index-By6Nq0QI.css
  - src/rsf/editor/static/assets/index-C5MJELYK.js
  - src/rsf/editor/static/assets/index-CqmWznkt.css
  - src/rsf/editor/static/assets/index-DMXAHBQe.css
  - src/rsf/editor/static/assets/index-EtoV4m1B.js
  - vscode-extension/package-lock.json
autonomous: true
requirements: []
must_haves:
  truths:
    - "All meaningful changed files are committed to master"
    - "master branch is pushed to GitHub"
    - "A v3.9 annotated tag exists and is pushed to GitHub"
  artifacts: []
  key_links: []
---

<objective>
Stage and commit all meaningful changed files, push master to GitHub, create v3.9 tag, and push the tag.

Purpose: Ship current editor static asset updates and planning files as a new minor release.
Output: Clean working tree on master, pushed to GitHub, with v3.9 tag.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update .gitignore and stage all meaningful changes</name>
  <files>.gitignore</files>
  <action>
    1. Add the following entries to .gitignore (they are currently missing):
       - `.hypothesis/`
       - `node_modules/`
    2. Stage the following files for commit:
       - `.gitignore` (newly updated)
       - `.planning/config.json` (modified)
       - `.planning/quick/1-add-mit-license-to-this-project-and-push/1-PLAN.md` (new, untracked planning artifact)
       - `.planning/quick/2-continue-fixing-all-integration-tests-ba/2-PLAN.md` (new, untracked planning artifact)
       - `src/rsf/editor/static/index.html` (modified)
       - `src/rsf/editor/static/assets/index-BigKWUMt.js` (new bundled asset)
       - `src/rsf/editor/static/assets/index-By6Nq0QI.css` (new bundled asset)
       - `src/rsf/editor/static/assets/index-C5MJELYK.js` (deleted old asset)
       - `src/rsf/editor/static/assets/index-CqmWznkt.css` (deleted old asset)
       - `src/rsf/editor/static/assets/index-DMXAHBQe.css` (deleted old asset)
       - `src/rsf/editor/static/assets/index-EtoV4m1B.js` (deleted old asset)
       - `vscode-extension/package-lock.json` (new)
    3. Do NOT stage: `.hypothesis/`, `vscode-extension/node_modules/`, `examples/registry-modules-demo/rsf.toml.bak`
    4. Commit with message: "chore: update editor static assets, gitignore, and planning files"
  </action>
  <verify>
    <automated>git status --short | grep -v '??' | wc -l</automated>
  </verify>
  <done>All meaningful files committed. Working tree has no modified/deleted tracked files. Only truly ignorable untracked items remain (.hypothesis/, rsf.toml.bak).</done>
</task>

<task type="auto">
  <name>Task 2: Push master and create v3.9 tag</name>
  <files></files>
  <action>
    1. Push master branch to GitHub: `git push origin master`
    2. Create annotated tag: `git tag -a v3.9 -m "v3.9 release"`
    3. Push the tag: `git push origin v3.9`

    The latest existing tag is v3.8, so the next minor version is v3.9.
  </action>
  <verify>
    <automated>git tag --sort=-v:refname | head -1 | grep "v3.9" && git ls-remote --tags origin | grep "v3.9"</automated>
  </verify>
  <done>master branch pushed to GitHub. v3.9 annotated tag exists locally and on GitHub remote.</done>
</task>

</tasks>

<verification>
- `git log --oneline -1` shows the commit with editor static assets
- `git tag --sort=-v:refname | head -1` returns `v3.9`
- `git status` shows a clean working tree (only untracked ignorable files)
- `git ls-remote --tags origin | grep v3.9` confirms tag is on remote
</verification>

<success_criteria>
- All changed files (editor assets, planning files, config, package-lock) committed
- .gitignore updated with .hypothesis/ and node_modules/
- master pushed to GitHub
- v3.9 annotated tag created and pushed to GitHub
</success_criteria>

<output>
After completion, create `.planning/quick/10-add-changed-files-to-git-commit-push-to-/10-SUMMARY.md`
</output>
