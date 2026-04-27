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


def test_refresh_failure_keeps_existing_spots(qtbot):
    existing = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    window = make_window(qtbot, [existing], spot_source=FakeSpotSource([]))

    window.handle_refresh_failure("network down")

    assert window.table.rowCount() == 1
    assert window.table.item(0, 0).text() == "K1ABC"
    assert window.refresh_button.isEnabled() is True
    assert window.status_label.text() == "POTA refresh failed: network down"


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
