# GitHub Actions CI and Release Design

## Goal

Add GitHub Actions workflows so pull requests run the test suite automatically and maintainers can publish a downloadable Windows executable from the GitHub Releases page.

## CI Workflow

Create `.github/workflows/test.yml`.

- Run on pull requests and pushes to `main`.
- Use `windows-latest` because the app is Windows-focused and includes optional Windows dependencies.
- Use Python 3.13 to match the current local development environment.
- Install the project with `.[dev,windows]`.
- Run `python -m pytest -v`.

## Release Workflow

Create `.github/workflows/release.yml`.

- Run manually with `workflow_dispatch`.
- Require a `tag` input such as `v0.2.0`.
- Build on `windows-latest`.
- Install Python 3.13.
- Use the existing `scripts/package-windows.ps1` script as the packaging source of truth.
- Upload `dist/POTA Spot Hunter.exe` as a workflow artifact.
- Create a GitHub Release for the requested tag and attach the executable as a release asset.

The workflow will not bump `pyproject.toml` automatically. The maintainer should update the version, commit it, and then run the release workflow with a matching tag.

## Permissions and Release Notes

The release workflow needs `contents: write` so the default `GITHUB_TOKEN` can create the release and tag. It should use the GitHub CLI already available on hosted runners. Release notes can be generated automatically by GitHub for the chosen tag.

## Documentation

Update `README.md` with short maintainer instructions:

1. Bump `pyproject.toml`.
2. Commit and push.
3. Run the release workflow with the matching tag.
4. Downloaders can use the executable attached to the GitHub Release.

## Testing

Local verification should include:

- Running the full pytest suite.
- Checking workflow YAML files exist in `.github/workflows`.
- Reviewing workflow syntax for trigger, permissions, install, test, package, artifact, and release steps.
