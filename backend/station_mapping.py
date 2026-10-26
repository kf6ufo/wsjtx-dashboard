"""Exact callsign-to-authorized-location matching; no network or submission."""
from .state import normalize_call
from .qso_model import QsoError


def station_identity(fields, profile, verified_call=''):
    raw = fields.get('STATION_CALLSIGN') or profile.get('station_callsign') or verified_call
    call = normalize_call(raw or '')
    if not call: raise QsoError('Station callsign is missing or invalid; select a verified station identity.')
    return call


def resolve_station(fields, profile, stations):
    call = station_identity(fields, profile)
    authorized = {s['id']: s for s in stations}
    override = profile.get('wavelog_station_id', 0)
    if override:
        station = authorized.get(override)
        if not station: raise QsoError('The explicit Wavelog location override is not in the authorized location list.')
        if normalize_call(station.get('callsign', '')) != call:
            raise QsoError('Station callsign does not match the explicit Wavelog location override.')
        return station, 'override'
    matches = [s for s in authorized.values() if normalize_call(s.get('callsign', '')) == call]
    if len(matches) > 1: raise QsoError(f'Multiple authorized Wavelog locations match {call}; select a location override.')
    if not matches: raise QsoError(f'No authorized Wavelog location matches {call}; refresh locations or select an override.')
    return matches[0], 'automatic'
