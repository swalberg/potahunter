from pota_spot_hunter import __version__
from pota_spot_hunter.app import main


def test_package_imports():
    assert __version__ == "0.1.0"
    assert main() == 0
