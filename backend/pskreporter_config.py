"""Read-only PSKReporter reception overlay; older installations remain opt-in."""
from dataclasses import asdict, dataclass
from .state import normalize_call


@dataclass(frozen=True)
class PskReporterSettings:
    enabled: bool = False
    callsign: str = ''
    window_minutes: int = 15

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise ValueError('PSKReporter enabled must be true or false')
        if not isinstance(self.callsign, str) or (self.callsign and normalize_call(self.callsign) != self.callsign):
            raise ValueError('Use an uppercase station callsign or leave it empty for WSJT-X identity')
        if type(self.window_minutes) is not int or self.window_minutes not in (5, 15, 30, 60):
            raise ValueError('Choose 5, 15, 30 or 60 minutes')

    def public(self):
        return asdict(self)
