from pota_spot_hunter.app import choose_rig_controller
from pota_spot_hunter.rig import FakeRigController


def test_choose_rig_controller_uses_fake_when_requested():
    rig = choose_rig_controller(use_fake=True, rig_number=1)

    assert isinstance(rig, FakeRigController)
