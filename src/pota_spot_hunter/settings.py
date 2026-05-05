from dataclasses import asdict, dataclass
import json
from pathlib import Path

from platformdirs import user_config_dir


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class AppSettings:
    refresh_seconds: int = 60
    ignore_minutes: int = 15
    logger_host: str = "127.0.0.1"
    logger_port: int = 2238
    omnirig_rig_number: int = 1

    def validate(self) -> "AppSettings":
        if self.refresh_seconds <= 0:
            raise SettingsError("refresh_seconds must be positive")
        if self.ignore_minutes < 0:
            raise SettingsError("ignore_minutes must be zero or positive")
        if not self.logger_host.strip():
            raise SettingsError("logger_host must not be empty")
        if not 1 <= self.logger_port <= 65535:
            raise SettingsError("logger_port must be between 1 and 65535")
        if self.omnirig_rig_number not in (1, 2):
            raise SettingsError("omnirig_rig_number must be 1 or 2")
        return self


def default_settings_path() -> Path:
    return Path(user_config_dir("POTA Spot Hunter", "pota-spot-hunter")) / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    settings_path = path or default_settings_path()
    if not settings_path.exists():
        return AppSettings()
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    return AppSettings(**data).validate()


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    settings.validate()
    settings_path = path or default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(asdict(settings), indent=2) + "\n",
        encoding="utf-8",
    )
