"""Field semantics and real destination adapters, with synthetic QSO/provider data only."""
import asyncio
from copy import deepcopy
from decimal import Decimal
import io
from types import SimpleNamespace
import pytest
from backend.qso_model import enrich_qso, adif_records, adif_text, identity
from backend.qso_fields import adif_coordinate, destination_fields, ADIF_QSO_FIELDS, WAVELOG_QSO_FIELDS
from backend.qso_delivery import ADIFLogWriter, DeliveryQueue, WavelogLogWriter
from backend.wavelog_config import WavelogSettings
from backend.protocol import parse_packet
from .test_qso_architecture import fields, logged, wait_for
from .test_station_mapping import service_at


def enrichment(**changes):
    qrz = dict(callsign='K1ABC', name_fmt='Test Operator', addr1='1 Fixture Street', addr2='Testville',
        state='CT', zipcode='00000', county='New Haven', country='United States', adif=291,
        cqz=5, ituz=8, locator='FN31', latitude=41.5, longitude=-72.5, geoloc='user',
        email='fixture@example.invalid', url='https://example.invalid/station', iota='NA-001',
        qslmgr='K2MANAGER', lotw='Y', eqsl='Y', mqsl='Y', license_class='E', image='https://example.invalid/photo')
    qrz.update(changes)
    return dict(providers=dict(qrz=dict(status='loaded',fields=qrz),
        countryfile=dict(status='loaded',fields=dict(country='United States',adif=291,cqz=5,ituz=8,continent='NA',prefix='K'))),
        computed=dict(distanceKm=1,heading=1,longPathKm=1,homeCall='K1WRONG'),
        stationGrid='DM57NS',stationGridSource='Configured station grid')


def test_all_reliable_fields_survive_actual_adif_and_wavelog_adapters(tmp_path):
    original = fields(GRIDSQUARE='FN31', MY_GRIDSQUARE='DM57NS')
    result, sources = enrich_qso(original, {}, enrichment())
    expected = dict(NAME='Test Operator',QTH='Testville',STATE='CT',CNTY='CT,New Haven',EMAIL='fixture@example.invalid',
        WEB='https://example.invalid/station', IOTA='NA-001', QSL_VIA='K2MANAGER', DXCC='291', COUNTRY='United States',
        CQZ='5', ITUZ='8', CONT='NA',PFX='K', LAT='N041 30.000', LON='W072 30.000',
        ADDRESS='1 Fixture Street\nTestville, CT 00000\nUnited States')
    assert {k:result[k] for k in expected} == expected
    assert result['MY_LAT'].startswith('N037 ') and result['MY_LON'].startswith('W108 ')
    assert 3000 < float(result['DISTANCE']) < 4000  # QSO grids, not the incorrect display calculation.
    assert sources['LAT'] == 'QRZ XML' and sources['DISTANCE'].startswith('Great-circle')
    queue = DeliveryQueue(tmp_path/'queue.sqlite3')
    writer = ADIFLogWriter(tmp_path/'contacts.adi', queue)
    writer.write('fixture-receipt',result)
    assert '<ADIF_VER:5>3.1.6' in (tmp_path/'contacts.adi').read_text()
    record = list(adif_records(io.StringIO((tmp_path/'contacts.adi').read_text())))[0]
    assert all(record[k] == v for k,v in result.items())
    assert record['APP_WSJT_DASHBOARD_ID'] == 'fixture-receipt'
    payload = WavelogLogWriter(WavelogSettings(),1,'KF6UFO').payload(result)
    assert all(payload[k.lower()] == v for k,v in result.items() if k not in ('DISTANCE','FREQ','QSO_DATE'))
    assert payload['distance'] == float(record['DISTANCE']) and payload['heading'] != 1
    assert payload['freq'] == 14074000
    assert 'ANT_AZ' not in record and 'HEADING' not in record
    assert 'ant_az' not in payload and 'class' not in payload and 'lotw_qsl_rcvd' not in payload
    queue.close()


