import pytest

from pota_spot_hunter.rig import FakeRigController, OmniRigController, RigCommand


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
    assert fake_client.omnirig.Rig2.Mode == 2


def test_omnirig_mode_constants(monkeypatch):
    fake_client = FakeComClient()
    monkeypatch.setattr("pota_spot_hunter.rig.win32com_client", fake_client)
    controller = OmniRigController(rig_number=1)

    expected_modes = {
        "LSB": 1,
        "USB": 2,
        "SSB": 2,
        "CW": 3,
        "DIGI": 12,
        "FT8": 12,
    }

    for mode, expected_value in expected_modes.items():
        controller.tune(frequency_khz=14074.0, mode=mode)
        assert fake_client.omnirig.Rig1.Mode == expected_value


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
        self.Mode = None
