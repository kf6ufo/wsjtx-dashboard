import asyncio
from unittest.mock import Mock, AsyncMock
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.protocol import PacketError, parse_packet, band_from_hz
from backend.receiver import Settings, create_socket, ingest, receive
from backend.state import FocusState
from .fixtures import status, decode, header


def test_schema_fixtures_and_optional_extensions():
    for schema in (2, 3):
        packet = parse_packet(status(schema=schema))
        assert (packet.rig_id, packet.dx_call, packet.frequency, packet.mode) == ('WSJT-X - A', 'JA2HDE', 14074000, 'FT8')
        assert parse_packet(status(schema=schema, extensions=False)) == packet
        assert parse_packet(status(schema=schema) + b'future trailing fields') == packet
    assert parse_packet(status(call=None)).dx_call == ''
    assert parse_packet(decode()).kind == 2
    assert band_from_hz(24915000) == '12m'
    assert band_from_hz(28074000) == '10m'
    assert band_from_hz(123) is None


def test_truncated_and_malformed_packets_never_mutate_focus():
    s = FocusState()
    ingest(status(call='N0BASE'), s); ingest(status(), s)
    before = s.snapshot()
    core = status(extensions=False)
    broken = [core[:i] for i in range(len(core))]
    broken += [b'\0'*20, header(schema=99), header(rig=''), header(rig='bad\nID'),
               header() + b'\xff'*8, header() + b'\0'*8 + b'\xff\xff\xff\xfe',
               header() + b'\0'*8 + b'\0\0\0\x01\xff']
    for data in broken:
        with pytest.raises(PacketError):
            parse_packet(data)
        ingest(data, s)
    assert s.call == before['call']
    assert s.history == before['history']
    assert s.counters['malformed'] == len(broken)


def test_baselines_changes_clears_invalid_and_independent_ids():
    s = FocusState()
    for rig in ('A', 'B', 'C'):
        s.accept(parse_packet(status(call='N0BASE', rig=rig)), at=1)
    assert s.call == '' and s.history == []
    for call in ('N0BASE', ' n0base ', '', '  ', 'bad!', 'CQ', '////'):
        s.accept(parse_packet(status(call=call, rig='A')), at=2)
    assert s.history == []
    s.accept(parse_packet(status(call='ja2hde', rig='A')), at=100)
    s.accept(parse_packet(status(call='DL1DEMO', rig='B', hz=28074000)), at=100)
    s.accept(parse_packet(status(call='JA2HDE', rig='C', hz=21074000)), at=100)
    assert [e['call'] for e in s.history] == ['JA2HDE', 'DL1DEMO']
    assert s.history[0]['rigId'] == 'C' and s.history[0]['band'] == '15m'
    before = s.snapshot()
    s.accept(parse_packet(status(call='JA2HDE', rig='C', hz=7074000)), at=200)
    s.accept(parse_packet(status(call='', rig='C')), at=300)
    assert s.history == before['history'] and s.call == 'JA2HDE'
    s.accept(parse_packet(status(call='JA2HDE', rig='C')), at=400)
    assert s.history[0]['selectedAt'] == 400  # Return after a clear is a change.


def test_passive_messages_and_browsing_preserve_selection_order_provenance():
    s = FocusState()
    ingest(status(call='N0BASE'), s); ingest(status(), s); ingest(status(call='DL1DEMO'), s)
    before = s.snapshot()
    assert s.browse('JA2HDE')
    assert s.call == 'JA2HDE' and s.source == 'browse'
    assert [{k: v for k, v in e.items() if k != 'browsedAt'} for e in s.history] == before['history']
    assert s.rigs == {r['id']: r for r in before['rigs']}
    assert not s.browse('N0MISSING')
    for data in (decode(), header(kind=0), header(kind=5), header(kind=12), header(kind=999)):
        ingest(data, s)
    assert s.call == 'JA2HDE' and s.source == 'browse'
    assert s.counters['decodes'] == 1
    ingest(header(kind=6), s)
    ingest(status(call='W7DEMO'), s)  # Close resets baseline; next Status isn't a selection.
    assert s.call == 'JA2HDE'


