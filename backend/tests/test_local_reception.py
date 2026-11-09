"""Offline map evidence only; fixture bytes never target a station service."""
import pytest
from backend.local_reception import LocalReceptionCache, decoded_station
from backend.protocol import parse_packet
from backend.workspace import WorkspaceState
from .fixtures import decode, status, header

NOW = 1794139200000  # Fixed UTC midday.


def ready(cache, *, rig='A', station='N0CALL', hz=14074000, call='K1FOCUS', grid='FN31', at=NOW):
    cache.capture(parse_packet(status(rig=rig, station=station, hz=hz, call=call, grid=grid)), at=at)


def hear(cache, *, at=NOW, **fields):
    fields = dict(rig='A', message='CQ K2NEAR FN32', milliseconds=at % 86400000) | fields
    cache.capture(parse_packet(decode(**fields)), at=at)


@pytest.mark.parametrize('message,expected', [
    ('CQ K1ABC FN31', ('K1ABC', 'FN31')), ('cq dx k1abc fn31pr', ('K1ABC', 'FN31PR')),
    ('CQ 123 K1ABC FN31', ('K1ABC', 'FN31')), ('QRZ K1ABC/P FN31', ('K1ABC/P', 'FN31')),
    ('N0CALL K1ABC FN31', ('K1ABC', 'FN31')), ('N0CALL <K1ABC/P> R FN31', ('K1ABC/P', 'FN31')),
    ('N0CALL K1ABC R-12', ('K1ABC', '')), ('N0CALL K1ABC RR73', ('K1ABC', '')),
    ('HELLO K1ABC FN31', None), ('CQ FN31 FN32', None), ('CQ <...> FN31', None),
    ('CQ K1ABC ZZ99', None), ('CQ K1ABC FN31; K2ABC RR73', None), ('CQ K1ABC FN31\n', None),
    ('N0CALL K1ABC HELLO', None), ('N0CALL K1ABC-888 FN31', None), ('TNX 73', None),
])
def test_conservative_standard_message_extraction(message, expected):
    assert decoded_station(message) == expected


def test_capture_dedupes_latest_scopes_context_and_never_fills_focus_history(tmp_path):
    clock = [NOW]
    cache = LocalReceptionCache(clock=lambda: clock[0])
    ready(cache)
    hear(cache)
    hear(cache, snr=-30)  # Same report time cannot replace the first report.
    hear(cache, at=NOW+1000, snr=-8)
    ready(cache, rig='B')
    hear(cache, rig='B', at=NOW+2000)
    ready(cache, rig='C', station='N0CALL/P')
    hear(cache, rig='C', at=NOW+3000)
    ready(cache, rig='D', hz=21074000)
    hear(cache, rig='D', at=NOW+4000)
    history = [dict(call='K1FOCUS', rigId='A', stationCall='N0CALL', band='20m')]
    snapshot = cache.snapshot('K1FOCUS', history, {})
    assert len(snapshot['spots']) == 1 and snapshot['spots'][0]['snr'] == -8
    assert snapshot['spots'][0]['rigId'] == 'A' and snapshot['spots'][0]['grid'] == 'FN32'
    snapshot['spots'][0]['grid'] = 'AA00'
    assert cache.snapshot('K1FOCUS', history, {})['spots'][0]['grid'] == 'FN32'
    assert not cache.snapshot('K2UNKNOWN', history, {})['spots']

    state = WorkspaceState(tmp_path/'workspace.sqlite3'); state.enter_radio_workspace()
    state.local_receptions = LocalReceptionCache(clock=lambda: NOW)
    state.accept(parse_packet(status(call='N0BASE', rig='A', station='N0CALL')), at=NOW)
    state.accept(parse_packet(status(call='K1FOCUS', rig='A', station='N0CALL', grid='FN31')), at=NOW)
    before, changes = state.snapshot(), state.database.total_changes
    state.accept(parse_packet(decode(rig='A', message='CQ K2NEAR FN32', milliseconds=NOW % 86400000)), at=NOW)
    assert state.call == before['call'] and state.history == before['history']
    assert state.database.total_changes == changes
    assert state.snapshot()['localReceptions']['spots'][0]['call'] == 'K2NEAR'
    state.clear_diagnostics()
    assert state.snapshot()['localReceptions']['spots']
    payload = state.database.execute('SELECT payload FROM live_workspace WHERE id=1').fetchone()[0]
    assert 'K2NEAR' not in payload and 'localReceptions' not in payload
    state.close()
    restarted = WorkspaceState(tmp_path/'workspace.sqlite3')
    assert restarted.snapshot()['localReceptions']['spots'] == []
    restarted.close()


