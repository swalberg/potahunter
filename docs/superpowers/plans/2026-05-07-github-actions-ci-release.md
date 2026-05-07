# GitHub Actions CI and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GitHub Actions workflows for pull request tests and manual Windows executable releases.

**Architecture:** Add two workflow files under `.github/workflows`: one for tests and one for releases. The release workflow reuses `scripts/package-windows.ps1` and publishes `dist/POTA Spot Hunter.exe` to GitHub Releases.

**Tech Stack:** GitHub Actions, Windows hosted runners, Python 3.13, PowerShell, pytest, PyInstaller, GitHub CLI.

---

### Task 1: Pull Request Test Workflow

**Files:**
- Create: `.github/workflows/test.yml`

- [ ] **Step 1: Create test workflow**

```yaml
name: Tests

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  test:
    name: Python tests
    runs-on: windows-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip

      - name: Install dependencies
        run: python -m pip install -e ".[dev,windows]"

      - name: Run tests
        run: python -m pytest -v
```

- [ ] **Step 2: Review workflow trigger and commands**

Confirm the workflow runs on `pull_request` and `push` to `main`, installs `.[dev,windows]`, and runs `python -m pytest -v`.

### Task 2: Manual Release Workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release workflow**

```yaml
name: Release

on:
  workflow_dispatch:
    inputs:
      tag:
        description: "Release tag, for example v0.2.0"
        required: true
        type: string

permissions:
  contents: write

jobs:
  release:
    name: Build and publish Windows release
    runs-on: windows-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip

      - name: Build executable
        shell: pwsh
        run: .\scripts\package-windows.ps1

      - name: Upload workflow artifact
        uses: actions/upload-artifact@v4
        with:
          name: POTA Spot Hunter
          path: dist/POTA Spot Hunter.exe
          if-no-files-found: error

      - name: Create GitHub Release
        shell: pwsh
        env:
          GH_TOKEN: ${{ github.token }}
          RELEASE_TAG: ${{ inputs.tag }}
        run: |
          gh release create $env:RELEASE_TAG `
            "dist/POTA Spot Hunter.exe#POTA Spot Hunter.exe" `
            --target $env:GITHUB_SHA `
            --title $env:RELEASE_TAG `
            --generate-notes
```

- [ ] **Step 2: Review release workflow permissions and asset path**

Confirm `permissions.contents` is `write`, `gh release create` receives the manual tag, and the uploaded asset path matches the packaging script output.

### Task 3: README Maintainer Instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add CI and release notes**

Add this section before `## Packaging on Windows`:

```markdown
## CI and Releases

- Pull requests and pushes to `main` run the test suite on GitHub Actions.
- To cut a release, update `pyproject.toml` with the new version, commit and push it, then run the `Release` workflow with a matching tag such as `v0.2.0`.
- The release workflow builds `dist/POTA Spot Hunter.exe` on Windows and attaches it to the GitHub Release.
```

- [ ] **Step 2: Run local test suite**

Run: `.\.venv\Scripts\pytest.exe -v`

Expected: PASS.

- [ ] **Step 3: Inspect final workflow files**

Run:

```powershell
Get-Content .github\workflows\test.yml
Get-Content .github\workflows\release.yml
```

Expected: files contain the workflow content from Tasks 1 and 2.

- [ ] **Step 4: Commit implementation**

```bash
git add .github/workflows/test.yml .github/workflows/release.yml README.md docs/superpowers/plans/2026-05-07-github-actions-ci-release.md
git commit -m "ci: add test and release workflows"
```
