"""Focus History preferences; contact storage is independent."""
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class HistorySettings:
    limit: int = 200
    retention_days: int = 0

    def __post_init__(self):
        if type(self.limit) is not int or self.limit not in (50, 100, 200, 500):
            raise ValueError('Choose 50, 100, 200 or 500 history entries')
        if type(self.retention_days) is not int or self.retention_days not in (0, 7, 30):
            raise ValueError('Choose manual, 7-day or 30-day history retention')

    def public(self): return asdict(self)
