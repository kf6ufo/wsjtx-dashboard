"""Distance is added only to the original Wavelog JSON request; no live writes."""
from copy import deepcopy
import json

import pytest

from backend.qso_delivery import WavelogLogWriter
from backend.qso_model import adif_text, identity
from backend.wavelog_config import WavelogSettings
from .test_qso_architecture import fields


@pytest.fixture
def submit(monkeypatch):
    sent = []

    class Response:
        status_code = 201
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, size): yield b'{"data":{"id":42}}'

    def post(url, **kwargs):
        # Exercise actual JSON encoding too: reject non-finite/non-numeric additions.
        sent.append((url, json.loads(json.dumps(kwargs['json'], allow_nan=False))))
        return Response()

    monkeypatch.setattr('backend.qso_delivery.requests.post', post)
    monkeypatch.setattr('backend.qso_delivery.requests.get', lambda *a, **k: pytest.fail('No extra API request'))
    monkeypatch.setattr('backend.qso_delivery.requests.patch', lambda *a, **k: pytest.fail('No follow-up edit'))
    writer = WavelogLogWriter(WavelogSettings(url='http://wavelog.invalid', token='wl2_fixture'), 1, 'KF6UFO')

    def write(extra):
        original = fields(**extra)
        before, adif_before, key = deepcopy(original), adif_text(original), identity(original)
        assert writer.write('fixture-key', original) == '42'
        assert len(sent) == 1
        assert sent[0][0] == 'http://wavelog.invalid/api/v2/qso'
        assert original == before and adif_text(original) == adif_before and identity(original) == key
        payload = sent[0][1]
        assert payload['station_profile_id'] == 1 and payload['freq'] == 14074000
        assert payload['call'] == original['CALL'] and payload['mode'] == original['MODE']
        return payload

    return write


@pytest.mark.parametrize('station,contact,km', [
    ('JN48', 'QF67', 16535.573),
    (' jn48qm ', 'qf67bf', 16466.413),
    ('JN48QM12', 'QF67BF34', 16468.059),
    ('AJ00', 'RJ90', 222.381),  # Short path across the date line.
    ('JN48QM', 'JN48QM', 0),
])
def test_great_circle_kilometres_in_original_request(submit, station, contact, km):
    distance = submit(dict(MY_GRIDSQUARE=station, GRIDSQUARE=contact))['distance']
    assert type(distance) is float and distance == pytest.approx(km, abs=0.001)


@pytest.mark.parametrize('distance', ['1234.56789', '0', '12.5'])
def test_valid_existing_distance_wins_even_without_grids(submit, distance):
    assert submit(dict(DISTANCE=distance))['distance'] == float(distance)


@pytest.mark.parametrize('extra', [
    {}, {'MY_GRIDSQUARE': 'JN48'}, {'GRIDSQUARE': 'QF67'},
    {'MY_GRIDSQUARE': 'JN48', 'GRIDSQUARE': ''},
    {'MY_GRIDSQUARE': 'XX99', 'GRIDSQUARE': 'QF67'},
    {'MY_GRIDSQUARE': 'JN48', 'GRIDSQUARE': 'QF67ZZ12'},
    {'MY_GRIDSQUARE': 'JN48', 'GRIDSQUARE': 'QF67B'},
    {'MY_GRIDSQUARE': None, 'GRIDSQUARE': 'QF67'},
    {'MY_GRIDSQUARE': 'JN48', 'GRIDSQUARE': '1234'},
])
def test_missing_or_invalid_grid_omits_distance(submit, extra):
    assert 'distance' not in submit(extra)


@pytest.mark.parametrize('distance', ['', '-1', 'nan', 'inf', '-inf', 'invalid', None])
@pytest.mark.parametrize('grids', [False, True])
def test_invalid_existing_distance_recomputed_or_omitted(submit, distance, grids):
    extra = dict(DISTANCE=distance)
    if grids: extra.update(MY_GRIDSQUARE='JN48QM', GRIDSQUARE='QF67BF')
    payload = submit(extra)
    if grids: assert payload['distance'] == pytest.approx(16466.413, abs=0.001)
    else: assert 'distance' not in payload


def test_existing_distance_preserved_when_grids_disagree(submit):
    assert submit(dict(DISTANCE='12.34567', MY_GRIDSQUARE='JN48QM', GRIDSQUARE='QF67BF'))['distance'] == 12.34567
