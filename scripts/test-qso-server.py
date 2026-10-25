"""Isolated ADIF history/logging browser fixture; never joins station multicast."""
from pathlib import Path
import subprocess
import sys
import tempfile
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from backend.config import save_qso_config
from backend.qso_config import QsoSettings
from backend.qso_model import adif_text
with tempfile.TemporaryDirectory(prefix='wsjtx-qso-browser-') as directory:
    data=Path(directory);log=data/'history.adi';config=data/'config.toml'
    log.write_text(adif_text(dict(CALL='K1ADIF',QSO_DATE='20260101',TIME_ON='120000',BAND='20m',MODE='FT8',RST_SENT='-07',RST_RCVD='-10',STATION_CALLSIGN='KF0TKE',GRIDSQUARE='FN31',NAME='Offline ADIF fixture')))
    config.write_text((root/'config.example.toml').read_text().replace('port = 8787','port = 8797').replace('enabled = false','enabled = true',1).replace('group = "239.255.0.73"','group = ""').replace('listen = "0.0.0.0"','listen = "127.0.0.1"').replace('port = 2238','port = 18241'))
    save_qso_config(config,QsoSettings(adif_path=str(log),adif_complete=False,logging_enabled=False,rigs=[dict(id='QSO fixture',station_callsign='KF6UFO',operator='KF6UFO',wavelog_station_id=0,tx_power='20')]))
    child=subprocess.Popen([sys.executable,'-m','backend.server','--config',str(config)],cwd=root)
    try:sys.exit(child.wait())
    finally:
        if child.poll() is None:child.terminate();child.wait(timeout=15)
