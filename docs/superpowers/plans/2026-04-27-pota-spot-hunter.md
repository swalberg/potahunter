# POTA Spot Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-focused Python desktop app that lists current POTA spots, row-click tunes OmniRig, sends WSJT-X-compatible UDP logger updates, and hides worked or temporarily ignored spots.

**Architecture:** Use a small PySide6 desktop shell around testable core modules. Keep POTA fetching, suppression state, rig control, settings, and logger UDP as separate units with fake implementations available on macOS and tests. The Windows-only OmniRig COM code lives behind the same `RigController` interface used by the fake controller.

**Tech Stack:** Python 3.11+, PySide6, httpx, platformdirs, pywin32 on Windows, pytest, pytest-qt, PyInstaller.

---

## File Structure

- `pyproject.toml`: package metadata, runtime dependencies, dev dependencies, pytest configuration, console entry point.
- `README.md`: setup, run, test, Windows integration, and packaging notes.
- `src/pota_spot_hunter/__init__.py`: package marker and version.
- `src/pota_spot_hunter/__main__.py`: `python -m pota_spot_hunter` entry point.
- `src/pota_spot_hunter/domain.py`: `Spot`, `SpotKey`, and small domain helpers.
- `src/pota_spot_hunter/bands.py`: frequency-to-band conversion.
- `src/pota_spot_hunter/spot_state.py`: in-memory worked and can't-hear suppression rules.
- `src/pota_spot_hunter/settings.py`: app settings dataclass, validation, JSON persistence.
- `src/pota_spot_hunter/spot_source.py`: POTA spot fetcher and JSON normalization.
- `src/pota_spot_hunter/rig.py`: `RigController`, `FakeRigController`, and `OmniRigController`.
- `src/pota_spot_hunter/logger_udp.py`: WSJT-X-compatible UDP framing and sender.
- `src/pota_spot_hunter/gui.py`: PySide6 main window and settings dialog.
- `src/pota_spot_hunter/app.py`: object wiring and application startup.
- `tests/`: focused pytest suite matching the modules above.

---

### Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/pota_spot_hunter/__init__.py`
- Create: `src/pota_spot_hunter/__main__.py`
- Create: `src/pota_spot_hunter/app.py`
- Create: `tests/test_imports.py`

- [ ] **Step 1: Add packaging and dependency metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "pota-spot-hunter"
version = "0.1.0"
description = "Desktop helper for hunting Parks on the Air spots"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "httpx>=0.27",
  "platformdirs>=4.2",
  "PySide6>=6.7",
]

[project.optional-dependencies]
windows = ["pywin32>=306; platform_system == 'Windows'"]
dev = [
  "pytest>=8.2",
  "pytest-qt>=4.4",
  "pyinstaller>=6.8",
]

[project.scripts]
pota-spot-hunter = "pota_spot_hunter.app:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Add basic README**

Create `README.md`:

```markdown
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
```

- [ ] **Step 3: Add minimal app entry points**

Create `src/pota_spot_hunter/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/pota_spot_hunter/__main__.py`:

```python
from .app import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Create `src/pota_spot_hunter/app.py`:

```python
def main() -> int:
    print("POTA Spot Hunter is not wired yet.")
    return 0
```

- [ ] **Step 4: Add import smoke test**

Create `tests/test_imports.py`:

```python
from pota_spot_hunter import __version__
from pota_spot_hunter.app import main


def test_package_imports():
    assert __version__ == "0.1.0"
    assert main() == 0
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_imports.py -v`

Expected: one passing test.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md src tests
git commit -m "chore: scaffold python app"
```

---

### Task 2: Domain Model and Band Conversion

**Files:**
- Create: `src/pota_spot_hunter/domain.py`
- Create: `src/pota_spot_hunter/bands.py`
- Create: `tests/test_domain.py`
- Create: `tests/test_bands.py`

- [ ] **Step 1: Write domain tests**

Create `tests/test_domain.py`:

```python
from pota_spot_hunter.domain import Spot


def test_spot_key_uses_activator_park_band_and_mode():
    spot = Spot(
        activator=" k1abc ",
        park=" us-1234 ",
        frequency_khz=14244.0,
        mode=" ssb ",
        spotter="W1XYZ",
        comments="57 into CT",
    )

    assert spot.activator == "K1ABC"
    assert spot.park == "US-1234"
    assert spot.mode == "SSB"
    assert spot.band == "20m"
    assert spot.key.activator == "K1ABC"
    assert spot.key.park == "US-1234"
    assert spot.key.band == "20m"
    assert spot.key.mode == "SSB"
```

Create `tests/test_bands.py`:

