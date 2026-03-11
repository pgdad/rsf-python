---
phase: quick-1
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - LICENSE
  - pyproject.toml
  - README.md
  - .planning/PROJECT.md
autonomous: true
requirements: [LICENSE-CHANGE]

must_haves:
  truths:
    - "LICENSE file contains MIT license text with correct copyright"
    - "pyproject.toml declares MIT license"
    - "README badge and section reflect MIT license"
    - "v3.1 tag exists and is pushed to GitHub"
  artifacts:
    - path: "LICENSE"
      provides: "MIT license text"
      contains: "MIT License"
    - path: "pyproject.toml"
      provides: "Package metadata with MIT license"
      contains: "MIT"
  key_links:
    - from: "git tag v3.1"
      to: "hatch-vcs version"
      via: "setuptools-scm derives version from tag"
      pattern: "v3\\.1"
---

<objective>
Switch project license from Apache-2.0 to MIT, update all references, and push a v3.1 tag to GitHub to create a release.

Purpose: Change the project's open-source license to MIT and cut a new minor release.
Output: MIT LICENSE file, updated metadata, v3.1 tag pushed to origin.
</objective>

<execution_context>
@/home/esa/.claude/get-shit-done/workflows/execute-plan.md
@/home/esa/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
Files to update:
- pyproject.toml line 10: `license = "Apache-2.0"` -> `license = "MIT"`
- pyproject.toml line 18: `"License :: OSI Approved :: Apache Software License"` -> `"License :: OSI Approved :: MIT License"`
- README.md line 5: badge URL references Apache 2.0 -> MIT
- README.md lines 180-182: License section says "Apache-2.0" -> "MIT"
- .planning/PROJECT.md line 140: `**License:** Apache-2.0` -> `**License:** MIT`
- LICENSE file does not exist yet; must be created
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create MIT LICENSE file and update all license references</name>
  <files>LICENSE, pyproject.toml, README.md, .planning/PROJECT.md</files>
  <action>
1. Create LICENSE file at project root with standard MIT License text:
   - Copyright year: 2026
   - Copyright holder: use the git config user name, or "rsf-python contributors" if unavailable

2. Update pyproject.toml:
   - Line 10: change `license = "Apache-2.0"` to `license = "MIT"`
   - Line 18: change `"License :: OSI Approved :: Apache Software License"` to `"License :: OSI Approved :: MIT License"`

3. Update README.md:
   - Line 5: change badge from `[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)` to `[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)`
   - Lines 180-182: change the License section text from "Apache-2.0" to "MIT"

4. Update .planning/PROJECT.md:
   - Change `**License:** Apache-2.0` to `**License:** MIT`

5. Stage all changed files and commit: `chore: switch license from Apache-2.0 to MIT`
  </action>
  <verify>
    <automated>grep -q "MIT License" LICENSE && grep -q 'license = "MIT"' pyproject.toml && grep -q "MIT" README.md && grep -q "MIT" .planning/PROJECT.md && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>LICENSE file exists with MIT text. pyproject.toml, README.md, and PROJECT.md all reference MIT instead of Apache-2.0. Changes committed.</done>
</task>

<task type="auto">
  <name>Task 2: Tag v3.1 and push to GitHub</name>
  <files></files>
  <action>
1. Ensure all changes from Task 1 are committed on master branch.
2. Create annotated tag: `git tag -a v3.1 -m "v3.1: Switch license to MIT"`
3. Push the commit and tag to origin: `git push origin master --tags`
4. Verify the tag is visible on origin.

Note: hatch-vcs derives the package version from git tags, so this tag will automatically set the version to 3.1.
  </action>
  <verify>
    <automated>git tag -l v3.1 | grep -q v3.1 && git ls-remote --tags origin v3.1 | grep -q v3.1 && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>v3.1 tag exists locally and on GitHub origin. Push succeeded.</done>
</task>

</tasks>

<verification>
- LICENSE file contains "MIT License" header
- pyproject.toml license field is "MIT"
- pyproject.toml classifier is "License :: OSI Approved :: MIT License"
- README badge shows MIT
- README License section says MIT
- PROJECT.md says MIT
- git tag v3.1 exists locally and on remote
- `git log --oneline -1` shows license change commit
</verification>

<success_criteria>
Project license is MIT everywhere (LICENSE file, pyproject.toml, README, PROJECT.md). Tag v3.1 is pushed to github.com/pgdad/rsf-python, triggering a release via hatch-vcs versioning.
</success_criteria>

<output>
After completion, create `.planning/quick/1-add-mit-license-to-this-project-and-push/1-SUMMARY.md`
</output>