@pytest.mark.parametrize('changes', [dict(new=False), dict(off_air=True), dict(low_confidence=True),
    dict(milliseconds=(NOW-3600001) % 86400000), dict(milliseconds=(NOW+31000) % 86400000),
    dict(message='CQ K2NEAR ZZ99'), dict(message='HELLO WORLD'), dict(mode='+')])
def test_unsupported_stale_replayed_playback_and_ambiguous_decodes_are_not_evidence(changes):
    cache = LocalReceptionCache(clock=lambda: NOW)
    ready(cache)
    hear(cache, **changes)
    assert not cache.spots


def test_requires_current_status_identity_and_handles_utc_midnight():
    cache = LocalReceptionCache(clock=lambda: NOW)
    hear(cache)
    assert not cache.spots
    ready(cache, station='')
    hear(cache)
    assert not cache.spots
    ready(cache, at=NOW-90001)
    hear(cache)
    assert not cache.spots
    midnight = NOW - NOW % 86400000
    cache = LocalReceptionCache(clock=lambda: midnight+5000)
    ready(cache, at=midnight-10000)
    hear(cache, at=midnight+5000, milliseconds=86399000)
    assert next(iter(cache.spots.values()))['heardAt'] == midnight-1000
    cache = LocalReceptionCache()
    ready(cache, at=NOW)
    ready(cache, at=NOW+60000, hz=21074000)
    hear(cache, at=NOW+60000, milliseconds=NOW % 86400000)
    assert not cache.spots  # Do not assign an earlier-band decode to a new context.


def test_grid_fallback_requires_exact_recent_evidence_and_expires_grid_independently():
    cache = LocalReceptionCache(clock=lambda: NOW)
    ready(cache, grid='')
    hear(cache, message='N0CALL K2NEAR -10')
    assert not cache.spots
    hear(cache)
    hear(cache, message='N0CALL K2NEAR -10', at=NOW+1000)
    spot = next(iter(cache.spots.values()))
    assert spot['grid'] == 'FN32' and spot['gridAt'] == NOW
    ready(cache, at=NOW+3599000, grid='')
    hear(cache, message='N0CALL K2NEAR -9', at=NOW+3599000)
    assert next(iter(cache.spots.values()))['gridAt'] == NOW
    ready(cache, at=NOW+3601000, grid='')
    hear(cache, message='N0CALL K2NEAR -8', at=NOW+3601000)
    assert next(iter(cache.spots.values()))['heardAt'] == NOW+3599000
    ready(cache, call='K3FOCUS', grid='FN33')
    hear(cache, message='N0CALL K3FOCUS -12')
    assert any(spot['gridSource'] == 'WSJT-X Status' for spot in cache.spots.values())
    history = [dict(call='K4HISTORY', rigId='A', stationCall='N0CALL', band='20m', selectedAt=NOW-60000, dxGrid='FN34')]
    packet = parse_packet(decode(rig='A', message='N0CALL K4HISTORY RR73', milliseconds=NOW % 86400000))
    cache.capture(packet, history, at=NOW)
    assert any(spot['gridSource'] == 'Recent WSJT-X selection' for spot in cache.spots.values())


def test_capacity_expiry_clear_close_and_legacy_flags():
    clock = [NOW]; cache = LocalReceptionCache(limit=2, clock=lambda: clock[0])
    ready(cache)
    for index in range(3): hear(cache, message=f'CQ K{index+2}NEAR FN32', at=NOW+index*1000)
    assert len(cache.spots) == 2 and cache.evicted == 1
    clock[0] = NOW+3601000
    history = [dict(call='K1FOCUS', rigId='A', stationCall='N0CALL', band='20m')]
    assert len(cache.snapshot('K1FOCUS', history, {})['spots']) == 1
    cache.capture(parse_packet(header(rig='A', kind=3)))
    assert not cache.spots
    ready(cache); hear(cache)
    cache.capture(parse_packet(header(rig='A', kind=6)))
    assert not cache.spots and not cache.contexts
    ready(cache)
    for raw in [decode(rig='A')[:-2], decode(rig='A')[:-1], decode(rig='A')[:-2]+b'\x02\x00']:
        packet = parse_packet(raw)  # Preserve the pre-existing parser/forwarding acceptance.
        cache.capture(packet, at=NOW)
    assert not cache.spots
