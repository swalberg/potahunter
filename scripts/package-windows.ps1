$ErrorActionPreference = "Stop"

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Command,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
  )

  & $Command @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $Command $Arguments"
  }
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
  Invoke-Checked py -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"

Invoke-Checked $python -m pip install -e ".[dev,windows]"
Invoke-Checked $python -m pytest
Invoke-Checked $python -m PyInstaller `
  --name "POTA Spot Hunter" `
  --windowed `
  --onefile `
  --collect-all PySide6 `
  --paths src `
  src\pota_spot_hunter\__main__.py