```python
import pytest

from pota_spot_hunter.bands import band_for_frequency_khz


@pytest.mark.parametrize(
    ("frequency_khz", "band"),
    [
        (1810.0, "160m"),
        (3560.0, "80m"),
        (7040.0, "40m"),
        (10136.0, "30m"),
        (14074.0, "20m"),
        (18100.0, "17m"),
        (21074.0, "15m"),
        (24915.0, "12m"),
        (28074.0, "10m"),
        (50313.0, "6m"),
    ],
)
def test_band_for_frequency(frequency_khz, band):
    assert band_for_frequency_khz(frequency_khz) == band


def test_band_for_unknown_frequency():
    assert band_for_frequency_khz(999999.0) == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_domain.py tests/test_bands.py -v`

Expected: import errors for missing modules.

- [ ] **Step 3: Implement band conversion**

Create `src/pota_spot_hunter/bands.py`:

```python
BANDS_KHZ = [
    ("160m", 1800.0, 2000.0),
    ("80m", 3500.0, 4000.0),
    ("60m", 5330.0, 5407.0),
    ("40m", 7000.0, 7300.0),
    ("30m", 10100.0, 10150.0),
    ("20m", 14000.0, 14350.0),
    ("17m", 18068.0, 18168.0),
    ("15m", 21000.0, 21450.0),
    ("12m", 24890.0, 24990.0),
    ("10m", 28000.0, 29700.0),
    ("6m", 50000.0, 54000.0),
]


def band_for_frequency_khz(frequency_khz: float) -> str:
    for band, low, high in BANDS_KHZ:
        if low <= frequency_khz <= high:
            return band
    return "unknown"
```

- [ ] **Step 4: Implement domain model**

Create `src/pota_spot_hunter/domain.py`:

```python
from dataclasses import dataclass, field

from .bands import band_for_frequency_khz


@dataclass(frozen=True)
class SpotKey:
    activator: str
    park: str
    band: str
    mode: str


@dataclass(frozen=True)
class Spot:
    activator: str
    park: str
    frequency_khz: float
    mode: str
    spotter: str = ""
    comments: str = ""
    expires_at: str | None = None
    band: str = field(init=False)
    key: SpotKey = field(init=False)

    def __post_init__(self) -> None:
        activator = self.activator.strip().upper()
        park = self.park.strip().upper()
        mode = self.mode.strip().upper()
        band = band_for_frequency_khz(self.frequency_khz)

        object.__setattr__(self, "activator", activator)
        object.__setattr__(self, "park", park)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "band", band)
        object.__setattr__(
            self,
            "key",
            SpotKey(activator=activator, park=park, band=band, mode=mode),
        )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_domain.py tests/test_bands.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/pota_spot_hunter/domain.py src/pota_spot_hunter/bands.py tests/test_domain.py tests/test_bands.py
git commit -m "feat: add spot domain model"
```

---

### Task 3: In-Memory Spot Suppression

**Files:**
- Create: `src/pota_spot_hunter/spot_state.py`
- Create: `tests/test_spot_state.py`

- [ ] **Step 1: Write suppression tests**

Create `tests/test_spot_state.py`:

```python
from datetime import datetime, timedelta, timezone

from pota_spot_hunter.domain import Spot
from pota_spot_hunter.spot_state import SpotState


NOW = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)


def make_spot(frequency_khz=14244.0, mode="SSB") -> Spot:
    return Spot(
        activator="K1ABC",
        park="US-1234",
        frequency_khz=frequency_khz,
        mode=mode,
        spotter="W1XYZ",
        comments="",
    )


def test_worked_hides_same_band_and_mode():
    state = SpotState(ignore_minutes=15)
    spot = make_spot()

    state.mark_worked(spot)

    assert state.visible_spots([spot], now=NOW) == []


def test_worked_reappears_on_different_band_or_mode():
    state = SpotState(ignore_minutes=15)
    state.mark_worked(make_spot(frequency_khz=14244.0, mode="SSB"))

    assert state.visible_spots([make_spot(frequency_khz=7244.0, mode="SSB")], now=NOW)
    assert state.visible_spots([make_spot(frequency_khz=14244.0, mode="CW")], now=NOW)


def test_cant_hear_expires_after_ignore_window():
    state = SpotState(ignore_minutes=15)
    spot = make_spot()

    state.mark_cant_hear(spot, now=NOW)

    assert state.visible_spots([spot], now=NOW + timedelta(minutes=14)) == []
    assert state.visible_spots([spot], now=NOW + timedelta(minutes=16)) == [spot]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_spot_state.py -v`

Expected: import error for missing `spot_state`.

- [ ] **Step 3: Implement `SpotState`**

