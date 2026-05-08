# Complete QSO From Keyboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators log a selected POTA QSO from POTA Spot Hunter with `Shift+W`, RST fields, and `Enter`.

**Architecture:** Add WSJT-X `Logged ADIF` packet support to `logger_udp.py`, then add a modal completion dialog and `Shift+W` command path to `MainWindow`. Existing `Space`, lowercase `w`, and `n` keyboard behavior stays intact.

**Tech Stack:** Python, PySide6, WSJT-X-compatible UDP framing, ADIF text, pytest, pytest-qt.

---

### Task 1: Logged ADIF Packet Support

**Files:**
- Modify: `src/pota_spot_hunter/logger_udp.py`
- Test: `tests/test_logger_udp.py`

- [ ] **Step 1: Write failing logger UDP tests**

Add imports:

```python
from datetime import datetime, timezone
```

Import new symbols:

```python
    MESSAGE_TYPE_LOGGED_ADIF,
    build_logged_adif,
    build_logged_adif_packet,
```

Add tests:

```python
def test_logged_adif_contains_minimal_qso_fields():
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    logged_at = datetime(2026, 5, 7, 14, 3, 5, tzinfo=timezone.utc)

    adif = build_logged_adif(spot, "57", "44", now=logged_at)

    assert "<CALL:5>K1ABC" in adif
    assert "<QSO_DATE:8>20260507" in adif
    assert "<TIME_ON:6>140305" in adif
    assert "<BAND:3>20M" in adif
    assert "<FREQ:6>14.244" in adif
    assert "<MODE:3>SSB" in adif
    assert "<RST_SENT:2>57" in adif
    assert "<RST_RCVD:2>44" in adif
    assert "<SIG:4>POTA" in adif
    assert "<SIG_INFO:7>US-1234" in adif
    assert "STATION_CALLSIGN" not in adif
    assert adif.endswith("<EOR>")
```

```python
def test_logged_adif_omits_blank_received_report():
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")

    adif = build_logged_adif(spot, "59", "  ")

    assert "<RST_SENT:2>59" in adif
    assert "RST_RCVD" not in adif
```

```python
def test_logged_adif_packet_fields_are_aligned():
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    logged_at = datetime(2026, 5, 7, 14, 3, 5, tzinfo=timezone.utc)

    reader = PacketReader(build_logged_adif_packet(spot, "57", "44", now=logged_at))

    assert reader.uint32() == MAGIC
    assert reader.uint32() == SCHEMA_VERSION
    assert reader.uint32() == MESSAGE_TYPE_LOGGED_ADIF
    assert reader.qstring() == "WSJT-X"
    adif = reader.qstring()
    assert "<CALL:5>K1ABC" in adif
    assert "<RST_SENT:2>57" in adif
    assert "<RST_RCVD:2>44" in adif
    assert reader.done()
```

Update `test_logger_client_sends_status_packet` or add:

```python
def test_logger_client_sends_logged_adif_packet(monkeypatch):
    sent = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def sendto(self, packet, address):
            sent.append((packet, address))

    monkeypatch.setattr("socket.socket", lambda family, kind: FakeSocket())

    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")

    from pota_spot_hunter.logger_udp import LoggerClient

    LoggerClient("127.0.0.1", 2237).log_qso(spot, "57", "44")

    assert len(sent) == 2
    assert sent[0] == (build_heartbeat_packet(), ("127.0.0.1", 2237))
    reader = PacketReader(sent[1][0])
    assert reader.uint32() == MAGIC
    assert reader.uint32() == SCHEMA_VERSION
    assert reader.uint32() == MESSAGE_TYPE_LOGGED_ADIF
    assert sent[1][1] == ("127.0.0.1", 2237)
```

- [ ] **Step 2: Run logger tests and verify failure**

Run: `.\.venv\Scripts\pytest.exe tests\test_logger_udp.py -v`

Expected: FAIL because logged ADIF helpers do not exist.

- [ ] **Step 3: Implement logged ADIF helpers**

In `src/pota_spot_hunter/logger_udp.py`, add:

```python
from datetime import datetime, timezone
```

Add:

```python
MESSAGE_TYPE_LOGGED_ADIF = 12
```

