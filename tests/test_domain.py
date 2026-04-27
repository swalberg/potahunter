from pota_spot_hunter.domain import Spot


def test_spot_key_uses_activator_park_band_and_mode():
    spot = Spot(
        activator=" k1abc ",
        park=" us-1234 ",
        frequency_khz=14244.0,
        mode=" ssb ",
        spotter="W1XYZ",
        comments="57 into CT",
    )

    assert spot.activator == "K1ABC"
    assert spot.park == "US-1234"
    assert spot.mode == "SSB"
    assert spot.band == "20m"
    assert spot.key.activator == "K1ABC"
    assert spot.key.park == "US-1234"
    assert spot.key.band == "20m"
    assert spot.key.mode == "SSB"
