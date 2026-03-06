---
phase: quick-9
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [QUICK-9]
must_haves:
  truths:
    - "Git tag v3.8 exists as an annotated tag on the current HEAD of master"
    - "Master branch is pushed to origin/master on GitHub"
    - "Tag v3.8 is pushed to origin on GitHub"
  artifacts: []
  key_links:
    - from: "v3.8 tag"
      to: "hatch-vcs"
      via: "git tag drives version in pyproject.toml"
      pattern: "source = .vcs."
---

<objective>
Create annotated git tag v3.8 on the master branch and push both the master branch and the tag to GitHub.

Purpose: Release v3.8 minor version. The project uses hatch-vcs so the version is derived from git tags — creating the tag IS the version bump.
Output: v3.8 tag on GitHub, master branch up to date on GitHub.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
The project uses hatch-vcs for versioning (configured in pyproject.toml). The version is derived from git tags. The last tag is v3.7. The next minor version is v3.8.

Remote: origin -> git@github.com:pgdad/rsf-python.git
Current branch: master
Main branch: main (also exists)

Previous tagging pattern (from v3.7):
- Annotated tag with message format: "v3.8: <brief description>"
- Tags are created on master branch
- Both master branch and tag are pushed to origin
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create v3.8 annotated tag and push master + tag to GitHub</name>
  <files></files>
  <action>
1. Ensure we are on the master branch.
2. Create an annotated git tag v3.8 with message "v3.8: Minor version release" on the current HEAD:
   ```
   git tag -a v3.8 -m "v3.8: Minor version release"
   ```
3. Push the master branch to origin:
   ```
   git push origin master
   ```
4. Push the tag to origin:
   ```
   git push origin v3.8
   ```
5. Verify the tag exists on the remote:
   ```
   git ls-remote --tags origin v3.8
   ```
6. Verify hatch-vcs picks up the new version:
   ```
   python -m hatchling version
   ```
   Expected output should show "3.8" or "3.8.0".
  </action>
  <verify>
    <automated>git tag -l v3.8 && git ls-remote --tags origin v3.8 && python -m hatchling version | grep -q "3.8"</automated>
  </verify>
  <done>
  - Annotated tag v3.8 exists locally and on GitHub
  - Master branch is pushed to origin
  - `python -m hatchling version` reports 3.8.x
  </done>
</task>

</tasks>

<verification>
- `git tag -l v3.8` shows the tag exists locally
- `git ls-remote --tags origin v3.8` shows the tag exists on GitHub
- `git log origin/master --oneline -1` matches local master HEAD
- `python -m hatchling version` outputs a version starting with "3.8"
</verification>

<success_criteria>
- v3.8 annotated tag created and pushed to GitHub
- master branch pushed to GitHub
- hatch-vcs reports version 3.8
</success_criteria>

<output>
After completion, create `.planning/quick/9-create-a-new-minor-version-and-push-mast/9-SUMMARY.md`
</output>
