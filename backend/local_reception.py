"""Bounded, volatile local Decode evidence, independent of focus/history/logging."""
import re
import time
from .protocol import band_from_hz
from .state import normalize_call

MAX_AGE = 3600000
CACHE_LIMIT = 2000
GRID = re.compile(r'[A-R]{2}[0-9]{2}(?:[A-X]{2}(?:[0-9]{2}(?:[A-X]{2})?)?)?')


def grid(raw):
    value = raw.strip().upper() if isinstance(raw, str) else ''
    return value if GRID.fullmatch(value) else ''


def decoded_station(message):
    """Only unambiguous standard CQ/QRZ and two-call exchanges; never free text."""
    if not isinstance(message, str) or not message.isascii() or len(message) > 100 or any(ord(c) < 32 for c in message): return None
    words = message.strip().upper().split()
    if len(words) not in (3, 4): return None
    def call(word):
        value = normalize_call(word[1:-1] if word.startswith('<') and word.endswith('>') else word)
        return value if value and not grid(value) and value not in ('RR73', 'RRR') else None
    if words[0] in ('CQ', 'QRZ'):
        if len(words) == 4 and not re.fullmatch(r'[A-Z]{1,4}|[0-9]{3}', words[1]): return None
        sender, locator = call(words[-2]), grid(words[-1])
        return (sender, locator) if sender and locator else None
    if not call(words[0]) or not call(words[1]): return None
    if len(words) == 4 and words[2] != 'R': return None
    locator = '' if words[-1] == 'RR73' else grid(words[-1])
    if not locator and not (len(words) == 3 and re.fullmatch(r'R?[+-][0-9]{1,2}|RRR|RR73|73', words[-1])): return None
    return call(words[1]), locator


class LocalReceptionCache:
    def __init__(self, *, limit=CACHE_LIMIT, clock=None):
        self.clock = clock or (lambda: int(time.time() * 1000))
        self.limit, self.evicted = limit, 0
        self.contexts, self.spots = {}, {}
        self.last_prune = 0

    def capture(self, packet, history=(), *, at=None):
        now = self.clock() if at is None else at
        if now - self.last_prune >= 10000:
            self.spots = {key: spot for key, spot in self.spots.items() if now - spot['heardAt'] < MAX_AGE}
            self.last_prune = now
        if packet.kind in (3, 6):
            self.spots = {key: spot for key, spot in self.spots.items() if spot['rigId'] != packet.rig_id}
            if packet.kind == 6: self.contexts.pop(packet.rig_id, None)
            return
        if packet.kind == 1:
            if packet.rig_id not in self.contexts and len(self.contexts) >= 32: return
            fields = packet.fields
            raw = fields.get('deCall')
            identity = normalize_call(raw) if isinstance(raw, str) else None
            band = band_from_hz(packet.frequency)
            previous = self.contexts.get(packet.rig_id, {})
            same = (previous.get('stationCall'), previous.get('band'), previous.get('mode')) == (identity, band, packet.mode)
            self.contexts[packet.rig_id] = dict(stationCall=identity, band=band, mode=packet.mode[:16],
                at=now, since=previous['since'] if same else now,
                dxCall=normalize_call(packet.dx_call), dxGrid=grid(fields.get('dxGrid')))
            return
        fields, context = packet.fields, self.contexts.get(packet.rig_id)
        if packet.kind != 2 or not context or not context['stationCall'] or not context['band'] or now - context['at'] > 90000: return
        # Require explicit live/high-confidence flags. Legacy/ambiguous payloads
        # still follow the original diagnostic/forwarding path, without map proof.
        if fields.get('new') is not True or fields.get('offAir') is not False or fields.get('lowConfidence') is not False: return
        milliseconds = fields.get('milliseconds')
        if type(milliseconds) is not int or not 0 <= milliseconds < 86400000: return
        today = now - now % 86400000 + milliseconds
        heard = min((today - 86400000, today, today + 86400000), key=lambda value: abs(value - now))
        if now - heard >= MAX_AGE or heard > now + 30000 or heard < context['since'] - 30000: return
        parsed = decoded_station(fields.get('message'))
        if not parsed: return
        call, locator = parsed
        if call == context['stationCall']: return
        key = (packet.rig_id, context['stationCall'], context['band'], call)
        previous = self.spots.get(key)
        if previous and previous['heardAt'] >= heard: return
        source, grid_at = 'WSJT-X Decode', heard
        if not locator:
            if call == context['dxCall'] and context['dxGrid']:
                locator, source = context['dxGrid'], 'WSJT-X Status'
            elif previous and now - previous['gridAt'] < MAX_AGE:
                locator, source, grid_at = previous['grid'], previous['gridSource'], previous['gridAt']
            else:
                entry = next((e for e in history if e['call'] == call and e.get('rigId') == packet.rig_id
                    and e.get('stationCall') == context['stationCall'] and e.get('band') == context['band']
                    and 0 <= now - e['selectedAt'] < MAX_AGE and grid(e.get('dxGrid'))), None)
                if entry: locator, source, grid_at = grid(entry['dxGrid']), 'Recent WSJT-X selection', entry['selectedAt']
        if not locator: return
        mode = context['mode']
        # Avoid applying a stale mode context to the common FT8/FT4 symbols.
        decoded_mode = {'~': 'FT8', '+': 'FT4'}.get(fields.get('mode'))
        if decoded_mode and decoded_mode != mode.upper(): return
        snr = fields.get('snr')
        self.spots[key] = dict(call=call, rigId=packet.rig_id, stationCall=context['stationCall'], band=context['band'],
            grid=locator, gridAt=grid_at, gridSource=source, mode=mode, heardAt=heard, snr=snr if type(snr) is int and -100 <= snr <= 100 else None)
        if len(self.spots) > self.limit:
            del self.spots[min(self.spots, key=lambda key: self.spots[key]['heardAt'])]
            self.evicted += 1

    def snapshot(self, call, history, rigs):
        entry = next((entry for entry in history if entry['call'] == call), {})
        identity = entry.get('stationCall') or rigs.get(entry.get('rigId'), {}).get('stationCall', '')
        now = self.clock()
        return dict(evicted=self.evicted, spots=[dict(spot) for spot in self.spots.values()
            if spot['rigId'] == entry.get('rigId') and spot['band'] == entry.get('band')
            and spot['stationCall'] == identity and now - spot['heardAt'] < MAX_AGE])
