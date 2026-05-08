from datetime import datetime, timezone
import struct

from pota_spot_hunter.domain import Spot
from pota_spot_hunter.logger_udp import (
    MAGIC,
    MESSAGE_TYPE_HEARTBEAT,
    MESSAGE_TYPE_LOGGED_ADIF,
    MESSAGE_TYPE_STATUS,
    SCHEMA_VERSION,
    build_heartbeat_packet,
    build_logged_adif,
    build_logged_adif_packet,
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
    assert b"WSJT-X" in packet
    assert b"K1ABC" in packet
    assert b"US-1234" in packet
    assert b"SSB" in packet


def test_heartbeat_packet_identifies_as_wsjtx_peer():
    reader = PacketReader(build_heartbeat_packet())

    assert reader.uint32() == MAGIC
    assert reader.uint32() == SCHEMA_VERSION
    assert reader.uint32() == MESSAGE_TYPE_HEARTBEAT
    assert reader.qstring() == "WSJT-X"
    assert reader.uint32() == SCHEMA_VERSION
    assert reader.qstring() == "POTA Spot Hunter"
    assert reader.qstring() == ""
    assert reader.done()


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
    assert reader.qstring() == "WSJT-X"
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
    assert reader.qstring() == "WSJT-X"
    assert reader.done()


def test_logged_adif_contains_minimal_qso_fields():
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    logged_at = datetime(2026, 5, 7, 14, 3, 5, tzinfo=timezone.utc)

    adif = build_logged_adif(spot, "57", "44", now=logged_at)

    assert "<CALL:5>K1ABC" in adif
    assert "<QSO_DATE:8>20260507" in adif
    assert "<TIME_ON:6>140305" in adif
    assert "<BAND:3>20M" in adif
    assert "<FREQ:6>14.244" in adif
    assert "<MODE:3>SSB" in adif
    assert "<RST_SENT:2>57" in adif
    assert "<RST_RCVD:2>44" in adif
    assert "<SIG:4>POTA" in adif
    assert "<SIG_INFO:7>US-1234" in adif
    assert "STATION_CALLSIGN" not in adif
    assert adif.endswith("<EOR>")


def test_logged_adif_omits_blank_received_report():
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")

    adif = build_logged_adif(spot, "59", "  ")

    assert "<RST_SENT:2>59" in adif
    assert "RST_RCVD" not in adif


def test_logged_adif_packet_fields_are_aligned():
    spot = Spot("K1ABC", "US-1234", 14244.0, "SSB")
    logged_at = datetime(2026, 5, 7, 14, 3, 5, tzinfo=timezone.utc)

    reader = PacketReader(build_logged_adif_packet(spot, "57", "44", now=logged_at))

    assert reader.uint32() == MAGIC
    assert reader.uint32() == SCHEMA_VERSION
    assert reader.uint32() == MESSAGE_TYPE_LOGGED_ADIF
    assert reader.qstring() == "WSJT-X"
    adif = reader.qstring()
    assert "<CALL:5>K1ABC" in adif
    assert "<RST_SENT:2>57" in adif
    assert "<RST_RCVD:2>44" in adif
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

    assert sent == [
        (build_heartbeat_packet(), ("127.0.0.1", 2237)),
        (build_status_packet(spot), ("127.0.0.1", 2237)),
    ]


def test_logger_client_sends_logged_adif_packet(monkeypatch):
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

    LoggerClient("127.0.0.1", 2237).log_qso(spot, "57", "44")

    assert len(sent) == 2
    assert sent[0] == (build_heartbeat_packet(), ("127.0.0.1", 2237))
    reader = PacketReader(sent[1][0])
    assert reader.uint32() == MAGIC
    assert reader.uint32() == SCHEMA_VERSION
    assert reader.uint32() == MESSAGE_TYPE_LOGGED_ADIF
    assert sent[1][1] == ("127.0.0.1", 2237)


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
