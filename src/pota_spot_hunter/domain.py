from dataclasses import dataclass, field

from .bands import band_for_frequency_khz


@dataclass(frozen=True)
class SpotKey:
    activator: str
    park: str
    band: str
    mode: str


@dataclass(frozen=True)
class Spot:
    activator: str
    park: str
    frequency_khz: float
    mode: str
    spotter: str = ""
    comments: str = ""
    expires_at: str | None = None
    is_qrt: bool = False
    band: str = field(init=False)
    key: SpotKey = field(init=False)

    def __post_init__(self) -> None:
        activator = self.activator.strip().upper()
        park = self.park.strip().upper()
        mode = self.mode.strip().upper()
        band = band_for_frequency_khz(self.frequency_khz)

        object.__setattr__(self, "activator", activator)
        object.__setattr__(self, "park", park)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "band", band)
        object.__setattr__(
            self,
            "key",
            SpotKey(activator=activator, park=park, band=band, mode=mode),
        )
