"""Opt-in one-way WSJT-X destinations. No third-party write credentials."""
from dataclasses import dataclass, field, asdict
import ipaddress
import re

# Receive-side notifications only; never forward radio-control commands.
PACKET_TYPES = {0: 'Heartbeat', 1: 'Status', 2: 'Decode', 3: 'Clear', 5: 'QSO Logged', 6: 'Close', 10: 'WSPR Decode', 12: 'Logged ADIF'}


@dataclass(frozen=True)
class ForwardingSettings:
    destinations: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.destinations, list) or len(self.destinations) > 16:
            raise ValueError('At most 16 forwarding destinations are supported')
        ids = set()
        for row in self.destinations:
            if not isinstance(row, dict) or set(row) != {'id', 'name', 'enabled', 'host', 'port', 'rigs', 'packets', 'format'}:
                raise ValueError('Invalid forwarding destination')
            if not isinstance(row['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', row['id']) or row['id'] in ids:
                raise ValueError('Use unique destination IDs')
            ids.add(row['id'])
            if not isinstance(row['name'], str) or not 1 <= len(row['name'].strip()) <= 80 or any(ord(c) < 32 for c in row['name']):
                raise ValueError('Use a descriptive destination name')
            if type(row['enabled']) is not bool: raise ValueError('Destination enabled must be boolean')
            host = row['host']
            if not isinstance(host, str) or len(host) > 253 or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host):
                raise ValueError('Use an IPv4 address or hostname, without a URL or port')
            try:
                address = ipaddress.IPv4Address(host)
                if address.is_multicast or address.is_unspecified or address.is_reserved or str(address).endswith('.255'):
                    raise ValueError('Forwarding requires a unicast destination')
            except ipaddress.AddressValueError:
                if all(c.isdigit() or c == '.' for c in host): raise ValueError('Invalid IPv4 destination')
            if type(row['port']) is not int or not 1024 <= row['port'] <= 65535: raise ValueError('Use an unprivileged UDP port')
            if not isinstance(row['rigs'], list) or len(row['rigs']) > 32 or any(not isinstance(r, str) or not 1 <= len(r) <= 128 or any(ord(c) < 32 for c in r) for r in row['rigs']):
                raise ValueError('Use exact WSJT-X network IDs for rig filters')
            if not isinstance(row['packets'], list) or not row['packets'] or len(row['packets']) != len(set(row['packets'])) or any(type(p) is not int or p not in PACKET_TYPES for p in row['packets']):
                raise ValueError('Select supported receive-side packet types')
            if row['format'] not in ('raw', 'enriched-adif'): raise ValueError('Choose original WSJT-X or enriched Logged ADIF')
            if row['format'] == 'enriched-adif' and 5 in row['packets'] and 12 not in row['packets']:
                raise ValueError('Enriched QSO forwarding needs Logged ADIF type 12; paired type 5 is suppressed')

    def public(self): return asdict(self)
