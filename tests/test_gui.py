import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from pota_spot_hunter.domain import Spot
from pota_spot_hunter.gui import MainWindow
from pota_spot_hunter.rig import FakeRigController
from pota_spot_hunter.spot_state import SpotState


class FakeLogger:
    def __init__(self, error=None):
        self.sent = []
        self.error = error

    def send_spot(self, spot):
        if self.error is not None:
            raise self.error
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


def test_table_click_tunes_and_sends_logger_update(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB", "W1XYZ", "57")
    rig = FakeRigController()
    logger = FakeLogger()
    window = make_window(qtbot, [spot], rig=rig, logger=logger)

    qtbot.mouseClick(
        window.table.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.table.visualItemRect(window.table.item(0, 0)).center(),
    )

    assert rig.commands[0].frequency_khz == 14244.0
    assert logger.sent == [spot]
    assert "K1ABC" in window.status_label.text()


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
    assert window.table.item(0, 0).text() == "K1ABC"


def test_show_qrt_filter_reveals_qrt_spots(qtbot):
    active = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    qrt = Spot("W9XYZ", "US-9876", 7032.0, "CW", is_qrt=True)
    window = make_window(qtbot, [active, qrt])

    window.show_qrt_checkbox.setChecked(True)

    assert window.table.rowCount() == 2
    assert {window.table.item(row, 0).text() for row in range(2)} == {"K1ABC", "W9XYZ"}


def test_mode_filters_allow_multiple_selected_modes(qtbot):
    cw = Spot("K1ABC", "US-1234", 14032.0, "CW")
    ssb = Spot("W9XYZ", "US-9876", 14244.0, "SSB")
    ft8 = Spot("N0CALL", "US-5555", 14074.0, "FT8")
    window = make_window(qtbot, [cw, ssb, ft8])

    window.mode_checkboxes["FT8"].setChecked(False)

    assert window.table.rowCount() == 2
    assert {window.table.item(row, 3).text() for row in range(2)} == {"CW", "SSB"}


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
    assert window.table.item(0, 0).text() == "K1ABC"
    assert window.refresh_button.isEnabled() is True
    assert window.status_label.text() == "Loaded 1 POTA spots"


def test_refresh_reselects_selected_spot_after_order_changes(qtbot):
    selected = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    other = Spot("W9XYZ", "US-9876", 7032.0, "CW")
    window = make_window(qtbot, [selected, other])

    window.handle_row_activated(0)
    window.handle_refresh_success([other, selected])

    assert window.table.currentRow() == 1
    assert window.table.item(window.table.currentRow(), 0).text() == "K1ABC"


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
    assert window.table.item(0, 0).text() == "K1ABC"
    assert window.refresh_button.isEnabled() is True
    assert window.status_label.text() == "POTA refresh failed: network down"


def test_refresh_worker_success_cleans_up_thread(qtbot):
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [], spot_source=FakeSpotSource([spot]))

    window.refresh_spots()

    qtbot.waitUntil(lambda: window.refresh_thread is None, timeout=1000)

    assert window.table.rowCount() == 1
    assert window.table.item(0, 0).text() == "K1ABC"
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
    actions = window.table.cellWidget(0, 6)
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
