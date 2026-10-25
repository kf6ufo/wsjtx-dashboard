"""Minimal WSJT-X schema 2/3 reader; no Qt dependency or outbound commands.

Field encoding verified against Network/NetworkMessage.hpp and the local
wsjtx-station-utility Reader/parse_status/parse_decode implementation.
"""
from dataclasses import dataclass, field
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
    schema: int = field(default=2, compare=False)
    fields: dict = field(default_factory=dict, compare=False)


def read_header(data: bytes):
    if len(data) > 65507:
        raise PacketError("oversized datagram")
    r = Reader(data)
    if r.number('I') != 0xADBCCBDA:
        raise PacketError("invalid magic")
    schema, kind, rig_id = r.number('I'), r.number('I'), r.text(128)
    if not rig_id.strip() or any(ord(c) < 32 or ord(c) == 127 for c in rig_id):
        raise PacketError("invalid network ID")
    return r, schema, kind, rig_id


def diagnostic_header(data: bytes):
    # A trustworthy header can still identify a malformed payload/unknown schema.
    try:
        _reader, schema, kind, rig_id = read_header(data)
        return dict(schema=schema, kind=kind, instance=rig_id)
    except PacketError:
        return {}


def parse_packet(data: bytes) -> Packet:
    r, schema, kind, rig_id = read_header(data)
    if schema not in (2, 3):
        raise PacketError("unsupported schema")
    fields = {}
    if kind == 0 and r.pos < len(data):
        fields['maximumSchema'] = r.number('I')
        fields['version'] = r.text(128)
        fields['revision'] = r.text(128)
    if kind == 1:
        frequency, mode, call = r.number('Q'), r.text(64), r.text(64)
        fields.update(frequency=frequency, mode=mode, dxCall=call, report=r.text(64), txMode=r.text(64))
        for name in ('txEnabled', 'transmitting', 'decoding'):
            fields[name] = r.boolean()
        fields['rxDf'], fields['txDf'] = r.number('I'), r.number('I')
        for name in ('deCall', 'deGrid', 'dxGrid'):
            fields[name] = r.text(128)
        # Status extensions are append-only. Preserve original bytes for details.
        return Packet(kind, rig_id, call, frequency, mode, schema, fields)
    if kind == 2:
        fields['new'] = r.boolean()
        milliseconds = fields['milliseconds'] = r.number('I')
        fields['snr'] = r.number('i')
        dt = fields['deltaTime'] = r.number('d')
        fields['deltaFrequency'] = r.number('I')
        fields['mode'], fields['message'] = r.text(64), r.text()
        if milliseconds >= 86400000 or not math.isfinite(dt):
            raise PacketError("invalid decode fields")
    if kind == 12:
        fields['adif'] = r.text(65000)
        if r.pos != len(data): raise PacketError('Unexpected Logged ADIF payload tail')
    # Other message payloads remain uninterpreted, bounded diagnostic bytes only.
    # Type 5 is not an observation/submission; type 12 feeds shared observation
    # and independently opted-in delivery/forwarding services.
    return Packet(kind, rig_id, schema=schema, fields=fields)


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
