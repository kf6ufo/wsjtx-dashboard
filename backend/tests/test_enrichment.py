"""Real pyhamtools fixtures and mocked provider HTTP; no station/network writes."""
import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import plistlib
import threading
import time

from fastapi.testclient import TestClient
import pytest
from backend.app import create_app
from backend.config import load_config, save_enrichment_config, save_receiver_config
from backend.enrichment import EnrichmentSettings, EnrichmentService, Providers, QRZLibrary, update_settings
from backend.receiver import Settings, ingest
from backend.workspace import WorkspaceState
from .fixtures import status, decode


@pytest.fixture
def countryfile(tmp_path):
    path = tmp_path / 'fixture.plist'
    entries = {}
    for prefix, country, continent, cq, itu, lat, lon in [
        ('K', 'United States', 'NA', 5, 8, 37.0, 95.0),
        ('DL', 'Fed. Rep. of Germany', 'EU', 14, 28, 51.0, -10.0),
        ('JA', 'Japan', 'AS', 25, 45, 36.0, -138.0)]:
        entries[prefix] = dict(Country=country, Continent=continent, CQZone=cq, ITUZone=itu,
            Latitude=lat, Longitude=lon, ExactCallsign=False)
    path.write_bytes(plistlib.dumps(entries))
    return path


def test_actual_pyhamtools_countryfile_fields_portable_and_grid_priority(tmp_path, countryfile):
    provider = Providers(EnrichmentSettings(enabled=True, filename=str(countryfile), station_grid='CN87'), tmp_path / 'providers')
    result = provider.enrich(dict(call='DL/K1ABC/P', dxGrid='JO62', deGrid='FN31', frequency=14074000))
    assert result['status'] == 'loaded'
    assert result['fields']['adif'] == 230 and result['fields']['cqz'] == 14
    assert result['fields']['longitude'] == 10.0
    assert result['locationGrid'] == 'JO62' and result['reportedGrid'] == 'JO62'
    assert result['stationGrid'] == 'CN87'
    assert 7000 < result['computed']['distanceKm'] < 10000
    assert result['computed']['frequencyBand']['adif'] == '20m'
    assert result['computed']['homeCall'] == 'K1ABC'
    assert result['fieldSources']['country'] == 'Country-files.com'
    assert provider.lookup('countryfile', 'DL/K1ABC/P')['cached']


def test_coordinates_not_passed_off_as_reported_grid_and_cache_is_bounded(tmp_path, countryfile):
    provider = Providers(EnrichmentSettings(enabled=True, filename=str(countryfile), cache_limit=20), tmp_path)
    result = provider.enrich(dict(call='K1ABC'))
    assert not result['locationGrid'] and 'distanceKm' not in result['computed']
    for i in range(30):
        provider.lookup('countryfile', f'K{i}ABC')
    assert len(provider.cache) == 20
    estimate = Providers(replace(provider.settings, allow_country_estimate=True, station_grid='CN87'), tmp_path).enrich(dict(call='K1ABC'))
    assert estimate['reportedGrid'] == '' and 'Approximate' in estimate['locationSource']


def test_provider_failure_does_not_hide_other_provider_or_leak_password(tmp_path, countryfile, monkeypatch):
    settings = EnrichmentSettings(enabled=True, filename=str(countryfile), qrz_enabled=True,
        qrz_username='xmluser', qrz_password='private-pass')
    def failing(*args, **kwargs):
        raise OSError('https://example/?password=private-pass')
    monkeypatch.setattr('backend.enrichment.requests.post', failing)
    result = Providers(settings, tmp_path).enrich(dict(call='K1ABC'))
    assert result['status'] == 'loaded'
    assert result['fields']['country'] == 'United States'
    assert result['providers']['qrz']['status'] == 'error'
    assert 'private-pass' not in json.dumps(result)


class Response:
    is_redirect = False
    def __init__(self, text): self.content = text.encode()
    def raise_for_status(self): pass
    def iter_content(self, _): yield self.content
    def __enter__(self): return self
    def __exit__(self, *args): pass


def test_qrz_secure_post_full_fields_large_serial_and_session_renewal(monkeypatch, tmp_path):
    calls = []
    replies = [
        '<QRZDatabase><Session><Key>secret-session-1</Key><SubExp>2027-01-01</SubExp></Session></QRZDatabase>',
        '<QRZDatabase><Session><Error>Session Timeout</Error></Session></QRZDatabase>',
        '<QRZDatabase><Session><Key>secret-session-2</Key></Session></QRZDatabase>',
        '<QRZDatabase xmlns="http://xmldata.qrz.com"><Callsign><call>K1ABC</call><fname>Test</fname><name>Operator</name><country>United States</country><dxcc>291</dxcc><lat>41</lat><lon>-72</lon><grid>FN31</grid><class>E</class><serial>9876543210123</serial><nickname>T</nickname><attn>Club</attn><expdate>2030-01-01</expdate><eqsl>1</eqsl><image>https://example.invalid/portrait.jpg</image><bio>1234</bio></Callsign><Session><Key>secret-session-2</Key><Message>Fixture notice</Message></Session></QRZDatabase>']
    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response(replies.pop(0))
    monkeypatch.setattr('backend.enrichment.requests.post', post)
    provider = Providers(EnrichmentSettings(source='qrz', qrz_username='xmluser', qrz_password='private-pass'), tmp_path)
    result = provider.enrich(dict(call='K1ABC', dxGrid='JO62', deGrid='CN87'))
    assert result['status'] == 'loaded'
    assert result['fields']['serial'] == '9876543210123'
    assert result['fields']['nickname'] == 'T' and result['fields']['license_class'] == 'E'
    assert result['locationGrid'] == 'JO62' and result['callbookGrid'] == 'FN31'
    assert result['providers']['qrz']['message'] == 'Fixture notice'
    assert all(url == 'https://xmldata.qrz.com/xml/current/' for url, _ in calls)
    assert calls[0][1]['data']['password'] == 'private-pass'
    assert all('private-pass' not in url for url, _ in calls)
    assert 'private-pass' not in json.dumps(result) and 'secret-session' not in json.dumps(result)


