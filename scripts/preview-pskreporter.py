"""Isolated visual review: fictional reception reports; no radio/upstream access.

Build first, then run with the project's Python. Config/state live only in a
temporary directory. This never reads or writes the operator's config or logs.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import create_app
from backend.config import load_config, save_pskreporter_config
from backend.pskreporter_config import PskReporterSettings
from backend.workspace import WorkspaceState
from backend.protocol import Packet


class FixtureFeed:
    def __init__(self, inbox):
        self.inbox, self.connected = inbox, True
        inbox.put_nowait(('connected', None))

    def is_connected(self): return self.connected
    def disconnect(self): self.connected = False
    def loop_stop(self): pass
    def unsubscribe(self, topic): pass

    def subscribe(self, topic, qos):
        now = int(time.time())
        # All callsigns/report locations are deliberately fictional examples.
        for call, grid, age, frequency in [('K1FOCUS','FN31',60,14074000), ('K2NEAR-888','FN32',120,14074000),
                ('K3COAST','FM29',180,14074000), ('W4NEAR','FM17',300,14074000),
                ('K5WEST','EM59',420,14074000), ('K6OLDER','EN80',1200,14074000),
                ('K7BAND','FN20',30,21074000)]:
            payload = dict(sc='N0CALL',rc=call,rl=grid,f=frequency,md='FT4' if call == 'K2NEAR-888' else 'FT8',rp=-12,t=now-age)
            self.inbox.put_nowait(('spot', json.dumps(payload).encode()))
        # Diagnostic fixtures: duplicate, stale, invalid-grid and malformed data.
        base = dict(sc='N0CALL',rc='K1FOCUS',rl='FN31',f=14074000,md='FT8',rp=-12,t=now-60)
        for payload in (json.dumps(base).encode(),json.dumps(base|{'t':now-7200}).encode(),
                        json.dumps(base|{'rl':'ZZ99'}).encode(),b'not JSON'):
            self.inbox.put_nowait(('spot',payload))
        self.inbox.put_nowait(('subscribed', dict(mid=1, reason='Fixture QoS 0')))
        return 0, 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8798)
    args = parser.parse_args()
    if args.port == 8787 or not 1024 <= args.port <= 65535:
        parser.error('Choose an isolated unprivileged port other than 8787')
    if not (ROOT/'dist/index.html').is_file():
        parser.error('Build the frontend first: npm run build')
    import uvicorn
    with tempfile.TemporaryDirectory(prefix='wsjtx-pskreporter-preview-') as directory:
        path = Path(directory)/'config.toml'
        path.write_text((ROOT/'config.example.toml').read_text().replace('port = 8787', f'port = {args.port}'))
        save_pskreporter_config(path, PskReporterSettings(True,'N0CALL'))
        state = WorkspaceState(Path(directory)/'workspace.sqlite3'); state.enter_radio_workspace()
        now = int(time.time()*1000)
        state.call, state.source = 'K1FOCUS', 'radio'
        state.history = [dict(call='K1FOCUS',rigId='Fictional radio',stationCall='N0CALL',band='20m',mode='FT8',
                              frequency=14074000,dxGrid='FN31',deGrid='CN85',selectedAt=now,recency=1)]
        state.selection_sequence = 1
        state.preferences['title'] = 'PSKReporter preview · fictional reports'
        # Fictional local evidence uses the same bounded cache, without a UDP socket.
        state.local_receptions.capture(Packet(1, 'Fictional radio', dx_call='K1FOCUS', frequency=14074000,
            mode='FT8', fields=dict(deCall='N0CALL', dxGrid='FN31')), at=now)
        for call, grid, age in [('K1FOCUS','FN31',5), ('K3COAST','FM29',10), ('K8LOCAL','FN33',15)]:
            state.local_receptions.capture(Packet(2, 'Fictional radio', fields=dict(new=True, offAir=False,
                lowConfidence=False, milliseconds=(now-age*1000) % 86400000, mode='~',
                message=f'CQ {call} {grid}', snr=-14)), at=now)
        config = load_config(path)
        app = create_app(config.receiver,state,config_path=path)
        state.pskreporter.client_factory = FixtureFeed
        print(f'Fictional reception preview: http://127.0.0.1:{args.port}/ · no radio or MQTT connection',flush=True)
        uvicorn.run(app,host='127.0.0.1',port=args.port,timeout_graceful_shutdown=5)


if __name__ == '__main__': main()
