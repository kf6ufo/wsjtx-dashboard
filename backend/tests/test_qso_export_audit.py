"""Exercise the read-only export audit against an isolated HTTP export fixture."""
import importlib.util
import io
import json
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from dataclasses import replace
from backend.config import load_config, save_qso_config, save_wavelog_config
from backend.qso_delivery import DeliveryQueue, ADIFLogWriter
from backend.qso_model import adif_text
from .test_qso_architecture import fields

spec=importlib.util.spec_from_file_location('export_audit',Path(__file__).resolve().parents[2]/'scripts/audit-qso-field-exports.py')
audit_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit_module)


def test_export_verification_uses_receipt_identity_get_only_and_never_repairs(tmp_path,capsys):
    local=fields(NAME='Original Operator',GRIDSQUARE='FN31',MY_LAT='N037 00.000',EMAIL='fixture@example.invalid',DISTANCE='0',CQZ='5')
    remote=local|dict(NAME='ORIGINAL OPERATOR')
    remote.pop('MY_LAT');remote.pop('EMAIL');remote.pop('DISTANCE')
    hits=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            hits.append(self.command)
            params=parse_qs(self.path.split('?',1)[1])
            data=dict(adif=adif_text(remote)) if params['format']==['adif'] else [dict(id=42,station_id=1,call='K1ABC',qso_date='2026-10-24 12:00:00',band='20m',mode='MFSK',submode='FT8',freq='14074000')]
            body=json.dumps(dict(data=data,meta=dict(has_more=False))).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        config_path=tmp_path/'config.toml';config_path.write_text(Path('config.example.toml').read_text())
        config=load_config(config_path);url=f'http://127.0.0.1:{server.server_port}'
        save_qso_config(config_path,replace(config.qso,adif_path=str(tmp_path/'local.adi')))
        save_wavelog_config(config_path,replace(config.wavelog,url=url,token='wl2_fixture'))
        queue=DeliveryQueue(tmp_path/'data/delivery.sqlite3')
        key=queue.capture('Rig',local,{},dict(adif=dict(path=str(tmp_path/'local.adi')),wavelog=dict(url=url,station_id=1)))
        ADIFLogWriter(tmp_path/'local.adi',queue).write(key,local)
        queue.delivered(key,'adif','receipt');queue.delivered(key,'wavelog','42');queue.close()
        before={p:p.read_bytes() for p in (config_path,tmp_path/'local.adi',tmp_path/'data/delivery.sqlite3')}
        result=audit_module.audit(config_path.resolve())
        assert result['outcomes']==dict(verified_receipt_and_unique_export_identity=1)
        assert result['fields']['NAME']==dict(text_normalized=1)
        assert result['fields']['EMAIL']==dict(missing_from_export=1)
        assert result['fields']['MY_LAT']==dict(not_exported_by_wavelog=1)
        assert result['fields']['DISTANCE']==dict(zero_omitted_by_wavelog=1)
        assert hits==['GET','GET']
        assert all(p.read_bytes()==value for p,value in before.items())
        text=capsys.readouterr().out
        assert 'K1ABC' not in text and 'Original Operator' not in text and 'wl2_fixture' not in text
    finally:
        server.shutdown();server.server_close();thread.join()
