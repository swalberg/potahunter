# Spot Age Column Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact `Age` column that shows how long ago each POTA spot was last heard.

**Architecture:** Store parsed `spotTime` on the `Spot` domain object as an optional timezone-aware `datetime`. Parse timestamps in `spot_source.py`, sort visible GUI rows newest-first by that timestamp, format compact relative ages in `gui.py`, and render the new column before `Call`.

**Tech Stack:** Python, PySide6 `QTableWidget`, pytest, pytest-qt.

---

### Task 1: Parse and Store Spot Time

**Files:**
- Modify: `src/pota_spot_hunter/domain.py`
- Modify: `src/pota_spot_hunter/spot_source.py`
- Test: `tests/test_spot_source.py`

- [ ] **Step 1: Write failing parser tests**

In `tests/test_spot_source.py`, add:

```python
from datetime import datetime, timezone
```

Update `test_parse_pota_spots_from_api_shape` payload with:

```python
            "spotTime": "2026-05-04T01:18:07",
```

Add this assertion:

```python
    assert spots[0].spotted_at == datetime(2026, 5, 4, 1, 18, 7, tzinfo=timezone.utc)
```

Add this new test:

```python
def test_parse_keeps_valid_spots_when_spot_time_is_missing_or_invalid():
    payload = [
        {
            "activator": "K1ABC",
            "reference": "US-1234",
            "frequency": "14.244",
            "mode": "SSB",
            "spotTime": "not-a-date",
        },
        {
            "activator": "W9XYZ",
            "reference": "US-9876",
            "frequency": "7.032",
            "mode": "CW",
        },
    ]

    spots = parse_pota_spots(payload)

    assert len(spots) == 2
    assert spots[0].spotted_at is None
    assert spots[1].spotted_at is None
```

- [ ] **Step 2: Run parser tests and verify failure**

Run: `.\.venv\Scripts\pytest.exe tests\test_spot_source.py -v`

Expected: FAIL because `Spot` has no `spotted_at` field yet.

- [ ] **Step 3: Implement domain and parser support**

In `src/pota_spot_hunter/domain.py`, add:

```python
from datetime import datetime
```

Add this field to `Spot`:

```python
    spotted_at: datetime | None = None
```

In `src/pota_spot_hunter/spot_source.py`, add:

```python
from datetime import datetime, timezone
```

Pass `spotted_at` into `Spot`:

```python
                    spotted_at=_parse_spot_time(item.get("spotTime")),
```

Add:

```python
def _parse_spot_time(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        text = str(value).strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
```

- [ ] **Step 4: Run parser tests and verify pass**

Run: `.\.venv\Scripts\pytest.exe tests\test_spot_source.py -v`

Expected: PASS.

### Task 2: Format, Sort, and Render Age Column

**Files:**
- Modify: `src/pota_spot_hunter/gui.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Write failing GUI tests**

In `tests/test_gui.py`, add:

```python
from datetime import datetime, timezone
```

Add this test after `test_table_click_tunes_and_sends_logger_update`:

```python
def test_table_shows_compact_spot_age(qtbot):
    spot = Spot(
        "K1ABC",
        "US-1234",
        14244.0,
        "SSB",
        spotted_at=datetime(2026, 5, 4, 0, 6, tzinfo=timezone.utc),
    )
    window = make_window(qtbot, [spot])

    assert window.table.horizontalHeaderItem(0).text() == "Age"
    assert window.table.item(0, 0).text() == "1h 12m"
```

Add this test near it:

```python
def test_table_leaves_age_blank_without_spot_time(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [spot])

    assert window.table.item(0, 0).text() == ""
```

Add this test near it:

```python
def test_table_sorts_freshest_spots_first(qtbot, monkeypatch):
    original = MainWindow.format_spot_age
    monkeypatch.setattr(
        MainWindow,
        "format_spot_age",
        lambda self, spot, now=None: original(
            self,
            spot,
            now=datetime(2026, 5, 4, 1, 18, tzinfo=timezone.utc),
        ),
    )
    older = Spot(
        "K1ABC",
        "US-1234",
        14244.0,
        "SSB",
        spotted_at=datetime(2026, 5, 4, 0, 6, tzinfo=timezone.utc),
    )
    newer = Spot(
        "W9XYZ",
        "US-9876",
        7032.0,
        "CW",
        spotted_at=datetime(2026, 5, 4, 1, 16, tzinfo=timezone.utc),
    )
    undated = Spot("N0CALL", "US-5555", 14074.0, "FT8")

    window = make_window(qtbot, [older, undated, newer])

    assert [window.table.item(row, 1).text() for row in range(3)] == [
        "W9XYZ",
        "K1ABC",
        "N0CALL",
    ]
    assert [window.table.item(row, 0).text() for row in range(3)] == [
        "2m",
        "1h 12m",
        "",
    ]
