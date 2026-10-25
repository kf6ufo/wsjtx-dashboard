"""Step 5/7 browser fixture: isolated multicast-free receiver and delayed read history."""
from pathlib import Path
import subprocess
import sys
import tempfile
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from backend.config import save_wavelog_config
from backend.wavelog_config import WavelogSettings
with tempfile.TemporaryDirectory(prefix='wsjtx-steps57-browser-') as directory:
    config=Path(directory)/'config.toml'
    config.write_text((root/'config.example.toml').read_text().replace('port = 8787','port = 8796').replace('enabled = false','enabled = true',1).replace('group = "239.255.0.73"','group = ""').replace('listen = "0.0.0.0"','listen = "127.0.0.1"').replace('port = 2238','port = 18243'))
    save_wavelog_config(config,WavelogSettings(enabled=True,url='http://wavelog-steps57.invalid',token='wl2_fixture'))
    launcher='''
import time
from copy import deepcopy
from backend.wavelog import WavelogClient
from backend.qso_model import history_record
from backend.observations import ObservationService
recorded={}
original_capture=ObservationService.capture
def capture(self,packet):
    changed=original_capture(self,packet)
    for key,item in self.pending.items():
        recorded.setdefault(key,(item['created']+3,history_record(item['fields'],key)))
    return changed
ObservationService.capture=capture
def lookup(self,call):
    rows=[deepcopy(row) for due,row in recorded.values() if due<=time.time() and row['call']==call]
    return dict(call=call,status='loaded' if rows else 'empty',complete=True,records=rows,total=len(rows),scope='Offline fixture',cached=False,confirmationStatus='complete')
def test(self):
    self.connection=dict(status='ready',scopes=['qso:read','station:read'],stations=[],logbooks=[])
    return self.connection
WavelogClient.lookup=lookup
WavelogClient.test=test
from backend.server import main
raise SystemExit(main())
'''
    child=subprocess.Popen([sys.executable,'-c',launcher,'--config',str(config)],cwd=root)
    try:sys.exit(child.wait())
    finally:
        if child.poll() is None:child.terminate();child.wait(timeout=20)
