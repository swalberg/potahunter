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
