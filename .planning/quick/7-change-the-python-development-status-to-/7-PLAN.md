---
phase: quick-7
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: [pyproject.toml]
autonomous: true
requirements: [quick-7]
must_haves:
  truths:
    - "pyproject.toml Development Status classifier reads '5 - Production/Stable'"
    - "A new v3.7 annotated git tag exists on the latest master commit"
    - "Master branch and v3.7 tag are pushed to GitHub origin"
  artifacts:
    - path: "pyproject.toml"
      provides: "Updated development status classifier"
      contains: "Development Status :: 5 - Production/Stable"
  key_links:
    - from: "pyproject.toml"
      to: "git tag v3.7"
      via: "hatch-vcs derives version from tag"
      pattern: "source = \"vcs\""
---

<objective>
Change the Python Development Status classifier from "4 - Beta" to "5 - Production/Stable" in pyproject.toml, create an annotated v3.7 release tag, and push both master branch and the tag to GitHub.

Purpose: Reflect the project's maturity after 151 plans across 12 milestones (v1.0 through v3.6), and publish a new minor release.
Output: Updated pyproject.toml committed, v3.7 tag created, master + tag pushed to origin.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@pyproject.toml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update Development Status classifier to Stable</name>
  <files>pyproject.toml</files>
  <action>
    In pyproject.toml, change the classifiers entry from:
      "Development Status :: 4 - Beta"
    to:
      "Development Status :: 5 - Production/Stable"

    No other changes to the file. Commit the change with message:
    "chore: update development status to Production/Stable"
  </action>
  <verify>
    <automated>grep -q "Development Status :: 5 - Production/Stable" pyproject.toml && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>pyproject.toml contains "Development Status :: 5 - Production/Stable" and the change is committed</done>
</task>

<task type="auto">
  <name>Task 2: Create v3.7 annotated tag and push to GitHub</name>
  <files></files>
  <action>
    1. Create an annotated tag v3.7 on the current HEAD commit:
       git tag -a v3.7 -m "v3.7: Update development status to Production/Stable"

    2. Push the master branch to origin:
       git push origin master

    3. Push the v3.7 tag to origin:
       git push origin v3.7

    Note: The project uses hatch-vcs for versioning, so the tag determines the package version.
  </action>
  <verify>
    <automated>git tag -l v3.7 | grep -q v3.7 && echo "TAG EXISTS" || echo "TAG MISSING"</automated>
  </verify>
  <done>v3.7 annotated tag exists, master branch pushed to origin, v3.7 tag pushed to origin</done>
</task>

</tasks>

<verification>
- `grep "Development Status :: 5 - Production/Stable" pyproject.toml` returns a match
- `git tag -l v3.7` shows v3.7
- `git log --oneline -1 v3.7` shows the tagged commit
- `git branch -vv` shows master tracking origin/master and up to date
</verification>

<success_criteria>
1. pyproject.toml Development Status is "5 - Production/Stable"
2. Annotated tag v3.7 exists on master HEAD
3. Master branch and v3.7 tag are pushed to GitHub
</success_criteria>

<output>
After completion, create `.planning/quick/7-change-the-python-development-status-to-/7-SUMMARY.md`
</output>
