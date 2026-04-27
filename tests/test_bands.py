import pytest

from pota_spot_hunter.bands import band_for_frequency_khz


@pytest.mark.parametrize(
    ("frequency_khz", "band"),
    [
        (1810.0, "160m"),
        (3560.0, "80m"),
        (7040.0, "40m"),
        (10136.0, "30m"),
        (14074.0, "20m"),
        (18100.0, "17m"),
        (21074.0, "15m"),
        (24915.0, "12m"),
        (28074.0, "10m"),
        (50313.0, "6m"),
    ],
)
def test_band_for_frequency(frequency_khz, band):
    assert band_for_frequency_khz(frequency_khz) == band


def test_band_for_unknown_frequency():
    assert band_for_frequency_khz(999999.0) == "unknown"
