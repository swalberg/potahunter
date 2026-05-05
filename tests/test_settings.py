import json

import pytest

from pota_spot_hunter.settings import AppSettings, SettingsError, load_settings, save_settings


def test_default_settings():
    settings = AppSettings()

    assert settings.refresh_seconds == 60
    assert settings.ignore_minutes == 15
    assert settings.logger_host == "127.0.0.1"
    assert settings.logger_port == 2238
    assert settings.omnirig_rig_number == 1


def test_rejects_invalid_settings():
    with pytest.raises(SettingsError, match="logger_port"):
        AppSettings(logger_port=70000).validate()

    with pytest.raises(SettingsError, match="ignore_minutes"):
        AppSettings(ignore_minutes=-1).validate()

    with pytest.raises(SettingsError, match="logger_host"):
        AppSettings(logger_host="").validate()


def test_save_and_load_settings(tmp_path):
    path = tmp_path / "settings.json"
    settings = AppSettings(refresh_seconds=30, ignore_minutes=10, logger_port=2240)

    save_settings(settings, path)
    loaded = load_settings(path)

    assert json.loads(path.read_text())["refresh_seconds"] == 30
    assert loaded == settings
