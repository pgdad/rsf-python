---
phase: quick-5
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: ["QUICK-5"]
must_haves:
  truths:
    - "Annotated tag v3.4 exists in local repository at HEAD of master"
    - "Tag v3.4 is pushed to origin (github.com/pgdad/rsf-python)"
    - "Master branch is pushed to origin and up to date"
    - "Tag message describes the release content"
  artifacts: []
  key_links:
    - from: "local tag v3.4"
      to: "origin refs/tags/v3.4"
      via: "git push origin v3.4"
      pattern: "v3\\.4"
    - from: "local master"
      to: "origin/master"
      via: "git push origin master"
      pattern: "master"
---

<objective>
Create an annotated v3.4 minor release tag at HEAD of master and push both the master branch and tag to GitHub for release creation.

Purpose: Mark the post-v3.3 bug fixes (init/generate/deploy workflow, examples, tutorials) with a proper release tag and ensure master branch is synced to origin.
Output: Tag v3.4 and updated master branch on origin.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Existing tag convention (annotated tags with milestone/release names):
- v3.0: "v3.0 Pluggable Infrastructure Providers"
- v3.1: "v3.1: Switch license to MIT"
- v3.2: "v3.2: Terraform Registry Modules Tutorial"
- v3.3: "v3.3 -- WebSocket fix for rsf ui"

Current state:
- Latest tag: v3.3 (7 commits behind HEAD)
- Next version: v3.4
- Branch: master (current)
- Remote: origin -> git@github.com:pgdad/rsf-python.git
- master is ahead of origin/master by multiple commits

Commits since v3.3 (the content of this release):
- fix: rsf init + generate + deploy end-to-end workflow
- fix: update init help text to reference src/handlers/ path
- fix(quick-4): remove invalid Handler field from templates, fix rsf test path resolution
- fix(quick-4): remove duplicate src/handlers/ from 6 examples, update tutorial paths
- fix(quick-4): cache loaded handlers and prefer handlers/ over src/handlers/
- docs(quick-4): complete fix-examples-and-tutorials plan
- docs(quick-4): ensure all examples and tutorials work

Version is dynamic (hatch-vcs from git tags) -- no version file to update manually.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create annotated v3.4 tag, push master branch and tag to GitHub</name>
  <files></files>
  <action>
1. Verify no uncommitted source changes that should be included:
   ```
   git status
   ```
   Planning docs in .planning/ and .hypothesis/ are fine to leave uncommitted. Only warn if src/, tests/, or examples/ have uncommitted changes.

2. Create an annotated tag following the established convention (use the "v{version}: {description}" format from v3.1/v3.2):
   ```
   git tag -a v3.4 -m "v3.4: Fix init/generate/deploy workflow and all examples"
   ```

3. Push the master branch to origin (it is ahead of remote):
   ```
   git push origin master
   ```

4. Push the tag to origin:
   ```
   git push origin v3.4
   ```

5. Verify both the branch and tag exist on the remote:
   ```
   git ls-remote --tags origin v3.4
   git log origin/master --oneline -1
   ```
  </action>
  <verify>
    <automated>git tag -l v3.4 && git ls-remote --tags origin v3.4 | grep -q v3.4 && git fetch origin master && git diff master origin/master --stat | wc -l | grep -q "^0$" && echo "PASS: v3.4 tag and master branch pushed to origin"</automated>
  </verify>
  <done>Annotated tag v3.4 exists locally and on origin with descriptive message. Master branch is pushed and up to date with origin/master.</done>
</task>

</tasks>

<verification>
- `git tag -l v3.4` shows the tag exists locally
- `git show v3.4` shows annotated tag with correct message and points to HEAD
- `git ls-remote --tags origin v3.4` confirms tag is on GitHub
- `git log origin/master --oneline -1` matches local master HEAD
</verification>

<success_criteria>
- Annotated tag v3.4 created at current HEAD of master
- Tag message: "v3.4: Fix init/generate/deploy workflow and all examples"
- Tag pushed to origin (github.com/pgdad/rsf-python)
- Master branch pushed to origin and in sync
</success_criteria>

<output>
After completion, create `.planning/quick/5-tag-minor-version-and-push-master-branch/5-SUMMARY.md`
</output>
