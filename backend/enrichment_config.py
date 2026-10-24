"""Dependency-free enrichment configuration, also used before installation."""
from dataclasses import asdict, dataclass, field
import re

PROVIDERS = {'countryfile': 'Country-files.com', 'clublogxml': 'Club Log XML', 'clublogapi': 'Club Log API', 'qrz': 'QRZ XML'}
SECRET_KEYS = ('clublog_key', 'qrz_username', 'qrz_password')


def grid(value):
    value = value.strip().upper()
    if value and not re.fullmatch(r'[A-R]{2}[0-9]{2}(?:[A-X]{2}(?:[0-9]{2})?)?', value):
        raise ValueError('Use a 4, 6 or 8 character Maidenhead grid, or leave it empty')
    return value


@dataclass(frozen=True)
class EnrichmentSettings:
    enabled: bool = False
    source: str = 'countryfile'
    filename: str = ''
    station_grid: str = ''
    refresh_hours: int = 24
    cache_minutes: int = 1440
    cache_limit: int = 200
    qrz_enabled: bool = False
    qrz_version: str = 'current'
    field_priority: str = 'qrz_first'
    allow_country_estimate: bool = False
    clublog_key: str = field(default='', repr=False)
    qrz_username: str = field(default='', repr=False)
    qrz_password: str = field(default='', repr=False)

    def __post_init__(self):
        for key in ('enabled', 'qrz_enabled', 'allow_country_estimate'):
            if type(getattr(self, key)) is not bool:
                raise ValueError(f'{key} must be true or false')
        if self.source not in PROVIDERS or self.field_priority not in ('qrz_first', 'source_first'):
            raise ValueError('Choose a supported source and field priority')
        for key, low, high in (('refresh_hours', 1, 720), ('cache_minutes', 1, 10080), ('cache_limit', 20, 1000)):
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f'{key} must be {low}–{high}')
        for key in ('filename', 'station_grid', 'qrz_version', *SECRET_KEYS):
            value = getattr(self, key)
            if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 for c in value):
                raise ValueError(f'Invalid {key}')
        grid(self.station_grid)
        if not re.fullmatch(r'current|1\.\d{1,2}(?:\.\d)?', self.qrz_version):
            raise ValueError('QRZ version must be current or a supported 1.xx version')

    def public(self):
        return {k: v for k, v in asdict(self).items() if k not in SECRET_KEYS} | {
            f'{key}_configured': bool(getattr(self, key)) for key in SECRET_KEYS}


def update_settings(old, payload):
    """Empty secret fields mean keep; explicit clear flags mean remove."""
    if not isinstance(payload, dict) or set(payload) - set(asdict(old)) - {f'clear_{k}' for k in SECRET_KEYS}:
        raise ValueError('Unknown enrichment setting')
    values = asdict(old)
    for key, value in payload.items():
        if key.startswith('clear_'):
            if type(value) is not bool:
                raise ValueError('Clear flags must be true or false')
        elif key not in SECRET_KEYS or value != '':
            values[key] = value
    for key in SECRET_KEYS:
        if payload.get(f'clear_{key}'):
            values[key] = ''
    if not isinstance(values['station_grid'], str):
        raise ValueError('Station grid must be text')
    values['station_grid'] = grid(values['station_grid'])
    return EnrichmentSettings(**values)


