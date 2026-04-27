import pytest

from pota_spot_hunter.spot_source import PotaSpotSource, SpotSourceError, parse_pota_spots


def test_parse_pota_spots_from_api_shape():
    payload = [
        {
            "activator": "K1ABC",
            "reference": "US-1234",
            "frequency": "14.244",
            "mode": "SSB",
            "spotter": "W1XYZ",
            "comments": "57 into CT",
            "expire": "2026-04-27T18:00:00Z",
        }
    ]

    spots = parse_pota_spots(payload)

    assert len(spots) == 1
    assert spots[0].activator == "K1ABC"
    assert spots[0].park == "US-1234"
    assert spots[0].frequency_khz == 14244.0
    assert spots[0].mode == "SSB"
    assert spots[0].spotter == "W1XYZ"
    assert spots[0].comments == "57 into CT"


def test_parse_skips_unusable_spot():
    payload = [{"activator": "K1ABC", "reference": "US-1234", "frequency": "", "mode": "SSB"}]

    assert parse_pota_spots(payload) == []


def test_fetch_wraps_http_errors():
    class BrokenClient:
        def get(self, url):
            raise RuntimeError("network down")

    source = PotaSpotSource(client=BrokenClient())

    with pytest.raises(SpotSourceError, match="network down"):
        source.fetch()
