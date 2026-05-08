from datetime import datetime, timezone
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton

from pota_spot_hunter.domain import Spot
from pota_spot_hunter.gui import CompleteQsoDialog, MainWindow
from pota_spot_hunter.rig import FakeRigController
from pota_spot_hunter.spot_state import SpotState


class FakeLogger:
    def __init__(self, error=None):
        self.sent = []
        self.logged = []
        self.error = error

    def send_spot(self, spot):
        if self.error is not None:
            raise self.error
        self.sent.append(spot)

    def log_qso(self, spot, rst_sent, rst_received=None):
        if self.error is not None:
            raise self.error
        self.logged.append((spot, rst_sent, rst_received))


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


def test_table_click_tunes_and_sends_logger_update(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB", "W1XYZ", "57")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [spot], rig=rig, logger=logger)

    qtbot.mouseClick(
        window.table.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.table.visualItemRect(window.table.item(0, 1)).center(),
    )

    assert rig.commands[0].frequency_khz == 14244.0
    assert logger.sent == [spot]
    assert "K1ABC" in window.status_label.text()


def test_table_shows_compact_spot_age(qtbot, monkeypatch):
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


def test_table_leaves_age_blank_without_spot_time(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [spot])

    assert window.table.item(0, 0).text() == ""


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


def test_worked_shortcut_hides_highlighted_spot_without_tuning(qtbot):
    first = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    second = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [first, second], rig=rig, logger=logger)
    window.table.selectRow(1)

    qtbot.keyClick(window.table, Qt.Key.Key_W)

    assert window.table.rowCount() == 1
    assert window.table.item(0, 1).text() == "K1ABC"
    assert rig.commands == []
    assert logger.sent == []
    assert "marked worked" in window.status_label.text()


def test_nil_copy_shortcut_hides_highlighted_spot_without_tuning(qtbot):
    first = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    second = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [first, second], rig=rig, logger=logger)
    window.table.selectRow(1)

    qtbot.keyClick(window.table, Qt.Key.Key_N)

    assert window.table.rowCount() == 1
    assert window.table.item(0, 1).text() == "K1ABC"
    assert rig.commands == []
    assert logger.sent == []
    assert "ignored temporarily" in window.status_label.text()


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


def test_default_qso_reports_follow_mode(qtbot):
    cw_window = make_window(qtbot, [Spot("K1ABC", "US-1234", 14032.0, "CW")])
    ssb_window = make_window(qtbot, [Spot("W9XYZ", "US-9876", 14244.0, "SSB")])

    assert cw_window.default_qso_report(cw_window.visible_spots[0]) == "599"
    assert ssb_window.default_qso_report(ssb_window.visible_spots[0]) == "59"


def test_complete_qso_dialog_shows_report_labels(qtbot):
    dialog = CompleteQsoDialog(Spot("K1ABC", "US-1234", 14244.0, "SSB"), "59")
    qtbot.addWidget(dialog)

    labels = {label.text() for label in dialog.findChildren(QLabel)}

    assert "Sent RST" in labels
    assert "Received RST" in labels
    assert dialog.sent_label.minimumWidth() == 90
    assert "color: #111827" in dialog.sent_label.styleSheet()


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