Create `src/pota_spot_hunter/spot_state.py`:

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .domain import Spot, SpotKey


@dataclass
class SpotState:
    ignore_minutes: int
    worked: set[SpotKey] = field(default_factory=set)
    cant_hear_until: dict[SpotKey, datetime] = field(default_factory=dict)

    def mark_worked(self, spot: Spot) -> None:
        self.worked.add(spot.key)
        self.cant_hear_until.pop(spot.key, None)

    def mark_cant_hear(self, spot: Spot, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        self.cant_hear_until[spot.key] = current + timedelta(minutes=self.ignore_minutes)

    def visible_spots(self, spots: list[Spot], now: datetime | None = None) -> list[Spot]:
        current = now or datetime.now(timezone.utc)
        self._discard_expired(current)
        return [
            spot
            for spot in spots
            if spot.key not in self.worked and spot.key not in self.cant_hear_until
        ]

    def _discard_expired(self, now: datetime) -> None:
        expired = [
            key
            for key, expires_at in self.cant_hear_until.items()
            if expires_at <= now
        ]
        for key in expired:
            self.cant_hear_until.pop(key, None)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_spot_state.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pota_spot_hunter/spot_state.py tests/test_spot_state.py
git commit -m "feat: add spot suppression state"
```

---

### Task 4: Settings

**Files:**
- Create: `src/pota_spot_hunter/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write settings tests**

Create `tests/test_settings.py`:

```python
import json

import pytest

from pota_spot_hunter.settings import AppSettings, SettingsError, load_settings, save_settings


def test_default_settings():
    settings = AppSettings()

    assert settings.refresh_seconds == 60
    assert settings.ignore_minutes == 15
    assert settings.logger_host == "127.0.0.1"
    assert settings.logger_port == 2237
    assert settings.omnirig_rig_number == 1


def test_rejects_invalid_settings():
    with pytest.raises(SettingsError, match="logger_port"):
        AppSettings(logger_port=70000).validate()

    with pytest.raises(SettingsError, match="ignore_minutes"):
        AppSettings(ignore_minutes=-1).validate()

    with pytest.raises(SettingsError, match="logger_host"):
        AppSettings(logger_host="").validate()


def test_save_and_load_settings(tmp_path):
    path = tmp_path / "settings.json"
    settings = AppSettings(refresh_seconds=30, ignore_minutes=10, logger_port=2240)

    save_settings(settings, path)
    loaded = load_settings(path)

    assert json.loads(path.read_text())["refresh_seconds"] == 30
    assert loaded == settings
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_settings.py -v`

Expected: import error for missing `settings`.

- [ ] **Step 3: Implement settings**

Create `src/pota_spot_hunter/settings.py`:

```python
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from platformdirs import user_config_dir


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class AppSettings:
    refresh_seconds: int = 60
    ignore_minutes: int = 15
    logger_host: str = "127.0.0.1"
    logger_port: int = 2237
    omnirig_rig_number: int = 1

    def validate(self) -> "AppSettings":
        if self.refresh_seconds <= 0:
            raise SettingsError("refresh_seconds must be positive")
        if self.ignore_minutes < 0:
            raise SettingsError("ignore_minutes must be zero or positive")
        if not self.logger_host.strip():
            raise SettingsError("logger_host must not be empty")
        if not 1 <= self.logger_port <= 65535:
            raise SettingsError("logger_port must be between 1 and 65535")
        if self.omnirig_rig_number not in (1, 2):
            raise SettingsError("omnirig_rig_number must be 1 or 2")
        return self


def default_settings_path() -> Path:
    return Path(user_config_dir("POTA Spot Hunter", "pota-spot-hunter")) / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    settings_path = path or default_settings_path()
    if not settings_path.exists():
        return AppSettings()
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    return AppSettings(**data).validate()


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    settings.validate()
    settings_path = path or default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(asdict(settings), indent=2) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_settings.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pota_spot_hunter/settings.py tests/test_settings.py
git commit -m "feat: add app settings"
```

---

### Task 5: POTA Spot Source

**Files:**
- Create: `src/pota_spot_hunter/spot_source.py`
- Create: `tests/test_spot_source.py`

- [ ] **Step 1: Write spot source tests**

Create `tests/test_spot_source.py`:

```python
import pytest

from pota_spot_hunter.spot_source import PotaSpotSource, SpotSourceError, parse_pota_spots


def test_parse_pota_spots_from_api_shape():
    payload = [
        {
            "activator": "K1ABC",
            "reference": "US-1234",
            "frequency": "14.244",
            "mode": "SSB",
            "spotter": "W1XYZ",
            "comments": "57 into CT",
            "expire": "2026-04-27T18:00:00Z",
        }
    ]

    spots = parse_pota_spots(payload)

    assert len(spots) == 1
    assert spots[0].activator == "K1ABC"
    assert spots[0].park == "US-1234"
    assert spots[0].frequency_khz == 14244.0
    assert spots[0].mode == "SSB"
    assert spots[0].spotter == "W1XYZ"
    assert spots[0].comments == "57 into CT"


def test_parse_skips_unusable_spot():
    payload = [{"activator": "K1ABC", "reference": "US-1234", "frequency": "", "mode": "SSB"}]

    assert parse_pota_spots(payload) == []


def test_fetch_wraps_http_errors():
    class BrokenClient:
        def get(self, url):
            raise RuntimeError("network down")

    source = PotaSpotSource(client=BrokenClient())

    with pytest.raises(SpotSourceError, match="network down"):
        source.fetch()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_spot_source.py -v`

Expected: import error for missing `spot_source`.

- [ ] **Step 3: Implement spot source**

Create `src/pota_spot_hunter/spot_source.py`:

```python
from typing import Any

import httpx

from .domain import Spot


POTA_SPOTS_URL = "https://api.pota.app/spot/activator"


class SpotSourceError(RuntimeError):
    pass


class PotaSpotSource:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=10.0)

    def fetch(self) -> list[Spot]:
        try:
            response = self.client.get(POTA_SPOTS_URL)
            response.raise_for_status()
            return parse_pota_spots(response.json())
        except Exception as exc:
            raise SpotSourceError(str(exc)) from exc


def parse_pota_spots(payload: list[dict[str, Any]]) -> list[Spot]:
    spots: list[Spot] = []
    for item in payload:
        try:
            frequency_khz = _frequency_to_khz(item["frequency"])
            spots.append(
                Spot(
                    activator=str(item["activator"]),
                    park=str(item["reference"]),
                    frequency_khz=frequency_khz,
                    mode=str(item["mode"]),
                    spotter=str(item.get("spotter", "")),
                    comments=str(item.get("comments", "")),
                    expires_at=item.get("expire"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return spots


def _frequency_to_khz(value: Any) -> float:
    number = float(value)
    if number < 1000:
        return number * 1000
    return number
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_spot_source.py -v`

Expected: all tests pass.

- [ ] **Step 5: Run live endpoint smoke test**

Run:

```bash
python - <<'PY'
from pota_spot_hunter.spot_source import PotaSpotSource

spots = PotaSpotSource().fetch()
print(len(spots))
print(spots[0] if spots else "no spots")
PY
```

Expected: prints a non-negative spot count. If the count is nonzero, the second line prints a `Spot(...)`.

- [ ] **Step 6: Commit**

```bash
git add src/pota_spot_hunter/spot_source.py tests/test_spot_source.py
git commit -m "feat: fetch pota spots"
```

---

### Task 6: Rig Controller Interface and OmniRig Adapter

**Files:**
- Create: `src/pota_spot_hunter/rig.py`
- Create: `tests/test_rig.py`

- [ ] **Step 1: Write rig tests**

Create `tests/test_rig.py`:

```python
import pytest

from pota_spot_hunter.rig import FakeRigController, OmniRigController, RigCommand


def test_fake_rig_records_tune_commands():
    rig = FakeRigController()

    rig.tune(frequency_khz=14244.0, mode="SSB")

    assert rig.commands == [RigCommand(frequency_khz=14244.0, mode="SSB")]


def test_omnirig_requires_windows_com_dependency(monkeypatch):
    monkeypatch.setattr("pota_spot_hunter.rig.win32com_client", None)

    with pytest.raises(RuntimeError, match="pywin32"):
        OmniRigController(rig_number=1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rig.py -v`

Expected: import error for missing `rig`.

- [ ] **Step 3: Implement rig controllers**

Create `src/pota_spot_hunter/rig.py`:

```python
from dataclasses import dataclass, field
from typing import Protocol

try:
    from win32com import client as win32com_client
except ImportError:
    win32com_client = None


@dataclass(frozen=True)
class RigCommand:
    frequency_khz: float
    mode: str


class RigController(Protocol):
    def tune(self, frequency_khz: float, mode: str) -> None:
        ...


@dataclass
class FakeRigController:
    commands: list[RigCommand] = field(default_factory=list)

    def tune(self, frequency_khz: float, mode: str) -> None:
        self.commands.append(RigCommand(frequency_khz=frequency_khz, mode=mode))


class OmniRigController:
    MODE_MAP = {
        "CW": 1,
        "USB": 2,
        "LSB": 3,
        "SSB": 2,
        "DIGI": 4,
        "FT8": 4,
    }

    def __init__(self, rig_number: int = 1) -> None:
        if win32com_client is None:
            raise RuntimeError("pywin32 is required for OmniRig control on Windows")
        if rig_number not in (1, 2):
            raise ValueError("rig_number must be 1 or 2")
        self.omnirig = win32com_client.Dispatch("OmniRig.OmniRigX")
        self.rig = self.omnirig.Rig1 if rig_number == 1 else self.omnirig.Rig2

    def tune(self, frequency_khz: float, mode: str) -> None:
        self.rig.FreqA = int(frequency_khz * 1000)
        rig_mode = self.MODE_MAP.get(mode.upper())
        if rig_mode is not None:
            self.rig.Mode = rig_mode
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_rig.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pota_spot_hunter/rig.py tests/test_rig.py
git commit -m "feat: add rig controllers"
```

---

### Task 7: WSJT-X-Compatible UDP Logger Client

**Files:**
- Create: `src/pota_spot_hunter/logger_udp.py`
- Create: `tests/test_logger_udp.py`

- [ ] **Step 1: Write UDP packet tests**

Create `tests/test_logger_udp.py`:

```python
from pota_spot_hunter.domain import Spot
from pota_spot_hunter.logger_udp import MAGIC, SCHEMA_VERSION, MESSAGE_TYPE_STATUS, build_status_packet


def test_status_packet_contains_wsjt_x_header_and_spot_details():
    spot = Spot(
        activator="K1ABC",
        park="US-1234",
        frequency_khz=14244.0,
        mode="SSB",
        spotter="W1XYZ",
        comments="57 into CT",
    )

    packet = build_status_packet(spot)

    assert packet[:4] == MAGIC.to_bytes(4, "big")
    assert packet[4:8] == SCHEMA_VERSION.to_bytes(4, "big")
    assert packet[8:12] == MESSAGE_TYPE_STATUS.to_bytes(4, "big")
    assert b"POTA Spot Hunter" in packet
    assert b"K1ABC" in packet
    assert b"US-1234" in packet
    assert b"14.244" in packet
    assert b"SSB" in packet
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_logger_udp.py -v`

Expected: import error for missing `logger_udp`.

- [ ] **Step 3: Implement UDP framing**

Create `src/pota_spot_hunter/logger_udp.py`:

```python
import socket
import struct

from .domain import Spot


MAGIC = 0xADBCCBDA
SCHEMA_VERSION = 2
MESSAGE_TYPE_STATUS = 1
CLIENT_ID = "POTA Spot Hunter"


def build_status_packet(spot: Spot) -> bytes:
    frequency_hz = int(spot.frequency_khz * 1000)
    dial_frequency_hz = frequency_hz
    dx_call = spot.activator
    report = ""
    tx_mode = spot.mode
    de_call = ""
    de_grid = ""
    dx_grid = spot.park

    return b"".join(
        [
            _uint32(MAGIC),
            _uint32(SCHEMA_VERSION),
            _uint32(MESSAGE_TYPE_STATUS),
            _qstring(CLIENT_ID),
            _uint64(dial_frequency_hz),
            _qstring(tx_mode),
            _qstring(dx_call),
            _qstring(report),
            _qstring(tx_mode),
            _bool(False),
            _bool(False),
            _bool(False),
            _uint32(0),
            _qstring(de_call),
            _qstring(de_grid),
            _qstring(dx_grid),
            _bool(False),
            _qstring(f"{spot.frequency_khz / 1000:.3f} {spot.mode} {spot.park}"),
        ]
    )


class LoggerClient:
    def __init__(self, host: str, port: int) -> None:
        self.address = (host, port)

    def send_spot(self, spot: Spot) -> None:
        packet = build_status_packet(spot)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(packet, self.address)


def _uint32(value: int) -> bytes:
    return struct.pack(">I", value)


def _uint64(value: int) -> bytes:
    return struct.pack(">Q", value)


def _bool(value: bool) -> bytes:
    return b"\x01" if value else b"\x00"


def _qstring(value: str | None) -> bytes:
    if value is None:
        return struct.pack(">i", -1)
    encoded = value.encode("utf-8")
    return struct.pack(">I", len(encoded)) + encoded
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_logger_udp.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pota_spot_hunter/logger_udp.py tests/test_logger_udp.py
git commit -m "feat: add logger udp client"
```

---

### Task 8: PySide6 GUI With Fake Integrations

**Files:**
- Create: `src/pota_spot_hunter/gui.py`
- Modify: `src/pota_spot_hunter/app.py`
- Create: `tests/test_gui.py`

- [ ] **Step 1: Write GUI action test**

Create `tests/test_gui.py`:

```python
from pota_spot_hunter.domain import Spot
from pota_spot_hunter.gui import MainWindow
from pota_spot_hunter.rig import FakeRigController
from pota_spot_hunter.spot_state import SpotState


class FakeLogger:
    def __init__(self):
        self.sent = []

    def send_spot(self, spot):
        self.sent.append(spot)


def test_row_click_tunes_and_sends_logger_update(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB", "W1XYZ", "57")
    rig = FakeRigController()
    logger = FakeLogger()
    window = MainWindow(
        spots=[spot],
        state=SpotState(ignore_minutes=15),
        rig=rig,
        logger=logger,
    )
    qtbot.addWidget(window)

    window.handle_row_activated(0)

    assert rig.commands[0].frequency_khz == 14244.0
    assert logger.sent == [spot]
    assert "K1ABC" in window.status_label.text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gui.py -v`

Expected: import error for missing `gui`.

- [ ] **Step 3: Implement GUI**

Create `src/pota_spot_hunter/gui.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .domain import Spot
from .rig import RigController
from .spot_state import SpotState


class MainWindow(QMainWindow):
    HEADERS = ["Call", "Freq", "Band", "Mode", "Park", "Comments", "After Trying"]

    def __init__(self, spots: list[Spot], state: SpotState, rig: RigController, logger) -> None:
        super().__init__()
        self.setWindowTitle("POTA Spot Hunter")
        self.all_spots = spots
        self.visible_spots = spots
        self.state = state
        self.rig = rig
        self.logger = logger

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(lambda row, column: self.handle_row_activated(row))

        self.status_label = QLabel("Ready")

        root = QWidget()
        layout = QVBoxLayout(root)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QPushButton("Refresh"))
        toolbar.addWidget(QPushButton("Settings"))
        toolbar.addStretch()
        layout.addLayout(toolbar)
        layout.addWidget(self.table)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

        self.setStyleSheet(
            """
            QHeaderView::section {
                background: #eef2f7;
                color: #111827;
                font-weight: 600;
                padding: 6px;
            }
            QTableWidget::item:selected {
                background: #dbeafe;
                color: #111827;
            }
            """
        )
        self.render_spots()

    def render_spots(self) -> None:
        self.visible_spots = self.state.visible_spots(self.all_spots)
        self.table.setRowCount(len(self.visible_spots))
        for row, spot in enumerate(self.visible_spots):
            values = [
                spot.activator,
                f"{spot.frequency_khz / 1000:.3f}",
                spot.band,
                spot.mode,
                spot.park,
                spot.comments,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)

            worked_button = QPushButton("Worked")
            worked_button.clicked.connect(lambda checked=False, s=spot: self.mark_worked(s))
            cant_hear_button = QPushButton("Can't Hear")
            cant_hear_button.clicked.connect(lambda checked=False, s=spot: self.mark_cant_hear(s))
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.addWidget(worked_button)
            action_layout.addWidget(cant_hear_button)
            self.table.setCellWidget(row, 6, actions)
        self.table.resizeColumnsToContents()

    def handle_row_activated(self, row: int) -> None:
        if row < 0 or row >= len(self.visible_spots):
            return
        spot = self.visible_spots[row]
        try:
            self.rig.tune(spot.frequency_khz, spot.mode)
            self.logger.send_spot(spot)
        except Exception as exc:
            self.status_label.setText(f"{spot.activator}: {exc}")
            return
        self.table.selectRow(row)
        self.status_label.setText(
            f"{spot.activator} {spot.park} on {spot.frequency_khz / 1000:.3f} {spot.mode} selected"
        )

    def mark_worked(self, spot: Spot) -> None:
        self.state.mark_worked(spot)
        self.status_label.setText(f"{spot.activator} marked worked")
        self.render_spots()

    def mark_cant_hear(self, spot: Spot) -> None:
        self.state.mark_cant_hear(spot)
        self.status_label.setText(f"{spot.activator} ignored temporarily")
        self.render_spots()
```

- [ ] **Step 4: Wire app entry point to fake GUI**

Replace `src/pota_spot_hunter/app.py` with:

```python
import sys

from PySide6.QtWidgets import QApplication

from .domain import Spot
from .gui import MainWindow
from .logger_udp import LoggerClient
from .rig import FakeRigController
from .settings import load_settings
from .spot_state import SpotState


def main() -> int:
    settings = load_settings()
    app = QApplication(sys.argv)
    sample_spots = [
        Spot("K1ABC", "US-1234", 14244.0, "SSB", "W1XYZ", "57 into CT"),
        Spot("W9XYZ", "US-9876", 7032.0, "CW", "N0CALL", "CQ POTA"),
    ]
    window = MainWindow(
        spots=sample_spots,
        state=SpotState(ignore_minutes=settings.ignore_minutes),
        rig=FakeRigController(),
        logger=LoggerClient(settings.logger_host, settings.logger_port),
    )
    window.resize(1100, 600)
    window.show()
    return app.exec()
```

- [ ] **Step 5: Run GUI test**

Run: `pytest tests/test_gui.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/pota_spot_hunter/gui.py src/pota_spot_hunter/app.py tests/test_gui.py
git commit -m "feat: add main spots gui"
```

---

### Task 9: Refresh Loop and Real Spot Wiring

**Files:**
- Modify: `src/pota_spot_hunter/gui.py`
- Modify: `src/pota_spot_hunter/app.py`
- Create: `tests/test_app_wiring.py`

- [ ] **Step 1: Add app wiring test**

Create `tests/test_app_wiring.py`:

```python
from pota_spot_hunter.app import choose_rig_controller
from pota_spot_hunter.rig import FakeRigController


def test_choose_rig_controller_uses_fake_when_requested():
    rig = choose_rig_controller(use_fake=True, rig_number=1)

    assert isinstance(rig, FakeRigController)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app_wiring.py -v`

Expected: import error for missing `choose_rig_controller`.

- [ ] **Step 3: Extend GUI for source refresh**

Modify `src/pota_spot_hunter/gui.py` to accept a `spot_source` and timer. Add these imports:

```python
from PySide6.QtCore import QTimer, Qt
```

Change the constructor signature:

```python
def __init__(
    self,
    spots: list[Spot],
    state: SpotState,
    rig: RigController,
    logger,
    spot_source=None,
    refresh_seconds: int = 60,
) -> None:
```

Add these attributes after `self.logger = logger`:

```python
self.spot_source = spot_source
self.refresh_timer = QTimer(self)
self.refresh_timer.timeout.connect(self.refresh_spots)
if self.spot_source is not None:
    self.refresh_timer.start(refresh_seconds * 1000)
```

Connect the `Refresh` button by replacing the toolbar button lines with:

```python
refresh_button = QPushButton("Refresh")
refresh_button.clicked.connect(self.refresh_spots)
toolbar.addWidget(refresh_button)
toolbar.addWidget(QPushButton("Settings"))
```

Add this method:

```python
def refresh_spots(self) -> None:
    if self.spot_source is None:
        self.render_spots()
        return
    try:
        self.all_spots = self.spot_source.fetch()
    except Exception as exc:
        self.status_label.setText(f"POTA refresh failed: {exc}")
        return
    self.status_label.setText(f"Loaded {len(self.all_spots)} POTA spots")
    self.render_spots()
```

- [ ] **Step 4: Wire real app dependencies**

Replace `src/pota_spot_hunter/app.py` with:

```python
import argparse
import sys

from PySide6.QtWidgets import QApplication

from .gui import MainWindow
from .logger_udp import LoggerClient
from .rig import FakeRigController, OmniRigController, RigController
from .settings import load_settings
from .spot_source import PotaSpotSource
from .spot_state import SpotState


def choose_rig_controller(use_fake: bool, rig_number: int) -> RigController:
    if use_fake:
        return FakeRigController()
    return OmniRigController(rig_number=rig_number)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake-rig", action="store_true", help="Use fake rig controller")
    args = parser.parse_args()

    settings = load_settings()
    app = QApplication(sys.argv)
    source = PotaSpotSource()
    window = MainWindow(
        spots=[],
        state=SpotState(ignore_minutes=settings.ignore_minutes),
        rig=choose_rig_controller(args.fake_rig, settings.omnirig_rig_number),
        logger=LoggerClient(settings.logger_host, settings.logger_port),
        spot_source=source,
        refresh_seconds=settings.refresh_seconds,
    )
    window.resize(1100, 600)
    window.show()
    window.refresh_spots()
    return app.exec()
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_app_wiring.py tests/test_gui.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/pota_spot_hunter/gui.py src/pota_spot_hunter/app.py tests/test_app_wiring.py
git commit -m "feat: wire live spot refresh"
```

---

### Task 10: Settings Dialog

**Files:**
- Modify: `src/pota_spot_hunter/gui.py`
- Create: `tests/test_settings_dialog.py`

- [ ] **Step 1: Write settings dialog test**

Create `tests/test_settings_dialog.py`:

```python
from pota_spot_hunter.gui import SettingsDialog
from pota_spot_hunter.settings import AppSettings


def test_settings_dialog_returns_updated_settings(qtbot):
    dialog = SettingsDialog(AppSettings())
    qtbot.addWidget(dialog)

    dialog.refresh_seconds.setValue(30)
    dialog.ignore_minutes.setValue(10)
    dialog.logger_host.setText("192.168.1.50")
    dialog.logger_port.setValue(2240)
    dialog.omnirig_rig_number.setValue(2)

    settings = dialog.to_settings()

    assert settings.refresh_seconds == 30
    assert settings.ignore_minutes == 10
    assert settings.logger_host == "192.168.1.50"
    assert settings.logger_port == 2240
    assert settings.omnirig_rig_number == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings_dialog.py -v`

Expected: import error for missing `SettingsDialog`.

- [ ] **Step 3: Add settings dialog**

Append this class to `src/pota_spot_hunter/gui.py` and add the listed imports:

```python
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QSpinBox, QDialogButtonBox

from .settings import AppSettings
```

```python
class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.setWindowTitle("Settings")

        self.refresh_seconds = QSpinBox()
        self.refresh_seconds.setRange(1, 3600)
        self.refresh_seconds.setValue(settings.refresh_seconds)

        self.ignore_minutes = QSpinBox()
        self.ignore_minutes.setRange(0, 1440)
        self.ignore_minutes.setValue(settings.ignore_minutes)

        self.logger_host = QLineEdit(settings.logger_host)

        self.logger_port = QSpinBox()
        self.logger_port.setRange(1, 65535)
        self.logger_port.setValue(settings.logger_port)

        self.omnirig_rig_number = QSpinBox()
        self.omnirig_rig_number.setRange(1, 2)
        self.omnirig_rig_number.setValue(settings.omnirig_rig_number)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("Refresh seconds", self.refresh_seconds)
        layout.addRow("Ignore minutes", self.ignore_minutes)
        layout.addRow("Logger host", self.logger_host)
        layout.addRow("Logger port", self.logger_port)
        layout.addRow("OmniRig rig number", self.omnirig_rig_number)
        layout.addRow(buttons)

    def to_settings(self) -> AppSettings:
        return AppSettings(
            refresh_seconds=self.refresh_seconds.value(),
            ignore_minutes=self.ignore_minutes.value(),
            logger_host=self.logger_host.text(),
            logger_port=self.logger_port.value(),
            omnirig_rig_number=self.omnirig_rig_number.value(),
        ).validate()
```

- [ ] **Step 4: Wire Settings button**

Modify `MainWindow.__init__` to accept and store `settings` and `settings_path`, then make the Settings button open `SettingsDialog`, save valid settings, update `SpotState.ignore_minutes`, and restart the refresh timer.

Use this implementation shape:

```python
def open_settings(self) -> None:
    dialog = SettingsDialog(self.settings)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    self.settings = dialog.to_settings()
    save_settings(self.settings, self.settings_path)
    self.state.ignore_minutes = self.settings.ignore_minutes
    if self.spot_source is not None:
        self.refresh_timer.start(self.settings.refresh_seconds * 1000)
    self.status_label.setText("Settings saved")
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_settings_dialog.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/pota_spot_hunter/gui.py tests/test_settings_dialog.py
git commit -m "feat: add settings dialog"
```

---

### Task 11: Windows Manual Validation and Packaging

**Files:**
- Modify: `README.md`
- Create: `scripts/package-windows.ps1`

- [ ] **Step 1: Add packaging script**

Create `scripts/package-windows.ps1`:

```powershell
$ErrorActionPreference = "Stop"

py -m pip install -e ".[dev,windows]"
py -m pytest
py -m PyInstaller `
  --name "POTA Spot Hunter" `
  --windowed `
  --onefile `
  --collect-all PySide6 `
  -m pota_spot_hunter
```

- [ ] **Step 2: Update README with manual validation**

Append to `README.md`:

```markdown
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

```powershell
.\scripts\package-windows.ps1
```

The packaged executable is written under `dist`.
```

- [ ] **Step 3: Run local tests**

Run: `pytest -v`

Expected: all tests pass on macOS using fake rig paths.

- [ ] **Step 4: Commit**

```bash
git add README.md scripts/package-windows.ps1
git commit -m "docs: add windows validation and packaging"
```

---

## Self-Review

- Spec coverage: The plan covers all current POTA spots, periodic refresh, row-click tuning, worked suppression, can't-hear suppression, in-memory state, settings, Windows OmniRig, WSJT-X-compatible UDP, GUI contrast, error reporting, and Windows validation.
- Integration risk: The exact Log4OM interpretation of WSJT-X status fields still needs Windows validation. The packet builder is isolated so the field mapping can be adjusted without touching GUI or spot state.
- Platform risk: PySide6 tests may need `QT_QPA_PLATFORM=offscreen` in headless environments. On local macOS desktop runs, pytest-qt should work without that environment variable.
