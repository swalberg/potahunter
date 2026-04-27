$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  py -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"

& $python -m pip install -e ".[dev,windows]"
& $python -m pytest
& $python -m PyInstaller `
  --name "POTA Spot Hunter" `
  --windowed `
  --onefile `
  --collect-all PySide6 `
  --paths src `
  src\pota_spot_hunter\__main__.py
