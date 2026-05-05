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
    assert spots[0].expires_at == "2026-04-27T18:00:00Z"
    assert spots[0].is_qrt is False


def test_parse_marks_qrt_spots_from_comments():
    payload = [
        {
            "activator": "K1ABC",
            "reference": "US-1234",
            "frequency": "14.244",
            "mode": "SSB",
            "comments": "QRT TNX",
        }
    ]

    spots = parse_pota_spots(payload)

    assert spots[0].is_qrt is True


def test_parse_skips_unusable_spots_and_preserves_valid_neighbors():
    payload = [
        {"activator": "K1ABC", "reference": "US-1234", "frequency": "", "mode": "SSB"},
        {"activator": None, "reference": "US-1234", "frequency": "14.244", "mode": "SSB"},
        {"activator": "K2ABC", "reference": "   ", "frequency": "14.244", "mode": "SSB"},
        {"activator": "K3ABC", "reference": "US-3333", "frequency": "14.244", "mode": ""},
        {
            "activator": "K4ABC",
            "reference": "US-4444",
            "frequency": "7.032",
            "mode": "CW",
            "spotter": None,
            "comments": None,
        },
    ]

    spots = parse_pota_spots(payload)

    assert len(spots) == 1
    assert spots[0].activator == "K4ABC"
    assert spots[0].park == "US-4444"
    assert spots[0].spotter == ""
    assert spots[0].comments == ""


def test_parse_rejects_non_list_payload():
    with pytest.raises(SpotSourceError, match="Expected POTA spots list"):
        parse_pota_spots({"spots": []})


def test_fetch_wraps_http_errors():
    class BrokenClient:
        def get(self, url):
            raise RuntimeError("network down")

    source = PotaSpotSource(client=BrokenClient())

    with pytest.raises(SpotSourceError, match="network down"):
        source.fetch()
