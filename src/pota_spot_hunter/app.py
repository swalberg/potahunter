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
