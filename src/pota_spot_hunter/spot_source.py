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
    if not isinstance(payload, list):
        raise SpotSourceError("Expected POTA spots list")

    spots: list[Spot] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            frequency_khz = _frequency_to_khz(item["frequency"])
            activator = _required_text(item["activator"])
            park = _required_text(item["reference"])
            mode = _required_text(item["mode"])
            spots.append(
                Spot(
                    activator=activator,
                    park=park,
                    frequency_khz=frequency_khz,
                    mode=mode,
                    spotter=_optional_text(item.get("spotter")),
                    comments=_optional_text(item.get("comments")),
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


def _required_text(value: Any) -> str:
    if value is None:
        raise ValueError("required text is missing")
    text = str(value).strip()
    if not text:
        raise ValueError("required text is blank")
    return text


def _optional_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
