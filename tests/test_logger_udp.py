import struct

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
    assert b"SSB" in packet


def test_status_packet_fields_are_aligned():
    spot = Spot(
        activator="K1ABC",
        park="US-1234",
        frequency_khz=14244.0,
        mode="SSB",
        spotter="W1XYZ",
        comments="57 into CT",
    )

    reader = PacketReader(build_status_packet(spot))

    assert reader.uint32() == MAGIC
    assert reader.uint32() == SCHEMA_VERSION
    assert reader.uint32() == MESSAGE_TYPE_STATUS
    assert reader.qstring() == "POTA Spot Hunter"
    assert reader.uint64() == 14244000
    assert reader.qstring() == "SSB"
    assert reader.qstring() == "K1ABC"
    assert reader.qstring() == ""
    assert reader.qstring() == "SSB"
    assert reader.bool() is False
    assert reader.bool() is False
    assert reader.bool() is False
    assert reader.uint32() == 0
    assert reader.uint32() == 0
    assert reader.qstring() == ""
    assert reader.qstring() == ""
    assert reader.qstring() == "US-1234"
    assert reader.bool() is False
    assert reader.qstring() == ""
    assert reader.bool() is False
    assert reader.uint8() == 0
    assert reader.uint32() == 0
    assert reader.uint32() == 0
    assert reader.qstring() == "POTA Spot Hunter"
    assert reader.done()


def test_logger_client_sends_status_packet(monkeypatch):
    sent = []

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def sendto(self, packet, address):
            sent.append((packet, address))

    monkeypatch.setattr("socket.socket", lambda family, kind: FakeSocket())

    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")

    from pota_spot_hunter.logger_udp import LoggerClient

    LoggerClient("127.0.0.1", 2237).send_spot(spot)

    assert sent == [(build_status_packet(spot), ("127.0.0.1", 2237))]


class PacketReader:
    def __init__(self, packet):
        self.packet = packet
        self.offset = 0

    def uint8(self):
        value = self.packet[self.offset]
        self.offset += 1
        return value

    def uint32(self):
        value = struct.unpack_from(">I", self.packet, self.offset)[0]
        self.offset += 4
        return value

    def uint64(self):
        value = struct.unpack_from(">Q", self.packet, self.offset)[0]
        self.offset += 8
        return value

    def bool(self):
        return bool(self.uint8())

    def qstring(self):
        length = struct.unpack_from(">i", self.packet, self.offset)[0]
        self.offset += 4
        if length == -1:
            return None
        value = self.packet[self.offset : self.offset + length].decode("utf-8")
        self.offset += length
        return value

    def done(self):
        return self.offset == len(self.packet)
