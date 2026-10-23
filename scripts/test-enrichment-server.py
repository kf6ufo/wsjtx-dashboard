"""Installed server + real loopback UDP + offline pyhamtools data for browser QA."""
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from backend.config import save_enrichment_config
from backend.enrichment import EnrichmentSettings

with tempfile.TemporaryDirectory(prefix='wsjtx-enrichment-browser-') as directory:
    data = Path(directory)
    fixture = data / 'fixture.plist'
    fixture.write_bytes(plistlib.dumps({
        'K': dict(Country='United States', Continent='NA', CQZone=5, ITUZone=8, Latitude=37.0, Longitude=95.0, ExactCallsign=False),
        'DL': dict(Country='Fed. Rep. of Germany', Continent='EU', CQZone=14, ITUZone=28, Latitude=51.0, Longitude=-10.0, ExactCallsign=False)}))
    config = data / 'config.toml'
    source = (root / 'config.example.toml').read_text().replace('port = 8787', 'port = 8793').replace('enabled = false', 'enabled = true', 1).replace('group = "239.255.0.73"', 'group = ""').replace('listen = "0.0.0.0"', 'listen = "127.0.0.1"').replace('port = 2238', 'port = 18239')
    config.write_text(source)
    save_enrichment_config(config, EnrichmentSettings(enabled=True, filename=str(fixture), station_grid='CN87'))
    child = subprocess.Popen([sys.executable, '-m', 'backend.server', '--config', str(config)], cwd=root)
    try:
        sys.exit(child.wait())
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=15)