def test_every_original_value_wins_and_unknown_destination_fields_stay_out():
    original = fields(NAME='Original', QTH='Original QTH', ADDRESS='Original address', EMAIL='original@example.invalid',
        WEB='https://example.invalid/original', IOTA='EU-001', QSL_VIA='K3ORIGINAL', GRIDSQUARE='FN31',
        MY_GRIDSQUARE='DM57', LAT='N041 00.000', LON='W072 00.000', MY_LAT='N037 00.000', MY_LON='W109 00.000',
        DXCC='291',COUNTRY='Original country',CQZ='4',ITUZ='7',CONT='NA',PFX='W',STATE='NY',CNTY='NY,Original',
        DISTANCE='0',TX_PWR='0',OPERATOR='K2OP',COMMENT='Original comment', HEADING='77',
        MYSTERY='unsupported',APP_OTHER_RECEIPT='preserve ADIF extension')
    before=deepcopy(original)
    result,sources=enrich_qso(original,{},enrichment())
    assert original==before and all(result[k]==v for k,v in original.items())
    assert identity(result)==identity(original)
    adif=destination_fields(result,'adif'); wl=WavelogLogWriter(WavelogSettings(),1,'KF6UFO').payload(result)
    assert all(adif[k]==v for k,v in original.items() if k not in ('MYSTERY','HEADING'))
    assert 'MYSTERY' not in adif and 'HEADING' not in adif
    assert 'mystery' not in wl and 'app_other_receipt' not in wl
    assert wl['distance']==0 and wl['heading']==77 and wl['tx_pwr']=='0'
    assert all(sources[k]=='WSJT-X' for k in original)


def test_conflicting_qrz_home_and_coarse_country_coordinates_cannot_replace_qso_location():
    result,sources=enrich_qso(fields(GRIDSQUARE='PM85',MY_GRIDSQUARE='DM57NS'),{},enrichment())
    assert result['GRIDSQUARE']=='PM85' and 'STATE' not in result and 'CNTY' not in result and 'IOTA' not in result and 'QTH' not in result
    assert result['LAT'].startswith('N035 ') and result['LON'].startswith('E137 ')
    assert sources['LAT']=='Grid centre (GRIDSQUARE)'
    assert result['EMAIL']=='fixture@example.invalid' and result['ADDRESS'] # Mailing info remains mailing info.
    for geoloc in ('zip','state','dxcc','none'):
        result,_=enrich_qso(fields(),{},enrichment(geoloc=geoloc))
        assert not set(result)&{'GRIDSQUARE','LAT','LON','IOTA','STATE','CNTY','QTH'}


def test_unknown_invalid_or_failed_provider_values_are_omitted():
    data=enrichment(locator='XX99', email='invalid', url='https://user:secret@example.invalid', iota='XX-999', cqz=0,ituz=91,adif=999,county=None,latitude=float('nan'),longitude=181)
    data['providers'].pop('countryfile')
    result,_=enrich_qso(fields(),{},data)
    assert not set(result)&{'GRIDSQUARE','EMAIL','WEB','IOTA','CQZ','ITUZ','DXCC','COUNTRY','LAT','LON'}
    data=enrichment();data['providers']['qrz']['status']='error';data['providers'].pop('countryfile')
    result,_=enrich_qso(fields(),{},data)
    assert not set(result)&{'NAME','QTH','GRIDSQUARE','QSL_VIA','ADDRESS','EMAIL','WEB','IOTA','LAT','LON'}


