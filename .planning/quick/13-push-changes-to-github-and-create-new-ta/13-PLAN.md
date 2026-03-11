---
phase: quick-13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements: [QUICK-13]
must_haves:
  truths:
    - "master branch is pushed to GitHub with all commits since v3.9"
    - "v3.10 annotated tag exists and is pushed to GitHub"
    - "hatch-vcs resolves version as 3.10.x from the new tag"
  artifacts: []
  key_links:
    - from: "v3.10 tag"
      to: "hatch-vcs version"
      via: "git tag used by hatch-vcs to derive version"
      pattern: "v3\\.10"
---

<objective>
Push all commits on master to GitHub and create annotated tag v3.10.

Purpose: Release a new minor version covering codebase mapping, rsf doctor fix, and save indicator feature for graph editor UI (8 commits since v3.9).
Output: master pushed, v3.10 tag created and pushed.
</objective>

<execution_context>
@/Users/esa/.claude/get-shit-done/workflows/execute-plan.md
@/Users/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Version is derived from git tags via hatch-vcs (tool.hatch.version source = "vcs").
No pyproject.toml version field to update — the tag IS the version source.
Latest tag: v3.9. Next: v3.10.

Commits since v3.9 (8 total):
- docs(quick-12): add saved/unsaved indicator to rsf ui
- docs(quick-12): complete save indicator and Ctrl+S plan
- chore(quick-12): rebuild static assets with save indicator and Ctrl+S support
- feat(quick-12): add save tracking state and Ctrl+S handler to editor UI
- docs(quick-11): complete fix rsf doctor handlers path plan
- fix(quick-11): fix rsf doctor to check src/handlers/ instead of handlers/
- docs: map existing codebase
- docs(quick-10): complete commit, push, and v3.9 tag plan
</context>

<tasks>

<task type="auto">
  <name>Task 1: Push master and tag v3.10</name>
  <files></files>
  <action>
1. Push master branch to GitHub origin:
   git push origin master

2. Create annotated v3.10 tag with release summary:
   git tag -a v3.10 -m "v3.10: codebase mapping, rsf doctor handlers path fix, graph editor save indicator"

3. Push the tag to GitHub:
   git push origin v3.10

4. Verify the tag resolves correctly for hatch-vcs:
   python -c "from rsf._version import __version__; print(__version__)"
   (Should show 3.10.0 or similar)
  </action>
  <verify>
    <automated>git ls-remote --tags origin | grep v3.10 && git log origin/master --oneline -1</automated>
  </verify>
  <done>master branch pushed to GitHub, v3.10 annotated tag created and pushed, version resolves to 3.10.x</done>
</task>

</tasks>

<verification>
- `git log origin/master --oneline -3` shows latest commits pushed
- `git ls-remote --tags origin | grep v3.10` shows tag on remote
- `python -c "from rsf._version import __version__; print(__version__)"` shows 3.10.x
</verification>

<success_criteria>
master branch and v3.10 tag both exist on GitHub origin remote.
</success_criteria>

<output>
After completion, create `.planning/quick/13-push-changes-to-github-and-create-new-ta/13-SUMMARY.md`
</output>
