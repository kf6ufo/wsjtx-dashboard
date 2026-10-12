"""Minimal WSJT-X schema 2/3 reader; no Qt dependency or outbound commands.

Field encoding verified against Network/NetworkMessage.hpp and the local
wsjtx-station-utility Reader/parse_status/parse_decode implementation.
"""
from dataclasses import dataclass
import math
import struct


class PacketError(ValueError):
    pass


class Reader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def take(self, size: int) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise PacketError("truncated packet")
        value = self.data[self.pos:self.pos + size]
        self.pos += size
        return value

    def number(self, fmt: str):
        return struct.unpack('!' + fmt, self.take(struct.calcsize('!' + fmt)))[0]

    def boolean(self):
        value = self.number('B')
        if value not in (0, 1):
            raise PacketError("invalid boolean")
        return bool(value)

    def text(self, limit=4096) -> str:
        size = self.number('I')
        if size == 0xffffffff:
            return ''
        if size > limit:
            raise PacketError("oversized string")
        try:
            return self.take(size).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise PacketError("invalid UTF-8") from exc


@dataclass(frozen=True)
class Packet:
    kind: int
    rig_id: str
    dx_call: str = ''
    frequency: int = 0
    mode: str = ''


def parse_packet(data: bytes) -> Packet:
    if len(data) > 65507:
        raise PacketError("oversized datagram")
    r = Reader(data)
    if r.number('I') != 0xADBCCBDA:
        raise PacketError("invalid magic")
    if r.number('I') not in (2, 3):
        raise PacketError("unsupported schema")
    kind, rig_id = r.number('I'), r.text(128)
    if not rig_id.strip() or any(ord(c) < 32 or ord(c) == 127 for c in rig_id):
        raise PacketError("invalid network ID")
    if kind == 1:
        frequency, mode, call = r.number('Q'), r.text(64), r.text(64)
        r.text(64)  # Report
        r.text(64)  # Tx mode
        for _ in range(3):
            r.boolean()
        r.number('I')  # Rx DF
        r.number('I')  # Tx DF
        for _ in range(3):
            r.text(128)  # DE call, DE grid, DX grid
        # Later Status fields are append-only. We deliberately consume just
        # the stable mandatory prefix and ignore extensions (including future ones).
        return Packet(kind, rig_id, call, frequency, mode)
    if kind == 2:
        r.boolean()
        milliseconds = r.number('I')
        r.number('i')  # SNR
        dt = r.number('d')
        r.number('I')  # DF
        r.text(64)
        r.text()
        if milliseconds >= 86400000 or not math.isfinite(dt):
            raise PacketError("invalid decode fields")
        # No decoded text is retained or used to select a station.
    # Heartbeat, Close, unknown types and QSO messages have no interpreted
    # payload here. In particular, types 5 and 12 never submit/store a QSO.
    return Packet(kind, rig_id)


def band_from_hz(frequency: int) -> str | None:
    ranges = [(1800000, 2000000, '160m'), (3500000, 4000000, '80m'),
              (5300000, 5500000, '60m'), (7000000, 7300000, '40m'),
              (10100000, 10150000, '30m'), (14000000, 14350000, '20m'),
              (18068000, 18168000, '17m'), (21000000, 21450000, '15m'),
              (24890000, 24990000, '12m'), (28000000, 29700000, '10m'),
              (50000000, 54000000, '6m'), (144000000, 148000000, '2m'),
              (222000000, 225000000, '1.25m'), (420000000, 450000000, '70cm'),
              (902000000, 928000000, '33cm'), (1240000000, 1300000000, '23cm')]
    return next((name for low, high, name in ranges if low <= frequency <= high), None)
