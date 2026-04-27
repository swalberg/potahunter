from datetime import datetime, timedelta, timezone

from pota_spot_hunter.domain import Spot
from pota_spot_hunter.spot_state import SpotState


NOW = datetime(2026, 4, 27, 12, 0, tzinfo=timezone.utc)


def make_spot(frequency_khz=14244.0, mode="SSB") -> Spot:
    return Spot(
        activator="K1ABC",
        park="US-1234",
        frequency_khz=frequency_khz,
        mode=mode,
        spotter="W1XYZ",
        comments="",
    )


def test_worked_hides_same_band_and_mode():
    state = SpotState(ignore_minutes=15)
    spot = make_spot()

    state.mark_worked(spot)

    assert state.visible_spots([spot], now=NOW) == []


def test_worked_reappears_on_different_band_or_mode():
    state = SpotState(ignore_minutes=15)
    state.mark_worked(make_spot(frequency_khz=14244.0, mode="SSB"))

    assert state.visible_spots([make_spot(frequency_khz=7244.0, mode="SSB")], now=NOW)
    assert state.visible_spots([make_spot(frequency_khz=14244.0, mode="CW")], now=NOW)


def test_cant_hear_expires_after_ignore_window():
    state = SpotState(ignore_minutes=15)
    spot = make_spot()

    state.mark_cant_hear(spot, now=NOW)

    assert state.visible_spots([spot], now=NOW + timedelta(minutes=14)) == []
    assert state.visible_spots([spot], now=NOW + timedelta(minutes=16)) == [spot]
