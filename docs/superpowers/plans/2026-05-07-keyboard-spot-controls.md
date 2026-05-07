# Keyboard Spot Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add keyboard-first spot navigation and actions to the POTA spot table.

**Architecture:** Keep the shortcuts as a thin command layer in `MainWindow`. Route activation, worked, and nil-copy actions through the existing row activation and spot state methods so mouse and keyboard behavior stay consistent.

**Tech Stack:** Python, PySide6 `QTableWidget`, pytest, pytest-qt.

---

### Task 1: Table Keyboard Command Tests

**Files:**
- Modify: `tests/test_gui.py`

- [ ] **Step 1: Add tests for movement, actions, and empty-table no-ops**

Add these tests after `test_table_click_tunes_and_sends_logger_update`:

```python
def test_j_and_down_arrow_move_selection_without_tuning(qtbot):
    first = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    second = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [first, second], rig=rig, logger=logger)

    qtbot.keyClick(window.table, Qt.Key.Key_J)

    assert window.table.currentRow() == 0
    assert rig.commands == []
    assert logger.sent == []

    qtbot.keyClick(window.table, Qt.Key.Key_J)

    assert window.table.currentRow() == 1
    assert rig.commands == []
    assert logger.sent == []

    qtbot.keyClick(window.table, Qt.Key.Key_Down)

    assert window.table.currentRow() == 1
    assert rig.commands == []
    assert logger.sent == []
```

```python
def test_k_and_up_arrow_move_selection_without_tuning(qtbot):
    first = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    second = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [first, second], rig=rig, logger=logger)
    window.table.selectRow(1)

    qtbot.keyClick(window.table, Qt.Key.Key_K)

    assert window.table.currentRow() == 0
    assert rig.commands == []
    assert logger.sent == []

    qtbot.keyClick(window.table, Qt.Key.Key_Up)

    assert window.table.currentRow() == 0
    assert rig.commands == []
    assert logger.sent == []
```

```python
def test_space_activates_highlighted_spot(qtbot):
    first = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    second = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [first, second], rig=rig, logger=logger)
    window.table.selectRow(1)

    qtbot.keyClick(window.table, Qt.Key.Key_Space)

    assert rig.commands[0].frequency_khz == 7032.0
    assert logger.sent == [second]
    assert "W9XYZ" in window.status_label.text()
```

```python
def test_worked_shortcut_hides_highlighted_spot_without_tuning(qtbot):
    first = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    second = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [first, second], rig=rig, logger=logger)
    window.table.selectRow(1)

    qtbot.keyClick(window.table, Qt.Key.Key_W)

    assert window.table.rowCount() == 1
    assert window.table.item(0, 0).text() == "K1ABC"
    assert rig.commands == []
    assert logger.sent == []
    assert "marked worked" in window.status_label.text()
```

```python
def test_nil_copy_shortcut_hides_highlighted_spot_without_tuning(qtbot):
    first = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    second = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [first, second], rig=rig, logger=logger)
    window.table.selectRow(1)

    qtbot.keyClick(window.table, Qt.Key.Key_N)

    assert window.table.rowCount() == 1
    assert window.table.item(0, 0).text() == "K1ABC"
    assert rig.commands == []
    assert logger.sent == []
    assert "ignored temporarily" in window.status_label.text()
```

```python
def test_keyboard_shortcuts_on_empty_table_do_not_crash(qtbot):
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [], rig=rig, logger=logger)

    qtbot.keyClick(window.table, Qt.Key.Key_J)
    qtbot.keyClick(window.table, Qt.Key.Key_K)
    qtbot.keyClick(window.table, Qt.Key.Key_Down)
    qtbot.keyClick(window.table, Qt.Key.Key_Up)
    qtbot.keyClick(window.table, Qt.Key.Key_Space)
    qtbot.keyClick(window.table, Qt.Key.Key_W)
    qtbot.keyClick(window.table, Qt.Key.Key_N)

    assert window.table.rowCount() == 0
    assert rig.commands == []
    assert logger.sent == []
```

- [ ] **Step 2: Run the new tests and verify failure**

Run: `.\.venv\Scripts\pytest.exe tests\test_gui.py -v`

Expected: at least one new keyboard shortcut test fails because no custom keyboard command layer exists yet.

### Task 2: MainWindow Keyboard Command Layer

**Files:**
- Modify: `src/pota_spot_hunter/gui.py`
- Test: `tests/test_gui.py`

- [ ] **Step 1: Add Qt shortcut support imports**

Update the existing imports:

```python
from PySide6.QtGui import QKeySequence, QShortcut
```

- [ ] **Step 2: Install shortcuts in `MainWindow.__init__`**

After the table `cellClicked` connection, add:

```python
        self.install_keyboard_shortcuts()
```

- [ ] **Step 3: Add command helper methods**

Add these methods before `open_settings`:

```python
    def install_keyboard_shortcuts(self) -> None:
        shortcuts = [
            ("j", self.move_selection_down),
            (Qt.Key.Key_Down, self.move_selection_down),
            ("k", self.move_selection_up),
            (Qt.Key.Key_Up, self.move_selection_up),
            (Qt.Key.Key_Space, self.activate_selected_spot),
            ("w", self.mark_selected_worked),
            ("n", self.mark_selected_cant_hear),
        ]
        for key, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self.table)
            shortcut.activated.connect(handler)

    def selected_or_first_row(self) -> int | None:
        if not self.visible_spots:
            return None
        row = self.table.currentRow()
        if row < 0 or row >= len(self.visible_spots):
            row = 0
            self.table.selectRow(row)
        return row

    def move_selection_down(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.table.selectRow(min(row + 1, len(self.visible_spots) - 1))
        self.table.setFocus()

    def move_selection_up(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.table.selectRow(max(row - 1, 0))
        self.table.setFocus()

    def activate_selected_spot(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.handle_row_activated(row)

    def mark_selected_worked(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.mark_worked(self.visible_spots[row])

    def mark_selected_cant_hear(self) -> None:
        row = self.selected_or_first_row()
        if row is None:
            return
        self.mark_cant_hear(self.visible_spots[row])
```

- [ ] **Step 4: Keep table focus after rendering**

At the end of `render_spots`, after `self.restore_selected_spot()`, add:

```python
        self.table.setFocus()
```

- [ ] **Step 5: Run GUI tests**

Run: `.\.venv\Scripts\pytest.exe tests\test_gui.py -v`

Expected: all GUI tests pass.

### Task 3: Documentation and Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document keyboard controls**

Add this section after `## Spot Filters`:

```markdown
## Keyboard Controls

- `j` or `Down Arrow`: move the highlighted spot down.
- `k` or `Up Arrow`: move the highlighted spot up.
- `Space`: tune the radio and send the highlighted spot to the logger.
- `w`: mark the highlighted spot worked.
- `n`: mark the highlighted spot nil copy / can't hear.
```

- [ ] **Step 2: Run full test suite**

Run: `.\.venv\Scripts\pytest.exe -v`

Expected: all tests pass.

- [ ] **Step 3: Commit implementation**

```bash
git add README.md src/pota_spot_hunter/gui.py tests/test_gui.py docs/superpowers/plans/2026-05-07-keyboard-spot-controls.md
git commit -m "feat: add keyboard spot controls"
```
