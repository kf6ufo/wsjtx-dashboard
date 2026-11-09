"""Synthetic protocol datagrams, not recordings from an operator log."""
import struct


def text(value):
    if value is None:
        return struct.pack('!I', 0xffffffff)
    encoded = value.encode()
    return struct.pack('!I', len(encoded)) + encoded


def header(rig='WSJT-X - A', kind=1, schema=2):
    return struct.pack('!III', 0xADBCCBDA, schema, kind) + text(rig)


def status(call='JA2HDE', rig='WSJT-X - A', hz=14074000, schema=2, extensions=True, station='N0TEST', grid='PM85', mode='FT8'):
    # Documented stable prefix through DX grid, followed by append-only fields.
    core = (header(rig, schema=schema) + struct.pack('!Q', hz) + text(mode) + text(call)
            + text('-10') + text(mode) + b'\x00\x00\x01'
            + struct.pack('!II', 1200, 1500) + text(station) + text('AA00') + text(grid))
    return core + (b'\x00' + text('') + b'\x00\x00' + struct.pack('!II', 50, 15) + text('Default') + text('CQ N0TEST AA00') if extensions else b'')


def decode(rig='WSJT-X - A', message='CQ W7DEMO AA00', milliseconds=12345000, new=True, snr=-12, mode='~', low_confidence=False, off_air=False):
    return header(rig, 2) + bytes([new]) + struct.pack('!IidI', milliseconds, snr, .2, 1200) + text(mode) + text(message) + bytes([low_confidence, off_air])
