---
phase: quick-3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: ["QUICK-3"]
must_haves:
  truths:
    - "Annotated tag v3.2 exists in local repository"
    - "Tag v3.2 is pushed to origin (github.com/pgdad/rsf-python)"
    - "Tag message describes the milestone: Terraform Registry Modules Tutorial"
  artifacts: []
  key_links:
    - from: "local tag v3.2"
      to: "origin refs/tags/v3.2"
      via: "git push origin v3.2"
      pattern: "v3\\.2"
---

<objective>
Create an annotated v3.2 release tag for the "Terraform Registry Modules Tutorial" milestone and push it to GitHub.

Purpose: Mark the v3.2 milestone completion with a proper release tag, following the established tagging convention (annotated tags with milestone description).
Output: Tag v3.2 on origin at the current HEAD of master.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Existing tag convention (annotated tags with milestone names):
- v3.0: "v3.0 Pluggable Infrastructure Providers" (2026-03-02)
- v3.1: "v3.1: Switch license to MIT" (2026-03-03)

Current state:
- Latest tag: v3.1 (64 commits behind HEAD)
- Current milestone: v3.2 — Terraform Registry Modules Tutorial
- Branch: master
- Remote: origin -> git@github.com:pgdad/rsf-python.git
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create annotated v3.2 tag and push to GitHub</name>
  <files></files>
  <action>
1. Verify no uncommitted changes that should be included (git status). If there are staged/unstaged changes to source files (src/, tests/, examples/), warn the user. Planning docs in .planning/ are fine to leave uncommitted.

2. Create an annotated tag following the established convention:
   ```
   git tag -a v3.2 -m "v3.2: Terraform Registry Modules Tutorial"
   ```
   Note: The message format follows v3.1's pattern ("v{version}: {description}").

3. Push the tag to origin:
   ```
   git push origin v3.2
   ```

4. Verify the tag exists on the remote:
   ```
   git ls-remote --tags origin v3.2
   ```
  </action>
  <verify>
    <automated>git tag -l v3.2 && git ls-remote --tags origin v3.2 | grep -q v3.2 && echo "PASS: v3.2 tag exists locally and on remote"</automated>
  </verify>
  <done>Annotated tag v3.2 exists locally and on origin with message "v3.2: Terraform Registry Modules Tutorial"</done>
</task>

</tasks>

<verification>
- `git tag -l v3.2` shows the tag exists locally
- `git show v3.2` shows annotated tag with correct message
- `git ls-remote --tags origin v3.2` confirms tag is on GitHub
</verification>

<success_criteria>
- Annotated tag v3.2 created at current HEAD of master
- Tag message: "v3.2: Terraform Registry Modules Tutorial"
- Tag pushed to origin (github.com/pgdad/rsf-python)
</success_criteria>

<output>
After completion, create `.planning/quick/3-create-minor-release-tag-and-push-to-git/3-SUMMARY.md`
</output>
