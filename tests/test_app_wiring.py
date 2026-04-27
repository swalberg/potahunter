from pota_spot_hunter.app import choose_rig_controller
from pota_spot_hunter.rig import FakeRigController


def test_choose_rig_controller_uses_fake_when_requested():
    rig = choose_rig_controller(use_fake=True, rig_number=1)

    assert isinstance(rig, FakeRigController)


def test_choose_rig_controller_uses_omnirig_when_fake_not_requested(monkeypatch):
    calls = []

    class FakeOmniRigController:
        def __init__(self, rig_number):
            calls.append(rig_number)

    monkeypatch.setattr("pota_spot_hunter.app.OmniRigController", FakeOmniRigController)

    rig = choose_rig_controller(use_fake=False, rig_number=2)

    assert isinstance(rig, FakeOmniRigController)
    assert calls == [2]
