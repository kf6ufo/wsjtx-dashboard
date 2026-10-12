"""Offline release safety checks; never installs or contacts a station/GitHub."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import pytest

spec = importlib.util.spec_from_file_location('install_ubuntu', Path(__file__).resolve().parents[2] / 'scripts/install-ubuntu.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def make_archive(path, *, commit='abc123', unsafe=None):
    with tarfile.open(path, 'w:gz') as tar:
        for name, data in [('dist/index.html', b'<html>dashboard</html>'),
                           ('dist/frontend.json', json.dumps({'commit': commit}).encode())]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        if unsafe:
            tar.addfile(unsafe)


def test_release_requires_matching_frontend_source_commit(tmp_path):
    archive = tmp_path / 'frontend.tar.gz'
    make_archive(archive)
    assert (installer.extract_frontend(archive, tmp_path / 'good', 'abc123') / 'index.html').is_file()
    with pytest.raises(ValueError, match='commit mismatch'):
        installer.extract_frontend(archive, tmp_path / 'mismatch', 'other')


@pytest.mark.parametrize('name,kind', [('../outside', tarfile.REGTYPE), ('/outside', tarfile.REGTYPE), ('dist/link', tarfile.SYMTYPE), ('dist/hardlink', tarfile.LNKTYPE)])
def test_release_rejects_path_traversal_and_links(tmp_path, name, kind):
    archive = tmp_path / 'frontend.tar.gz'
    info = tarfile.TarInfo(name)
    info.type = kind
    info.linkname = '/outside'
    make_archive(archive, unsafe=info)
    with pytest.raises(ValueError, match='Unsafe'):
        installer.extract_frontend(archive, tmp_path / 'out', 'abc123')
    assert not (tmp_path / 'out').exists()
