$ErrorActionPreference = "Stop"

py -m pip install -e ".[dev,windows]"
py -m pytest
py -m PyInstaller `
  --name "POTA Spot Hunter" `
  --windowed `
  --onefile `
  --collect-all PySide6 `
  -m pota_spot_hunter
