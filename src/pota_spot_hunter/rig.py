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
    MODE_SSB_U = 0x02000000
    MODE_SSB_L = 0x04000000
    MODE_CW_U = 0x00800000
    MODE_CW_L = 0x01000000
    MODE_DATA_U = 0x08000000
    MODE_DATA_L = 0x10000000

    def __init__(self, rig_number: int = 1) -> None:
        if rig_number not in (1, 2):
            raise ValueError("rig_number must be 1 or 2")
        if win32com_client is None:
            raise RuntimeError("pywin32 is required for OmniRig control on Windows")
        self.omnirig = win32com_client.Dispatch("OmniRig.OmniRigX")
        self.rig = self.omnirig.Rig1 if rig_number == 1 else self.omnirig.Rig2

    def tune(self, frequency_khz: float, mode: str) -> None:
        self.rig.FreqA = int(frequency_khz * 1000)
        rig_mode = mode_identifier_for_frequency(frequency_khz, mode)
        if rig_mode is not None:
            self.rig.SetMode(rig_mode)


def mode_identifier_for_frequency(frequency_khz: float, mode: str) -> int | None:
    normalized = mode.strip().upper()
    if normalized == "LSB":
        return OmniRigController.MODE_SSB_L
    if normalized == "USB":
        return OmniRigController.MODE_SSB_U
    if normalized == "SSB":
        return (
            OmniRigController.MODE_SSB_L
            if frequency_khz < 10000
            else OmniRigController.MODE_SSB_U
        )
    if normalized == "CW":
        return OmniRigController.MODE_CW_L
    if normalized in {"DIGI", "FT8"}:
        return (
            OmniRigController.MODE_DATA_L
            if frequency_khz < 10000
            else OmniRigController.MODE_DATA_U
        )
    return None