def test_worked_button_hides_row_without_tuning(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB", "W1XYZ", "57")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [spot], rig=rig, logger=logger)

    click_action_button(qtbot, window, "Worked")

    assert window.table.rowCount() == 0
    assert rig.commands == []
    assert logger.sent == []
    assert "marked worked" in window.status_label.text()


def test_cant_hear_button_hides_row_without_tuning(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB", "W1XYZ", "57")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [spot], rig=rig, logger=logger)

    click_action_button(qtbot, window, "Can't Hear")

    assert window.table.rowCount() == 0
    assert rig.commands == []
    assert logger.sent == []
    assert "ignored temporarily" in window.status_label.text()


def test_row_activation_reports_logger_errors(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB", "W1XYZ", "57")
    rig = FakeRigController()
    window = make_window(qtbot, [spot], rig=rig, logger=FakeLogger(error=RuntimeError("udp down")))

    window.handle_row_activated(0)

    assert rig.commands[0].frequency_khz == 14244.0
    assert "K1ABC" in window.status_label.text()
    assert "udp down" in window.status_label.text()


def test_stylesheet_sets_explicit_button_contrast(qtbot):
    window = make_window(qtbot, [Spot("K1ABC", "US-1234", 14244.0, "SSB")])

    stylesheet = window.styleSheet()

    assert "QPushButton" in stylesheet
    assert "background: #ffffff" in stylesheet
    assert "color: #111827" in stylesheet
    assert "QCheckBox" in stylesheet
    assert "QCheckBox::indicator:checked" in stylesheet


def test_qrt_spots_are_hidden_by_default(qtbot):
    active = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    qrt = Spot("W9XYZ", "US-9876", 7032.0, "CW", is_qrt=True)
    window = make_window(qtbot, [active, qrt])

    assert window.table.rowCount() == 1
    assert window.table.item(0, 1).text() == "K1ABC"


def test_show_qrt_filter_reveals_qrt_spots(qtbot):
    active = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    qrt = Spot("W9XYZ", "US-9876", 7032.0, "CW", is_qrt=True)
    window = make_window(qtbot, [active, qrt])

    window.show_qrt_checkbox.setChecked(True)

    assert window.table.rowCount() == 2
    assert {window.table.item(row, 1).text() for row in range(2)} == {"K1ABC", "W9XYZ"}


def test_mode_filters_allow_multiple_selected_modes(qtbot):
    cw = Spot("K1ABC", "US-1234", 14032.0, "CW")
    ssb = Spot("W9XYZ", "US-9876", 14244.0, "SSB")
    ft8 = Spot("N0CALL", "US-5555", 14074.0, "FT8")
    window = make_window(qtbot, [cw, ssb, ft8])

    window.mode_checkboxes["FT8"].setChecked(False)

    assert window.table.rowCount() == 2
    assert {window.table.item(row, 4).text() for row in range(2)} == {"CW", "SSB"}


def test_unchecking_all_modes_hides_all_spots(qtbot):
    cw = Spot("K1ABC", "US-1234", 14032.0, "CW")
    ssb = Spot("W9XYZ", "US-9876", 14244.0, "SSB")
    window = make_window(qtbot, [cw, ssb])

    window.mode_checkboxes["CW"].setChecked(False)
    window.mode_checkboxes["SSB"].setChecked(False)

    assert window.table.rowCount() == 0


def test_refresh_starts_worker_without_fetching_on_gui_thread(qtbot):
    source = FakeSpotSource([Spot("K1ABC", "US-1234", 14244.0, "SSB")])
    window = make_window(qtbot, [], spot_source=source)

    window.refresh_spots()

    assert source.fetch_calls == 0
    assert window.refresh_button.isEnabled() is False
    assert "Refreshing POTA spots" in window.status_label.text()


def test_refresh_success_updates_spots_and_status(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [], spot_source=FakeSpotSource([]))

    window.handle_refresh_success([spot])

    assert window.table.rowCount() == 1
    assert window.table.item(0, 1).text() == "K1ABC"
    assert window.refresh_button.isEnabled() is True
    assert window.status_label.text() == "Loaded 1 POTA spots"


def test_refresh_reselects_selected_spot_after_order_changes(qtbot):
    selected = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    other = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    window = make_window(qtbot, [selected, other])

    window.handle_row_activated(0)
    window.handle_refresh_success([other, selected])

    assert window.table.currentRow() == 1
    assert window.table.item(window.table.currentRow(), 1).text() == "K1ABC"


def test_worked_selected_spot_clears_remembered_selection(qtbot):
    selected = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    other = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    window = make_window(qtbot, [selected, other])

    window.handle_row_activated(0)
    window.mark_worked(selected)

    assert window.selected_spot_key is None
    assert not window.table.selectionModel().hasSelection()


def test_refresh_failure_keeps_existing_spots(qtbot):
    existing = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [existing], spot_source=FakeSpotSource([]))

    window.handle_refresh_failure("network down")

    assert window.table.rowCount() == 1
    assert window.table.item(0, 1).text() == "K1ABC"
    assert window.refresh_button.isEnabled() is True
    assert window.status_label.text() == "POTA refresh failed: network down"


def test_refresh_worker_success_cleans_up_thread(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [], spot_source=FakeSpotSource([spot]))

    window.refresh_spots()

    qtbot.waitUntil(lambda: window.refresh_thread is None, timeout=1000)

    assert window.table.rowCount() == 1
    assert window.table.item(0, 1).text() == "K1ABC"
    assert window.refresh_worker is None
    assert window.refresh_button.isEnabled() is True


def test_close_waits_for_inflight_refresh(qtbot):
    source = BlockingSpotSource()
    window = make_window(qtbot, [], spot_source=source)

    window.refresh_spots()

    assert window.refresh_thread is not None
    window.close()

    assert source.fetch_finished is True
    assert window.refresh_thread is None
    assert window.refresh_worker is None


def test_close_ignores_event_when_refresh_does_not_finish(qtbot):
    window = make_window(qtbot, [], spot_source=FakeSpotSource([]))
    window.refresh_thread = FakeRefreshThread(wait_result=False)
    window.refresh_worker = object()
    assert window.refresh_timer.isActive() is True
    event = FakeCloseEvent()

    window.closeEvent(event)

    assert event.ignored is True
    assert window.refresh_timer.isActive() is True
    assert window.refresh_thread is not None
    assert window.refresh_worker is not None
    assert window.refresh_thread.quit_called is True
    assert window.refresh_thread.wait_timeout == 12000


def make_window(qtbot, spots, rig=None, logger=None, spot_source=None):
    window = MainWindow(
        spots=spots,
        state=SpotState(ignore_minutes=15),
        rig=rig or FakeRigController(),
        logger=logger or FakeLogger(),
        spot_source=spot_source,
    )
    qtbot.addWidget(window)
    window.show()
    return window


def click_action_button(qtbot, window, text):
    actions = window.table.cellWidget(0, 7)
    buttons = actions.findChildren(QPushButton)
    button = next(button for button in buttons if button.text() == text)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


class FakeSpotSource:
    def __init__(self, spots):
        self.spots = spots
        self.fetch_calls = 0

    def fetch(self):
        self.fetch_calls += 1
        return self.spots


class BlockingSpotSource:
    def __init__(self):
        self.fetch_started = False
        self.fetch_finished = False

    def fetch(self):
        self.fetch_started = True
        time.sleep(0.05)
        self.fetch_finished = True
        return []


class FakeCloseEvent:
    def __init__(self):
        self.ignored = False

    def ignore(self):
        self.ignored = True

    def accept(self):
        pass


class FakeRefreshThread:
    def __init__(self, wait_result):
        self.wait_result = wait_result
        self.quit_called = False
        self.wait_timeout = None

    def quit(self):
        self.quit_called = True

    def wait(self, timeout):
        self.wait_timeout = timeout
        return self.wait_result