```

- [ ] **Step 2: Run GUI tests and verify failure**

Run: `.\.venv\Scripts\pytest.exe tests\test_gui.py::test_table_shows_compact_spot_age tests\test_gui.py::test_table_leaves_age_blank_without_spot_time -v`

Expected: FAIL because there is no `Age` column yet.

- [ ] **Step 3: Implement age formatting and column rendering**

In `src/pota_spot_hunter/gui.py`, add:

```python
from datetime import datetime, timezone
```

Change headers to:

```python
    HEADERS = ["Age", "Call", "Freq", "Band", "Mode", "Park", "Comments", "After Trying"]
```

In `render_spots`, sort visible rows by age and add age before activator:

```python
        self.visible_spots = self.sort_spots_by_age(
            self.filter_spots(self.state.visible_spots(self.all_spots))
        )
```

```python
                self.format_spot_age(spot),
                spot.activator,
                f"{spot.frequency_khz / 1000:.3f}",
```

Change the action widget column from `6` to `7`:

```python
            self.table.setCellWidget(row, 7, actions)
```

Add:

```python
    def format_spot_age(self, spot: Spot, now: datetime | None = None) -> str:
        if spot.spotted_at is None:
            return ""
        current = now or datetime.now(timezone.utc)
        spotted_at = spot.spotted_at
        if spotted_at.tzinfo is None:
            spotted_at = spotted_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(0, int((current - spotted_at.astimezone(timezone.utc)).total_seconds()))
        elapsed_minutes = elapsed_seconds // 60
        if elapsed_minutes < 60:
            return f"{elapsed_minutes}m"
        hours = elapsed_minutes // 60
        minutes = elapsed_minutes % 60
        return f"{hours}h {minutes}m"
```

Add:

```python
    def sort_spots_by_age(self, spots: list[Spot]) -> list[Spot]:
        def spotted_at_utc(spot: Spot) -> datetime:
            if spot.spotted_at is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if spot.spotted_at.tzinfo is None:
                return spot.spotted_at.replace(tzinfo=timezone.utc)
            return spot.spotted_at.astimezone(timezone.utc)

        return sorted(
            spots,
            key=lambda spot: (spot.spotted_at is not None, spotted_at_utc(spot)),
            reverse=True,
        )
```

- [ ] **Step 4: Stabilize GUI age tests**

Because `format_spot_age` uses the current clock during normal rendering, update `test_table_shows_compact_spot_age` to monkeypatch `MainWindow.format_spot_age` before creating the window:

```python
    original = MainWindow.format_spot_age
    monkeypatch.setattr(
        MainWindow,
        "format_spot_age",
        lambda self, spot, now=None: original(
            self,
            spot,
            now=datetime(2026, 5, 4, 1, 18, tzinfo=timezone.utc),
        ),
    )
```

Add `monkeypatch` to the test signature:

```python
def test_table_shows_compact_spot_age(qtbot, monkeypatch):
```

- [ ] **Step 5: Run GUI tests and verify pass**

Run: `.\.venv\Scripts\pytest.exe tests\test_gui.py -v`

Expected: PASS.

### Task 3: Update Action Column Helper and Documentation

**Files:**
- Modify: `tests/test_gui.py`
- Modify: `README.md`

- [ ] **Step 1: Update the test action helper for the new action column**

In `tests/test_gui.py`, update:

```python
    actions = window.table.cellWidget(0, 7)
```

- [ ] **Step 2: Document the age column**

In `README.md`, add this bullet under `## Spot Filters` or a nearby table behavior section:

```markdown
- The leftmost `Age` column shows compact spot freshness from the POTA `spotTime` value, such as `2m` or `1h 12m`; spots are sorted newest first.
```

- [ ] **Step 3: Run full test suite**

Run: `.\.venv\Scripts\pytest.exe -v`

Expected: PASS.

- [ ] **Step 4: Commit implementation**

```bash
git add README.md src/pota_spot_hunter/domain.py src/pota_spot_hunter/gui.py src/pota_spot_hunter/spot_source.py tests/test_gui.py tests/test_spot_source.py docs/superpowers/plans/2026-05-07-spot-age-column.md
git commit -m "feat: show spot age column"
```
