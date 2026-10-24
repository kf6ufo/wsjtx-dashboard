"""Dependency-free, server-owned Wavelog configuration."""
from dataclasses import asdict, dataclass, field
from urllib.parse import urlsplit


def application_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) <= 32 for c in value):
        raise ValueError('Enter the Wavelog application URL')
    if not value:
        return ''
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError()
        parsed.port
        if any(part in ('.', '..') for part in parsed.path.split('/')):
            raise ValueError()
    except ValueError:
        raise ValueError('Use an HTTP(S) application URL without credentials or query parameters') from None
    value = value.rstrip('/')
    for suffix in ('/api/v2', '/api'):
        if value.endswith(suffix):
            value = value[:-len(suffix)]
            break
    return value


@dataclass(frozen=True)
class WavelogSettings:
    enabled: bool = False
    url: str = ''
    token: str = field(default='', repr=False)
    scope_mode: str = 'all'
    station_ids: list[int] = field(default_factory=list)
    logbook_id: int = 0
    cache_minutes: int = 5
    cache_limit: int = 20
    page_size: int = 100
    max_pages: int = 100
    max_records: int = 10000
    timeout_seconds: int = 8

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise ValueError('Enabled must be true or false')
        object.__setattr__(self, 'url', application_url(self.url))
        if not isinstance(self.token, str) or len(self.token) > 4096 or any(ord(c) <= 32 for c in self.token):
            raise ValueError('Invalid Wavelog token')
        if self.token and not self.token.startswith('wl2_'):
            raise ValueError('Use a Wavelog API v2 token (wl2_), not a legacy API key')
        if self.scope_mode not in ('all', 'stations', 'logbook'):
            raise ValueError('Choose all locations, selected locations, or a logbook')
        if not isinstance(self.station_ids, list) or len(self.station_ids) > 200 or any(type(i) is not int or i < 1 for i in self.station_ids):
            raise ValueError('Station IDs must be positive integers')
        object.__setattr__(self, 'station_ids', sorted(set(self.station_ids)))
        for key, low, high in (('logbook_id', 0, 2147483647), ('cache_minutes', 1, 60), ('cache_limit', 1, 100),
            ('page_size', 10, 500), ('max_pages', 1, 1000), ('max_records', 1, 50000), ('timeout_seconds', 2, 30)):
            number = getattr(self, key)
            if type(number) is not int or not low <= number <= high:
                raise ValueError(f'{key} must be {low}–{high}')
        if self.scope_mode == 'stations' and not self.station_ids:
            raise ValueError('Select at least one station location')
        if self.scope_mode == 'logbook' and not self.logbook_id:
            raise ValueError('Select a logbook')

    def public(self):
        return {key: value for key, value in asdict(self).items() if key != 'token'} | {'token_configured': bool(self.token)}


def update_wavelog_settings(old, payload):
    if not isinstance(payload, dict) or set(payload) - set(asdict(old)) - {'clear_token'}:
        raise ValueError('Unknown Wavelog setting')
    values = asdict(old)
    for key, value in payload.items():
        if key == 'clear_token':
            if type(value) is not bool:
                raise ValueError('Clear token must be true or false')
        elif key != 'token' or value != '':
            values[key] = value
    if payload.get('clear_token'):
        values['token'] = ''
    return WavelogSettings(**values)