Add:

```python
def build_logged_adif(
    spot: Spot,
    rst_sent: str,
    rst_received: str | None = None,
    now: datetime | None = None,
) -> str:
    logged_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    fields = [
        _adif_field("CALL", spot.activator),
        _adif_field("QSO_DATE", logged_at.strftime("%Y%m%d")),
        _adif_field("TIME_ON", logged_at.strftime("%H%M%S")),
        _adif_field("BAND", spot.band.upper()),
        _adif_field("FREQ", f"{spot.frequency_khz / 1000:.3f}"),
        _adif_field("MODE", spot.mode),
        _adif_field("RST_SENT", rst_sent.strip()),
    ]
    received = "" if rst_received is None else rst_received.strip()
    if received:
        fields.append(_adif_field("RST_RCVD", received))
    fields.extend(
        [
            _adif_field("SIG", "POTA"),
            _adif_field("SIG_INFO", spot.park),
        ]
    )
    return " ".join(fields) + " <EOR>"


def build_logged_adif_packet(
    spot: Spot,
    rst_sent: str,
    rst_received: str | None = None,
    now: datetime | None = None,
) -> bytes:
    return b"".join(
        [
            _uint32(MAGIC),
            _uint32(SCHEMA_VERSION),
            _uint32(MESSAGE_TYPE_LOGGED_ADIF),
            _qstring(CLIENT_ID),
            _qstring(build_logged_adif(spot, rst_sent, rst_received, now)),
        ]
    )


def _adif_field(name: str, value: str) -> str:
    return f"<{name}:{len(value)}>{value}"
```

Add to `LoggerClient`:

```python
    def log_qso(self, spot: Spot, rst_sent: str, rst_received: str | None = None) -> None:
        packets = [
            build_heartbeat_packet(),
            build_logged_adif_packet(spot, rst_sent, rst_received),
        ]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            for packet in packets:
                sock.sendto(packet, self.address)
```

- [ ] **Step 4: Run logger tests and verify pass**

Run: `.\.venv\Scripts\pytest.exe tests\test_logger_udp.py -v`

Expected: PASS.

### Task 2: QSO Completion Dialog and GUI Command

**Files:**
- Modify: `src/pota_spot_hunter/gui.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write failing GUI tests**

Extend `FakeLogger`:

```python
        self.logged = []
```

Add:

```python
    def log_qso(self, spot, rst_sent, rst_received=None):
        if self.error is not None:
            raise self.error
        self.logged.append((spot, rst_sent, rst_received))
```

Add tests:

```python
def test_default_qso_reports_follow_mode(qtbot):
    cw_window = make_window(qtbot, [Spot("K1ABC", "US-1234", 14032.0, "CW")])
    ssb_window = make_window(qtbot, [Spot("W9XYZ", "US-9876", 14244.0, "SSB")])

    assert cw_window.default_qso_report(cw_window.visible_spots[0]) == "599"
    assert ssb_window.default_qso_report(ssb_window.visible_spots[0]) == "59"
```

```python
def test_shift_w_logs_qso_and_marks_worked(qtbot, monkeypatch):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    logger = FakeLogger()
    window = make_window(qtbot, [spot], logger=logger)

    class FakeDialog:
        def __init__(self, spot, default_report, parent=None):
            self.default_report = default_report

        def exec(self):
            return QDialog.DialogCode.Accepted

        def reports(self):
            return ("57", "44")

    monkeypatch.setattr("pota_spot_hunter.gui.CompleteQsoDialog", FakeDialog)

    qtbot.keyClick(window.table, Qt.Key.Key_W, modifier=Qt.KeyboardModifier.ShiftModifier)

    assert logger.logged == [(spot, "57", "44")]
    assert window.table.rowCount() == 0
    assert "logged" in window.status_label.text()