def test_bounded_history_rigs_and_full_snapshot_on_reconnect():
    async def exercise():
        s = FocusState(history_limit=2, rig_limit=2)
        queue = s.subscribe()
        assert (await queue.get())['history'] == []
        for rig in ('A', 'B', 'C'):
            ingest(status(call='N0BASE', rig=rig), s)
        assert len(s.rigs) == 2 and s.counters['capacity'] == 1
        for call in ('JA2HDE', 'DL1DEMO', 'W7DEMO'):
            ingest(status(call=call, rig='A'), s)
        assert queue.qsize() == 1
        assert (await queue.get()) == s.snapshot()  # Slow clients receive latest full state.
        s.unsubscribe(queue)
        ingest(status(call='ZS6DEMO', rig='B'), s)
        reconnected = s.subscribe()
        snap = await reconnected.get()
        assert snap == s.snapshot() and [e['call'] for e in snap['history']] == ['ZS6DEMO', 'W7DEMO']
        snap['history'].clear()
        assert len(s.history) == 2
        s.unsubscribe(reconnected)
        assert not s.subscribers
        queues = [s.subscribe() for _ in range(32)]
        with pytest.raises(ValueError):
            s.subscribe()
        for queue in queues:
            s.unsubscribe(queue)
    asyncio.run(exercise())


def test_api_snapshot_navigation_no_injection_route_and_origin_check():
    s = FocusState()
    ingest(status(call='N0BASE'), s); ingest(status(), s)
    with TestClient(create_app(Settings(), s)) as client:
        assert client.get('/api/snapshot').json()['call'] == 'JA2HDE'
        assert client.post('/api/focus', json={'call': 'JA2HDE'}).json()['source'] == 'browse'
        assert client.post('/api/focus', json={'call': 'N0MISSING'}).status_code == 404
        assert client.post('/api/focus', json={'call': 'JA2HDE'}, headers={'Origin': 'https://untrusted.example'}).status_code == 403
        assert client.post('/fixture/packet', json={}).status_code in (404, 405)
        assert s.receiver['status'] == 'disabled'


def test_configuration_and_receive_only_socket(monkeypatch):
    with pytest.raises(ValueError):
        Settings(enabled=True)
    with pytest.raises(ValueError):
        Settings(group='127.0.0.1')
    sock = Mock()
    monkeypatch.setattr('backend.receiver.socket.socket', lambda *args: sock)
    settings = Settings(enabled=True, interface='10.176.1.6')
    assert create_socket(settings) is sock
    sock.bind.assert_called_once_with(('', 2238))
    sock.setblocking.assert_called_once_with(False)
    assert not sock.sendto.called and not sock.connect.called


def test_failed_join_is_visible_without_claiming_reception(monkeypatch):
    def fail(_settings):
        raise OSError('fixture interface unavailable')
    monkeypatch.setattr('backend.app.create_socket', fail)
    with TestClient(create_app(Settings(enabled=True, interface='10.176.1.6'))) as client:
        snapshot = client.get('/api/snapshot').json()
        assert snapshot['receiver']['status'] == 'error'
        assert snapshot['call'] == ''


def test_invalid_initial_status_is_a_baseline_and_receive_loop_survives_bad_data(monkeypatch):
    async def exercise():
        s = FocusState()
        packets = [(status(call='invalid!'), ('127.0.0.1', 1234)),
                   (b'broken', ('127.0.0.1', 1234)),
                   (status(), ('127.0.0.1', 1234)),
                   (decode(), ('127.0.0.1', 1234)), OSError('fixture socket failed')]
        fake_loop = Mock(sock_recvfrom=AsyncMock(side_effect=packets))
        with monkeypatch.context() as patch:
            patch.setattr('backend.receiver.asyncio.get_running_loop', lambda: fake_loop)
            await receive(Mock(), s)
        assert s.call == 'JA2HDE' and len(s.history) == 1
        assert s.counters['malformed'] == 1 and s.counters['decodes'] == 1
        assert s.receiver['status'] == 'error'
    asyncio.run(exercise())
