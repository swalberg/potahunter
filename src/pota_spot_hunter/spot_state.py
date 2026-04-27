from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .domain import Spot, SpotKey


@dataclass
class SpotState:
    ignore_minutes: int
    worked: set[SpotKey] = field(default_factory=set)
    cant_hear_until: dict[SpotKey, datetime] = field(default_factory=dict)

    def mark_worked(self, spot: Spot) -> None:
        self.worked.add(spot.key)
        self.cant_hear_until.pop(spot.key, None)

    def mark_cant_hear(self, spot: Spot, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        self.cant_hear_until[spot.key] = current + timedelta(minutes=self.ignore_minutes)

    def visible_spots(self, spots: list[Spot], now: datetime | None = None) -> list[Spot]:
        current = now or datetime.now(timezone.utc)
        self._discard_expired(current)
        return [
            spot
            for spot in spots
            if spot.key not in self.worked and spot.key not in self.cant_hear_until
        ]

    def _discard_expired(self, now: datetime) -> None:
        expired = [
            key
            for key, expires_at in self.cant_hear_until.items()
            if expires_at <= now
        ]
        for key in expired:
            self.cant_hear_until.pop(key, None)