def test_unicode_and_partial_original_coordinates_are_preserved_without_mixing():
    result,_=enrich_qso(fields(LAT='N000 00.000'),{},enrichment(name_fmt='André',addr1='1 Rue Été'))
    assert result['NAME_INTL']=='André' and result['NAME']=='Andre'
    assert 'Été' in result['ADDRESS_INTL'] and 'Ete' in result['ADDRESS']
    assert result['LAT']=='N000 00.000' and 'LON' not in result
    result,_=enrich_qso(fields(NAME='Original',ADDRESS_INTL='原住所'),{},enrichment(name_fmt='André'))
    assert 'NAME_INTL' not in result and 'ADDRESS' not in result and result['ADDRESS_INTL']=='原住所'
    result,_=enrich_qso(fields(),{},enrichment(country='Curaçao'))
    assert result['COUNTRY']=='Curacao' and result['COUNTRY_INTL']=='Curaçao'
    result,_=enrich_qso(fields(COUNTRY='Original',COUNTRY_INTL='原国'),{},enrichment(country='Curaçao'))
    assert result['COUNTRY']=='Original' and result['COUNTRY_INTL']=='原国'
    result,_=enrich_qso(fields(),{},enrichment(name_fmt='張三'))
    assert result['NAME_INTL']=='張三' and 'NAME' not in result


@pytest.mark.parametrize('value,lat,expected', [(0,True,'N000 00.000'),(-0.5,False,'W000 30.000'),(89.9999999,True,'N090 00.000'),(180,False,'E180 00.000'),(91,True,''),(float('inf'),False,'')])
def test_adif_coordinate_format_ranges_and_minute_carry(value,lat,expected):
    assert adif_coordinate(value,lat)==expected


def test_destination_support_is_explicit_and_keeps_standard_extensions():
    assert WAVELOG_QSO_FIELDS - ADIF_QSO_FIELDS == {'HEADING'}
    original=fields(MY_CQ_ZONE='5',GRIDSQUARE_EXT='AB',QRZCOM_QSO_DOWNLOAD_STATUS='Y',MORSE_KEY_TYPE='STRAIGHT',APP_WSJT_DASHBOARD_ID='receipt',LOTW_QSL_RCVD='Y')
    assert destination_fields(original,'adif')==original
    wl=destination_fields(original,'wavelog')
    assert 'MY_CQ_ZONE' not in wl and 'GRIDSQUARE_EXT' not in wl and 'APP_WSJT_DASHBOARD_ID' not in wl
    assert wl['QRZCOM_QSO_DOWNLOAD_STATUS']=='Y' and wl['MORSE_KEY_TYPE']=='STRAIGHT' and wl['LOTW_QSL_RCVD']=='Y'


def test_prepared_field_delivery_keeps_existing_deduplication(tmp_path,monkeypatch):
    async def run():
        state,service=service_at(tmp_path,True,profiles=[dict(id='Rig A',station_callsign='KF6UFO',operator='',tx_power='',wavelog_station_id=1)])
        service.enrichment=SimpleNamespace(settings=SimpleNamespace(enabled=True),lock=asyncio.Lock(),providers=SimpleNamespace(enrich=lambda ctx:enrichment()))
        monkeypatch.setattr(WavelogLogWriter,'prepare',lambda *a:None)
        sent=[]
        class Response:
            status_code=201
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def iter_content(self,size): yield b'{"data":{"id":42}}'
        def post(url,**kwargs): sent.append(kwargs['json']);return Response()
        monkeypatch.setattr('backend.qso_delivery.requests.post',post)
        packet=parse_packet(logged(rig='Rig A',GRIDSQUARE='FN31',MY_GRIDSQUARE='DM57NS'))
        await service.start();service.capture(packet)
        await wait_for(lambda:service.queue.summary()['jobs'].get('delivered')==1)
        path=tmp_path/'local.adi';before=path.read_bytes()
        service.capture(packet);await asyncio.sleep(.3)
        assert path.read_bytes()==before and len(sent)==1
        record=list(adif_records(io.StringIO(before.decode())))[0]
        assert sent[0]['email']==record['EMAIL'] and Decimal(str(sent[0]['distance']))==Decimal(record['DISTANCE'])
        assert service.queue.execute("SELECT status FROM qso_delivery")==[('delivered',),('delivered',)]
        await service.stop();state.close()
    asyncio.run(run())
