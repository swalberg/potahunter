from pota_spot_hunter.gui import SettingsDialog
from pota_spot_hunter.settings import AppSettings


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