def test_qrz_rejects_redirect_and_xml_entities(monkeypatch):
    response = Response('<!DOCTYPE x [<!ENTITY x "bad">]><QRZDatabase/>')
    monkeypatch.setattr('backend.enrichment.requests.post', lambda *a, **k: response)
    with pytest.raises(ValueError):
        QRZLibrary(lookuptype='qrz', username='x', pwd='y')
    response.is_redirect = True
    with pytest.raises(ValueError, match='redirect'):
        QRZLibrary(lookuptype='qrz', username='x', pwd='y')


@pytest.mark.parametrize('changes', [dict(enabled='true'), dict(cache_limit=True), dict(refresh_hours=0),
    dict(cache_minutes=10081), dict(station_grid='ZZ99'), dict(source='unknown'), dict(qrz_version='../bad')])
def test_settings_validation(changes):
    with pytest.raises(ValueError): EnrichmentSettings(**changes)


def test_config_upgrade_secret_retention_and_receiver_save_preserve_other_sections(tmp_path):
    path = tmp_path / 'config.toml'
    original = '[http]\n# Keep this\nhost="127.0.0.1"\nport=8787\n[wsjtx]\nenabled=false\nport=2238\ngroup="239.255.0.73"\ninterface="127.0.0.1"\n'
    path.write_text(original)
    assert not load_config(path).enrichment.enabled
    settings = EnrichmentSettings(enabled=True, qrz_username='operator', qrz_password='pass#word"safe', clublog_key='private-key')
    save_enrichment_config(path, settings)
    assert path.read_text().startswith(original)
    assert path.stat().st_mode & 0o077 == 0
    assert load_config(path).enrichment == settings
    save_receiver_config(path, Settings(retention=50, interface='127.0.0.1'))
    assert load_config(path).enrichment == settings
    assert 'pass#word' not in json.dumps(settings.public())
    assert update_settings(settings, {'qrz_password': ''}).qrz_password == settings.qrz_password
    assert update_settings(settings, {'clear_qrz_password': True}).qrz_password == ''
    assert 'pass#word' not in repr(settings)


def test_api_saves_sanitized_settings_without_receiver_restart(tmp_path, countryfile):
    config = tmp_path / 'config.toml'
    config.write_text(Path('config.example.toml').read_text())
    state = WorkspaceState(tmp_path / 'data/workspace.sqlite3')
    with TestClient(create_app(Settings(), state, config_path=config, serve_frontend=False)) as client:
        state.previous['A'] = 'K1ABC'
        response = client.put('/api/enrichment', json={'enabled': True, 'filename': str(countryfile), 'qrz_password': 'keep-secret'})
        assert response.status_code == 200
        assert response.json()['enrichment']['config']['qrz_password_configured']
        assert 'keep-secret' not in response.text
        assert state.previous == {'A': 'K1ABC'}
        before = state.snapshot()['history']
        result = client.post('/api/enrichment/test', json={'call': 'K1ABC'})
        assert result.json()['fields']['adif'] == 291
        assert state.history == before
        assert client.put('/api/enrichment', json={'station_grid': 'bad', 'qrz_password': 'hidden'}).status_code == 422
        assert 'hidden' not in client.put('/api/enrichment', json={'unknown': 'hidden'}).text
        assert client.put('/api/enrichment', json={}, headers={'Origin': 'https://foreign.example'}).status_code == 403


