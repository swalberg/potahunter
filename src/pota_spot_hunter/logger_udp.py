from datetime import datetime, timezone
import socket
import struct

from .domain import Spot


MAGIC = 0xADBCCBDA
SCHEMA_VERSION = 2
MESSAGE_TYPE_HEARTBEAT = 0
MESSAGE_TYPE_STATUS = 1
MESSAGE_TYPE_LOGGED_ADIF = 12
CLIENT_ID = "WSJT-X"
CLIENT_VERSION = "POTA Spot Hunter"
CLIENT_REVISION = ""


def build_heartbeat_packet() -> bytes:
    return b"".join(
        [
            _uint32(MAGIC),
            _uint32(SCHEMA_VERSION),
            _uint32(MESSAGE_TYPE_HEARTBEAT),
            _qstring(CLIENT_ID),
            _uint32(SCHEMA_VERSION),
            _qstring(CLIENT_VERSION),
            _qstring(CLIENT_REVISION),
        ]
    )


def build_status_packet(spot: Spot) -> bytes:
    frequency_hz = int(spot.frequency_khz * 1000)
    dial_frequency_hz = frequency_hz
    dx_call = spot.activator
    report = ""
    tx_mode = spot.mode
    de_call = ""
    de_grid = ""
    dx_grid = spot.park

    return b"".join(
        [
            _uint32(MAGIC),
            _uint32(SCHEMA_VERSION),
            _uint32(MESSAGE_TYPE_STATUS),
            _qstring(CLIENT_ID),
            _uint64(dial_frequency_hz),
            _qstring(tx_mode),
            _qstring(dx_call),
            _qstring(report),
            _qstring(tx_mode),
            _bool(False),
            _bool(False),
            _bool(False),
            _uint32(0),
            _uint32(0),
            _qstring(de_call),
            _qstring(de_grid),
            _qstring(dx_grid),
            _bool(False),
            _qstring(""),
            _bool(False),
            _uint8(0),
            _uint32(0),
            _uint32(0),
            _qstring(CLIENT_ID),
        ]
    )


def build_logged_adif(
    spot: Spot,
    rst_sent: str,
    rst_received: str | None = None,
    now: datetime | None = None,
) -> str:
    logged_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    fields = [
        _adif_field("CALL", spot.activator),
        _adif_field("QSO_DATE", logged_at.strftime("%Y%m%d")),
        _adif_field("TIME_ON", logged_at.strftime("%H%M%S")),
        _adif_field("BAND", spot.band.upper()),
        _adif_field("FREQ", f"{spot.frequency_khz / 1000:.3f}"),
        _adif_field("MODE", spot.mode),
        _adif_field("RST_SENT", rst_sent.strip()),
    ]
    received = "" if rst_received is None else rst_received.strip()
    if received:
        fields.append(_adif_field("RST_RCVD", received))
    fields.extend(
        [
            _adif_field("SIG", "POTA"),
            _adif_field("SIG_INFO", spot.park),
        ]
    )
    return " ".join(fields) + " <EOR>"


def build_logged_adif_packet(
    spot: Spot,
    rst_sent: str,
    rst_received: str | None = None,
    now: datetime | None = None,
) -> bytes:
    return b"".join(
        [
            _uint32(MAGIC),
            _uint32(SCHEMA_VERSION),
            _uint32(MESSAGE_TYPE_LOGGED_ADIF),
            _qstring(CLIENT_ID),
            _qstring(build_logged_adif(spot, rst_sent, rst_received, now)),
        ]
    )


class LoggerClient:
    def __init__(self, host: str, port: int) -> None:
        self.address = (host, port)

    def send_spot(self, spot: Spot) -> None:
        packets = [build_heartbeat_packet(), build_status_packet(spot)]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            for packet in packets:
                sock.sendto(packet, self.address)

    def log_qso(self, spot: Spot, rst_sent: str, rst_received: str | None = None) -> None:
        packets = [
            build_heartbeat_packet(),
            build_logged_adif_packet(spot, rst_sent, rst_received),
        ]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            for packet in packets:
                sock.sendto(packet, self.address)


def _uint32(value: int) -> bytes:
    return struct.pack(">I", value)


def _uint64(value: int) -> bytes:
    return struct.pack(">Q", value)


def _bool(value: bool) -> bytes:
    return b"\x01" if value else b"\x00"


def _uint8(value: int) -> bytes:
    return struct.pack(">B", value)


def _qstring(value: str | None) -> bytes:
    if value is None:
        return struct.pack(">i", -1)
    encoded = value.encode("utf-8")
    return struct.pack(">I", len(encoded)) + encoded


def _adif_field(name: str, value: str) -> str:
    return f"<{name}:{len(value)}>{value}"
