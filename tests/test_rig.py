import pytest

from pota_spot_hunter.rig import (
    FakeRigController,
    OmniRigController,
    RigCommand,
    mode_identifier_for_frequency,
)


def test_fake_rig_records_tune_commands():
    rig = FakeRigController()

    rig.tune(frequency_khz=14244.0, mode="SSB")

    assert rig.commands == [RigCommand(frequency_khz=14244.0, mode="SSB")]


def test_omnirig_requires_windows_com_dependency(monkeypatch):
    monkeypatch.setattr("pota_spot_hunter.rig.win32com_client", None)

    with pytest.raises(RuntimeError, match="pywin32"):
        OmniRigController(rig_number=1)


def test_omnirig_rejects_invalid_rig_number_before_com_dependency(monkeypatch):
    monkeypatch.setattr("pota_spot_hunter.rig.win32com_client", None)

    with pytest.raises(ValueError, match="rig_number"):
        OmniRigController(rig_number=3)


def test_omnirig_selects_rig_and_tunes_with_mode(monkeypatch):
    fake_client = FakeComClient()
    monkeypatch.setattr("pota_spot_hunter.rig.win32com_client", fake_client)

    controller = OmniRigController(rig_number=2)
    controller.tune(frequency_khz=14244.0, mode="USB")

    assert fake_client.dispatched_name == "OmniRig.OmniRigX"
    assert fake_client.omnirig.Rig1.FreqA is None
    assert fake_client.omnirig.Rig2.FreqA == 14244000
    assert fake_client.omnirig.Rig2.set_modes == [OmniRigController.MODE_SSB_U]


def test_omnirig_mode_identifiers():
    assert mode_identifier_for_frequency(7244.0, "SSB") == OmniRigController.MODE_SSB_L
    assert mode_identifier_for_frequency(14244.0, "SSB") == OmniRigController.MODE_SSB_U
    assert mode_identifier_for_frequency(14244.0, "USB") == OmniRigController.MODE_SSB_U
    assert mode_identifier_for_frequency(7244.0, "LSB") == OmniRigController.MODE_SSB_L
    assert mode_identifier_for_frequency(14032.0, "CW") == OmniRigController.MODE_CW_L
    assert mode_identifier_for_frequency(14074.0, "FT8") == OmniRigController.MODE_DATA_U
    assert mode_identifier_for_frequency(7074.0, "FT8") == OmniRigController.MODE_DATA_L
    assert mode_identifier_for_frequency(14244.0, "FM") is None


def test_omnirig_sets_mode_with_setmode(monkeypatch):
    fake_client = FakeComClient()
    monkeypatch.setattr("pota_spot_hunter.rig.win32com_client", fake_client)
    controller = OmniRigController(rig_number=1)

    expected_modes = {
        "LSB": OmniRigController.MODE_SSB_L,
        "USB": OmniRigController.MODE_SSB_U,
        "SSB": OmniRigController.MODE_SSB_U,
        "CW": OmniRigController.MODE_CW_L,
        "DIGI": OmniRigController.MODE_DATA_U,
        "FT8": OmniRigController.MODE_DATA_U,
    }

    for mode, expected_value in expected_modes.items():
        controller.tune(frequency_khz=14074.0, mode=mode)
        assert fake_client.omnirig.Rig1.set_modes[-1] == expected_value


class FakeComClient:
    def __init__(self):
        self.dispatched_name = None
        self.omnirig = FakeOmniRig()

    def Dispatch(self, name):
        self.dispatched_name = name
        return self.omnirig


class FakeOmniRig:
    def __init__(self):
        self.Rig1 = FakeComRig()
        self.Rig2 = FakeComRig()


class FakeComRig:
    def __init__(self):
        self.FreqA = None
        self.set_modes = []

    def SetMode(self, mode):
        self.set_modes.append(mode)
