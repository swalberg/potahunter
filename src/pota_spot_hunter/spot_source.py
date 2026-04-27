from typing import Any

import httpx

from .domain import Spot


POTA_SPOTS_URL = "https://api.pota.app/spot/activator"


class SpotSourceError(RuntimeError):
    pass


class PotaSpotSource:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=10.0)

    def fetch(self) -> list[Spot]:
        try:
            response = self.client.get(POTA_SPOTS_URL)
            response.raise_for_status()
            return parse_pota_spots(response.json())
        except Exception as exc:
            raise SpotSourceError(str(exc)) from exc


def parse_pota_spots(payload: list[dict[str, Any]]) -> list[Spot]:
    spots: list[Spot] = []
    for item in payload:
        try:
            frequency_khz = _frequency_to_khz(item["frequency"])
            spots.append(
                Spot(
                    activator=str(item["activator"]),
                    park=str(item["reference"]),
                    frequency_khz=frequency_khz,
                    mode=str(item["mode"]),
                    spotter=str(item.get("spotter", "")),
                    comments=str(item.get("comments", "")),
                    expires_at=item.get("expire"),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return spots


def _frequency_to_khz(value: Any) -> float:
    number = float(value)
    if number < 1000:
        return number * 1000
    return number
