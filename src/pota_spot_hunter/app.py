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
