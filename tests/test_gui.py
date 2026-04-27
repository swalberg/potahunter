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