def test_slow_old_lookup_cannot_replace_new_focus_and_decodes_remain_live(tmp_path, monkeypatch):
    async def scenario():
        state = WorkspaceState(tmp_path / 'state.sqlite3')
        state.enter_radio_workspace()
        release, started = threading.Event(), threading.Event()
        def lookup(self, context):
            if context['call'] == 'K1SLOW':
                started.set()
                release.wait(2)
            return dict(status='loaded', call=context['call'], fields={'country': 'Fixture'})
        monkeypatch.setattr(Providers, 'enrich', lookup)
        service = EnrichmentService(state, EnrichmentSettings(enabled=True), tmp_path)
        state.enrichment_service = service
        await service.start()
        ingest(status(call='K0BASE'), state)
        ingest(status(call='K1SLOW'), state)
        while not started.is_set(): await asyncio.sleep(.005)
        ingest(status(call='K2FAST'), state)
        before = state.counters['decodes']
        ingest(decode(), state)
        assert state.call == 'K2FAST' and state.counters['decodes'] == before + 1
        assert service.result['status'] == 'pending' and service.result['call'] == 'K2FAST'
        release.set()
        deadline = time.monotonic() + 2
        while service.result['status'] == 'pending' and time.monotonic() < deadline: await asyncio.sleep(.01)
        assert service.result['call'] == 'K2FAST' and service.result['status'] == 'loaded'
        assert state.history[0]['call'] == 'K2FAST'
        await service.stop()
        state.close()
    asyncio.run(scenario())


def test_clublog_xml_uses_private_intermediate_and_preserves_operator_file(tmp_path):
    entities = ''.join(f'<entity><adif>{adif}</adif><name>{name}</name><prefix>{prefix}</prefix><deleted>FALSE</deleted><cqz>{zone}</cqz><cont>{continent}</cont><lat>{lat}</lat><long>{lon}</long></entity>'
        for adif, name, prefix, zone, continent, lat, lon in [(291, 'United States', 'K', 5, 'NA', 37, -95), (230, 'Germany', 'DL', 14, 'EU', 51, 10)])
    prefixes = ''.join(f'<prefix record="{index}"><call>{call}</call><entity>{country}</entity><adif>{adif}</adif><cqz>{zone}</cqz><cont>{continent}</cont><lat>{lat}</lat><long>{lon}</long></prefix>'
        for index, call, country, adif, zone, continent, lat, lon in [(1, 'K', 'United States', 291, 5, 'NA', 37, -95), (2, 'DL', 'Germany', 230, 14, 'EU', 51, 10)])
    exceptions = ''.join(f'<exception record="{i}"><call>K{i}EXC</call><entity>United States</entity><adif>291</adif><cqz>5</cqz><cont>NA</cont><lat>37</lat><long>-95</long></exception>' for i in (1, 2))
    invalid = ''.join(f'<invalid_operation record="{i}"><call>K{i}BAD</call><start>1990-01-01T00:00:00</start><end>1990-02-01T00:00:00</end></invalid_operation>' for i in (1, 2))
    zones = ''.join(f'<zone_exception record="{i}"><call>K{i}ZONE</call><zone>4</zone></zone_exception>' for i in (1, 2))
    content = f"<clublog date='2026-10-23T00:00:00' xmlns='http://clublog.org'>\n<entities>{entities}</entities><exceptions>{exceptions}</exceptions><prefixes>{prefixes}</prefixes><invalid_operations>{invalid}</invalid_operations><zone_exceptions>{zones}</zone_exceptions></clublog>"
    path = tmp_path / 'operator.xml'
    path.write_text(content)
    directory = tmp_path / 'cache'
    provider = Providers(EnrichmentSettings(source='clublogxml', filename=str(path)), directory)
    result = provider.enrich(dict(call='DL1ABC'))
    assert result['status'] == 'loaded'
    assert result['fields']['adif'] == 230 and result['fields']['country'] == 'Germany'
    assert path.read_text() == content
    assert list(directory.iterdir()) == []


def test_clublog_api_adapter_and_field_preference(monkeypatch, tmp_path, countryfile):
    requested = []
    class ClubResponse:
        status_code = 200
        def json(self): return dict(Name='Germany', DXCC=230, Lon=-10, Lat=51, CQZ=14, Continent='EU')
    def get(url, **kwargs):
        requested.append(url)
        return ClubResponse()
    monkeypatch.setattr('backend.enrichment.requests.get', get)
    result = Providers(EnrichmentSettings(source='clublogapi', clublog_key='private-key'), tmp_path).enrich(dict(call='DL1ABC'))
    assert result['status'] == 'loaded' and result['fields']['adif'] == 230
    assert result['fields']['longitude'] == 10
    assert requested[0].startswith('https://cdn.clublog.org/dxcc?')
    assert 'private-key' not in json.dumps(result)
    provider = Providers(EnrichmentSettings(filename=str(countryfile), qrz_enabled=True), tmp_path)
    monkeypatch.setattr(provider, 'lookup', lambda source, call: dict(status='loaded', fields={'country': source, 'adif': 291}))
    assert provider.enrich(dict(call='K1ABC'))['fields']['country'] == 'qrz'
    provider.settings = replace(provider.settings, field_priority='source_first')
    assert provider.enrich(dict(call='K1ABC'))['fields']['country'] == 'countryfile'


def test_bad_optional_provider_coordinates_leave_other_fields_available(tmp_path, countryfile, monkeypatch):
    provider = Providers(EnrichmentSettings(filename=str(countryfile), allow_country_estimate=True), tmp_path)
    monkeypatch.setattr(provider, 'lookup', lambda *args: dict(status='loaded', fields={'country': 'Fixture', 'latitude': None, 'longitude': 10}))
    result = provider.enrich(dict(call='K1ABC'))
    assert result['status'] == 'loaded' and not result['locationGrid']
