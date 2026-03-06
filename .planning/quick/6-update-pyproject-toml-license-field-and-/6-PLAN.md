---
phase: quick-6
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: [pyproject.toml]
autonomous: true
requirements: [QUICK-6]
must_haves:
  truths:
    - "pyproject.toml license field uses file reference format"
    - "v3.5 annotated tag exists on current HEAD"
    - "master branch and v3.5 tag pushed to GitHub"
  artifacts:
    - path: "pyproject.toml"
      provides: "Updated license field"
      contains: 'license = {file = "LICENSE"}'
  key_links: []
---

<objective>
Update pyproject.toml license field from string format to file reference format, then tag v3.5 release and push to GitHub.

Purpose: Align license metadata with PEP 639 file-reference format and cut a new minor release.
Output: Updated pyproject.toml, v3.5 tag, master branch and tag pushed to origin.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@pyproject.toml
Current state:
- Line 10: `license = "MIT"` (string format, needs to become file reference)
- Latest tag: v3.4
- Next minor release: v3.5
- LICENSE file exists at project root
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update pyproject.toml license field</name>
  <files>pyproject.toml</files>
  <action>
In pyproject.toml, change line 10 from:
```
license = "MIT"
```
to:
```
license = {file = "LICENSE"}
```

This is a single-line edit. Do NOT change any other lines.

After editing, verify the TOML is valid by running:
```bash
python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"
```

Stage and commit with message: `fix: use file reference for license field in pyproject.toml`
  </action>
  <verify>
    <automated>python3 -c "import tomllib; data=tomllib.load(open('pyproject.toml','rb')); assert data['project']['license'] == {'file': 'LICENSE'}, f'Got: {data[\"project\"][\"license\"]}'; print('OK: license field correct')"</automated>
  </verify>
  <done>pyproject.toml license field reads `license = {file = "LICENSE"}` and file parses as valid TOML</done>
</task>

<task type="auto">
  <name>Task 2: Tag v3.5 release and push to GitHub</name>
  <files></files>
  <action>
1. Create an annotated tag for v3.5:
```bash
git tag -a v3.5 -m "v3.5: update license metadata to PEP 639 file reference"
```

2. Push master branch and tag to origin:
```bash
git push origin master
git push origin v3.5
```

3. Verify the tag exists on remote:
```bash
git ls-remote --tags origin v3.5
```
  </action>
  <verify>
    <automated>git tag -l v3.5 --format='%(tag) %(subject)' && git ls-remote --tags origin v3.5</automated>
  </verify>
  <done>v3.5 annotated tag exists locally and on GitHub, master branch pushed</done>
</task>

</tasks>

<verification>
- `python3 -c "import tomllib; data=tomllib.load(open('pyproject.toml','rb')); print(data['project']['license'])"` prints `{'file': 'LICENSE'}`
- `git tag -l v3.5` shows the tag
- `git ls-remote --tags origin v3.5` confirms tag on remote
</verification>

<success_criteria>
- pyproject.toml license field is `license = {file = "LICENSE"}`
- v3.5 annotated release tag created and pushed
- master branch pushed to GitHub
</success_criteria>

<output>
After completion, create `.planning/quick/6-update-pyproject-toml-license-field-and-/6-SUMMARY.md`
</output>
