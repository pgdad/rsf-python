---
phase: quick-16
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [QUICK-16]
must_haves:
  truths:
    - "Master branch is pushed to GitHub origin"
    - "Annotated v3.11 tag exists locally and on GitHub"
  artifacts: []
  key_links:
    - from: "local master"
      to: "origin/master"
      via: "git push"
      pattern: "git push origin master"
    - from: "v3.11 tag"
      to: "origin tags"
      via: "git push --tags"
      pattern: "git push origin v3.11"
---

<objective>
Push master branch to GitHub and create annotated v3.11 release tag.

Purpose: Release the scroll bars feature and CI fixes (10 commits since v3.10) as v3.11.
Output: Master pushed, v3.11 tag on GitHub.
</objective>

<execution_context>
@/Users/esa/.claude/get-shit-done/workflows/execute-plan.md
@/Users/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Latest tag: v3.10
Remote: origin (https://github.com/pgdad/rsf-python)
Version is derived from git tags via hatch-vcs — no pyproject.toml update needed.

Commits since v3.10 (10 total):
- feat(quick-14): add custom scroll bars to workflow graph editor
- fix(ci): resolve conftest plugin collision, ruff format, missing test deps
- docs: planning/summary updates for quick-13 through quick-15
</context>

<tasks>

<task type="auto">
  <name>Task 1: Push master and create v3.11 tag</name>
  <files></files>
  <action>
1. Push master branch to GitHub:
   git push origin master

2. Create annotated v3.11 tag with a summary of changes since v3.10:
   git tag -a v3.11 -m "v3.11 - Scroll bars for graph editor + CI fixes

   Changes since v3.10:
   - Add custom scroll bars to workflow graph editor
   - Fix CI: resolve conftest plugin collision
   - Fix CI: run ruff format, add missing test deps (requests, hypothesis)
   - Fix CI: resolve ruff lint violations"

3. Push the tag to GitHub:
   git push origin v3.11

4. Verify the tag exists on the remote:
   git ls-remote --tags origin | grep v3.11
  </action>
  <verify>
    <automated>git ls-remote --tags origin | grep v3.11 && git log --oneline origin/master -1</automated>
  </verify>
  <done>Master branch pushed to GitHub, annotated v3.11 tag exists on origin</done>
</task>

</tasks>

<verification>
- `git ls-remote --tags origin | grep v3.11` shows the tag on remote
- `git log origin/master..master --oneline` shows no unpushed commits
- `git tag -v v3.11 2>&1 | head -5` shows annotated tag message
</verification>

<success_criteria>
- Master branch is up to date on GitHub
- v3.11 annotated tag exists locally and on GitHub remote
</success_criteria>

<output>
After completion, create `.planning/quick/16-push-master-to-github-and-create-v3-11-t/16-SUMMARY.md`
</output>
