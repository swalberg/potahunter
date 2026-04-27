from pota_spot_hunter.domain import Spot
from pota_spot_hunter.logger_udp import (
    MAGIC,
    MESSAGE_TYPE_STATUS,
    SCHEMA_VERSION,
    build_status_packet,
)


def test_status_packet_contains_wsjt_x_header_and_spot_details():
    spot = Spot(
        activator="K1ABC",
        park="US-1234",
        frequency_khz=14244.0,
        mode="SSB",
        spotter="W1XYZ",
        comments="57 into CT",
    )

    packet = build_status_packet(spot)

    assert packet[:4] == MAGIC.to_bytes(4, "big")
    assert packet[4:8] == SCHEMA_VERSION.to_bytes(4, "big")
    assert packet[8:12] == MESSAGE_TYPE_STATUS.to_bytes(4, "big")
    assert b"POTA Spot Hunter" in packet
    assert b"K1ABC" in packet
    assert b"US-1234" in packet
    assert b"14.244" in packet
    assert b"SSB" in packet
