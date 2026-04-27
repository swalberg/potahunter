from dataclasses import dataclass, field
from typing import Protocol

try:
    from win32com import client as win32com_client
except ImportError:
    win32com_client = None


@dataclass(frozen=True)
class RigCommand:
    frequency_khz: float
    mode: str


class RigController(Protocol):
    def tune(self, frequency_khz: float, mode: str) -> None:
        ...


@dataclass
class FakeRigController:
    commands: list[RigCommand] = field(default_factory=list)

    def tune(self, frequency_khz: float, mode: str) -> None:
        self.commands.append(RigCommand(frequency_khz=frequency_khz, mode=mode))


class OmniRigController:
    MODE_MAP = {
        "CW": 1,
        "USB": 2,
        "LSB": 3,
        "SSB": 2,
        "DIGI": 4,
        "FT8": 4,
    }

    def __init__(self, rig_number: int = 1) -> None:
        if win32com_client is None:
            raise RuntimeError("pywin32 is required for OmniRig control on Windows")
        if rig_number not in (1, 2):
            raise ValueError("rig_number must be 1 or 2")
        self.omnirig = win32com_client.Dispatch("OmniRig.OmniRigX")
        self.rig = self.omnirig.Rig1 if rig_number == 1 else self.omnirig.Rig2

    def tune(self, frequency_khz: float, mode: str) -> None:
        self.rig.FreqA = int(frequency_khz * 1000)
        rig_mode = self.MODE_MAP.get(mode.upper())
        if rig_mode is not None:
            self.rig.Mode = rig_mode