```

```python
def test_shift_w_cancel_does_not_log_or_mark_worked(qtbot, monkeypatch):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    logger = FakeLogger()
    window = make_window(qtbot, [spot], logger=logger)

    class FakeDialog:
        def __init__(self, spot, default_report, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr("pota_spot_hunter.gui.CompleteQsoDialog", FakeDialog)

    qtbot.keyClick(window.table, Qt.Key.Key_W, modifier=Qt.KeyboardModifier.ShiftModifier)

    assert logger.logged == []
    assert window.table.rowCount() == 1
```

```python
def test_shift_w_logger_error_keeps_spot_visible(qtbot, monkeypatch):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [spot], logger=FakeLogger(error=RuntimeError("log failed")))

    class FakeDialog:
        def __init__(self, spot, default_report, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def reports(self):
            return ("57", "")

    monkeypatch.setattr("pota_spot_hunter.gui.CompleteQsoDialog", FakeDialog)

    qtbot.keyClick(window.table, Qt.Key.Key_W, modifier=Qt.KeyboardModifier.ShiftModifier)

    assert window.table.rowCount() == 1
    assert "log failed" in window.status_label.text()
```

Import `QDialog` in the test file:

```python
from PySide6.QtWidgets import QDialog, QPushButton
```

- [ ] **Step 2: Run GUI tests and verify failure**

Run: `.\.venv\Scripts\pytest.exe tests\test_gui.py -v`

Expected: FAIL because `CompleteQsoDialog`, `default_qso_report`, and Shift+W handling do not exist.

- [ ] **Step 3: Implement GUI completion flow**

In `Logger` protocol, add:

```python
    def log_qso(self, spot: Spot, rst_sent: str, rst_received: str | None = None) -> None:
        ...
```

In `eventFilter`, handle `Shift+W` before the plain key handlers:

```python
            if (
                event.key() == Qt.Key.Key_W
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            ):
                self.complete_selected_qso()
                return True
```

Add methods to `MainWindow`:

```python
    def default_qso_report(self, spot: Spot) -> str:
        if spot.mode == "CW":
            return "599"
        return "59"

    def complete_selected_qso(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        spot = self.visible_spots[row]
        dialog = CompleteQsoDialog(spot, self.default_qso_report(spot), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rst_sent, rst_received = dialog.reports()
        try:
            self.logger.log_qso(spot, rst_sent, rst_received)
        except Exception as exc:
            self.status_label.setText(f"{spot.activator}: {exc}")
            return
        self.state.mark_worked(spot)
        if self.selected_spot_key == spot.key:
            self.selected_spot_key = None
        self.status_label.setText(f"{spot.activator} logged and marked worked")
        self.render_spots()
```

Add dialog class before `SettingsDialog`:

```python
class CompleteQsoDialog(QDialog):
    def __init__(self, spot: Spot, default_report: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Log {spot.activator}")

        self.rst_sent = QLineEdit(default_report)
        self.rst_received = QLineEdit(default_report)
        self.rst_sent.selectAll()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow("Sent RST", self.rst_sent)
        layout.addRow("Received RST", self.rst_received)
        layout.addRow(buttons)

    def reports(self) -> tuple[str, str]:
        return self.rst_sent.text().strip(), self.rst_received.text().strip()
```

- [ ] **Step 4: Run GUI tests and verify pass**

Run: `.\.venv\Scripts\pytest.exe tests\test_gui.py -v`

Expected: PASS.

### Task 3: Documentation and Full Verification

**Files:**
- Modify: `README.md`
- Create: `docs/superpowers/plans/2026-05-07-complete-qso-from-keyboard.md`

- [ ] **Step 1: Update README keyboard controls**

Add:

```markdown
- `Shift+W`: log the highlighted spot as a completed QSO, then mark it worked.
```

Add a short note near the integrations or keyboard section:

```markdown
Completed QSOs are sent to the logger as WSJT-X-compatible Logged ADIF messages with contact details and POTA park reference. Station identity remains managed by the logger.
```

- [ ] **Step 2: Run full test suite**

Run: `.\.venv\Scripts\pytest.exe -v`

Expected: PASS.

- [ ] **Step 3: Commit implementation**

```bash
git add README.md src/pota_spot_hunter/gui.py src/pota_spot_hunter/logger_udp.py tests/test_gui.py tests/test_logger_udp.py docs/superpowers/plans/2026-05-07-complete-qso-from-keyboard.md
git commit -m "feat: log completed qsos from keyboard"
```
