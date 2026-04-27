# POTA Spot Hunter

POTA Spot Hunter is a Python desktop app for quickly working Parks on the Air activator spots.

The first version targets Windows station use with OmniRig and WSJT-X-compatible UDP logger updates. The app can still be developed and tested on macOS with a fake rig controller.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m pota_spot_hunter
```

On Windows, install the Windows extra:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,windows]"
pota-spot-hunter
```

## Integrations

- POTA spots are fetched from `https://api.pota.app/spot/activator`.
- OmniRig control is used on Windows through COM.
- Logger updates are sent as WSJT-X-compatible UDP messages. Log4OM is the first validation target.

## Windows Validation

1. Start OmniRig and confirm the target radio is connected.
2. Start Log4OM and enable WSJT-X-compatible UDP reception.
3. Run `pota-spot-hunter`.
4. Click a POTA spot row.
5. Confirm the radio changes to the spot frequency and mode.
6. Confirm Log4OM receives the selected callsign, frequency, mode, and park reference.
7. Click `Worked` and confirm the row disappears.
8. Wait for or simulate a same-activator spot on another band or mode and confirm it can appear again.
9. Click `Can't Hear` and confirm the row disappears until the configured ignore period expires.

## Packaging on Windows

The packaging script creates `.venv` if needed, installs the Windows dependencies into it, runs the tests, and builds a one-file executable.

```powershell
.\scripts\package-windows.ps1
```

The packaged executable is written to `dist\POTA Spot Hunter.exe`.
