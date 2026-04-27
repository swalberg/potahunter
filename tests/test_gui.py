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


def make_window(qtbot, spots, rig=None, logger=None):
    window = MainWindow(
        spots=spots,
        state=SpotState(ignore_minutes=15),
        rig=rig or FakeRigController(),
        logger=logger or FakeLogger(),
    )
    qtbot.addWidget(window)
    window.show()
    return window


def click_action_button(qtbot, window, text):
    actions = window.table.cellWidget(0, 6)
    buttons = actions.findChildren(QPushButton)
    button = next(button for button in buttons if button.text() == text)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
