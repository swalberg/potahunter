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
