#!/usr/bin/env python3
"""Build a commit-matched frontend asset for publication on GitHub Releases."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

root = Path(__file__).resolve().parents[1]
if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
    raise SystemExit('Commit all source changes before packaging the frontend.')
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
subprocess.run(['npm', 'run', 'build'], cwd=root, check=True)
(root / 'dist/frontend.json').write_text(json.dumps({'commit': commit}) + '\n')
output = Path(tempfile.mkdtemp(prefix='wsjtx-frontend-'))
archive = output / 'frontend.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    tar.add(root / 'dist', arcname='dist')
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(output / 'frontend.tar.gz.sha256').write_text(f'{checksum}  frontend.tar.gz\n')
print(json.dumps({'commit': commit, 'archive': str(archive), 'sha256': checksum}, indent=2))
