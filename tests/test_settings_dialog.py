from PySide6.QtWidgets import QDialog

from pota_spot_hunter.domain import Spot
from pota_spot_hunter.gui import MainWindow, SettingsDialog
from pota_spot_hunter.rig import FakeRigController
from pota_spot_hunter.settings import AppSettings
from pota_spot_hunter.spot_state import SpotState


def test_settings_dialog_returns_updated_settings(qtbot):
    dialog = SettingsDialog(AppSettings())
    qtbot.addWidget(dialog)

    dialog.refresh_seconds.setValue(30)
    dialog.ignore_minutes.setValue(10)
    dialog.logger_host.setText("192.168.1.50")
    dialog.logger_port.setValue(2240)
    dialog.omnirig_rig_number.setValue(2)

    settings = dialog.to_settings()

    assert settings.refresh_seconds == 30
    assert settings.ignore_minutes == 10
    assert settings.logger_host == "192.168.1.50"
    assert settings.logger_port == 2240
    assert settings.omnirig_rig_number == 2


def test_main_window_stores_full_settings(qtbot):
    settings = AppSettings(
        refresh_seconds=45,
        ignore_minutes=12,
        logger_host="192.168.1.50",
        logger_port=2240,
        omnirig_rig_number=2,
    )

    window = make_window(qtbot, settings=settings)

    assert window.settings == settings


def test_open_settings_saves_updates_state_and_restarts_timer(qtbot, tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    window = make_window(
        qtbot,
        settings=AppSettings(refresh_seconds=60, ignore_minutes=15),
        settings_path=path,
        spot_source=FakeSpotSource(),
    )

    class FakeDialog:
        def __init__(self, settings):
            self.settings = settings

        def exec(self):
            return QDialog.DialogCode.Accepted

        def to_settings(self):
            return AppSettings(refresh_seconds=30, ignore_minutes=10, logger_port=2240)

    monkeypatch.setattr("pota_spot_hunter.gui.SettingsDialog", FakeDialog)

    window.open_settings()

    assert window.settings.refresh_seconds == 30
    assert window.state.ignore_minutes == 10
    assert window.refresh_timer.interval() == 30000
    assert "Settings saved" in window.status_label.text()
    assert '"logger_port": 2240' in path.read_text()


def test_open_settings_reports_invalid_settings(qtbot, monkeypatch):
    window = make_window(qtbot, settings=AppSettings())

    class FakeDialog:
        def __init__(self, settings):
            self.settings = settings

        def exec(self):
            return QDialog.DialogCode.Accepted

        def to_settings(self):
            raise ValueError("logger_host must not be empty")

    monkeypatch.setattr("pota_spot_hunter.gui.SettingsDialog", FakeDialog)

    window.open_settings()

    assert "Settings error: logger_host must not be empty" == window.status_label.text()


def test_open_settings_does_not_update_runtime_state_when_save_fails(qtbot, monkeypatch):
    original = AppSettings(refresh_seconds=60, ignore_minutes=15)
    window = make_window(qtbot, settings=original, spot_source=FakeSpotSource())

    class FakeDialog:
        def __init__(self, settings):
            self.settings = settings

        def exec(self):
            return QDialog.DialogCode.Accepted

        def to_settings(self):
            return AppSettings(refresh_seconds=30, ignore_minutes=10)

    def fail_save(settings, path):
        raise OSError("disk full")

    monkeypatch.setattr("pota_spot_hunter.gui.SettingsDialog", FakeDialog)
    monkeypatch.setattr("pota_spot_hunter.gui.save_settings", fail_save)

    window.open_settings()

    assert window.settings == original
    assert window.state.ignore_minutes == 15
    assert window.refresh_timer.interval() == 60000
    assert window.status_label.text() == "Settings error: disk full"


def make_window(qtbot, settings=None, settings_path=None, spot_source=None):
    window = MainWindow(
        spots=[Spot("K1ABC", "US-1234", 14244.0, "SSB")],
        state=SpotState(ignore_minutes=(settings or AppSettings()).ignore_minutes),
        rig=FakeRigController(),
        logger=FakeLogger(),
        spot_source=spot_source,
        settings=settings,
        settings_path=settings_path,
    )
    qtbot.addWidget(window)
    return window


class FakeLogger:
    def send_spot(self, spot):
        pass


class FakeSpotSource:
    def fetch(self):
        return []
