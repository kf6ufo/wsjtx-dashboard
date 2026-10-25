"""Optional history and delivery settings. Existing installs remain read-only."""
from dataclasses import asdict, dataclass, field
from pathlib import Path
from decimal import Decimal, InvalidOperation
from .state import normalize_call


@dataclass(frozen=True)
class QsoSettings:
    history_source: str = 'auto'
    adif_path: str = ''
    adif_complete: bool = False
    logging_enabled: bool = False
    log_to_wavelog: bool = False
    recovery_seconds: int = 30
    rigs: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.history_source not in ('auto', 'wavelog', 'adif'):
            raise ValueError('Choose automatic, Wavelog or ADIF history')
        for key in ('adif_complete', 'logging_enabled', 'log_to_wavelog'):
            if type(getattr(self, key)) is not bool: raise ValueError('Checkbox settings must be boolean')
        if not isinstance(self.adif_path, str) or len(self.adif_path) > 4096 or any(ord(c) < 32 for c in self.adif_path):
            raise ValueError('Invalid ADIF path')
        if self.adif_path and (not Path(self.adif_path).is_absolute() or Path(self.adif_path).suffix.lower() not in ('.adi', '.adif')):
            raise ValueError('Use an absolute .adi or .adif path')
        if type(self.recovery_seconds) is not int or not 5 <= self.recovery_seconds <= 3600:
            raise ValueError('Recovery interval must be 5–3600 seconds')
        if not isinstance(self.rigs, list) or len(self.rigs) > 32: raise ValueError('At most 32 rig mappings are supported')
        ids = set()
        for row in self.rigs:
            if not isinstance(row, dict) or set(row) != {'id', 'station_callsign', 'operator', 'wavelog_station_id', 'tx_power'}:
                raise ValueError('Invalid rig mapping')
            if not isinstance(row['id'], str) or not 1 <= len(row['id']) <= 128 or any(ord(c) < 32 for c in row['id']) or row['id'] in ids:
                raise ValueError('Use unique WSJT-X network IDs')
            ids.add(row['id'])
            for key in ('station_callsign', 'operator'):
                if not isinstance(row[key], str) or (row[key] and normalize_call(row[key]) != row[key]): raise ValueError('Use normalized station/operator callsigns')
            if type(row['wavelog_station_id']) is not int or not 0 <= row['wavelog_station_id'] <= 2147483647: raise ValueError('Invalid station location ID')
            try:
                power = row['tx_power']
                if not isinstance(power, str) or (power and (not Decimal(power).is_finite() or not 0 <= Decimal(power) <= 100000)):
                    raise ValueError('Invalid configured transmit power')
            except InvalidOperation: raise ValueError('Invalid configured transmit power') from None

    def public(self): return asdict(self)


def update_qso_settings(old, payload):
    if not isinstance(payload, dict) or set(payload) - set(asdict(old)): raise ValueError('Unknown QSO setting')
    return QsoSettings(**(asdict(old) | payload))
