"""Temporary build-tool setup: synthetic archives, no network or global install."""
import hashlib
import io
import os
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.error

import pytest
from .test_deployment import installer


def archive_bytes(name, unsafe=False):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as bundle:
        for binary in ['node','npm']:
            entry = tarfile.TarInfo('../../escape' if unsafe else f'{name}/bin/{binary}')
            content = b'fixture executable'; entry.mode = 0o755; entry.size = len(content)
            bundle.addfile(entry, io.BytesIO(content))
            if unsafe: break
    return output.getvalue()


@pytest.mark.parametrize('system,machine,target', [('Darwin','arm64',('darwin','arm64')),('Darwin','x86_64',('darwin','x64')),('Linux','aarch64',('linux','arm64')),('Linux','x86_64',('linux','x64'))])
def test_supported_targets_and_pinned_checksums(monkeypatch, system, machine, target):
    monkeypatch.setattr(installer.platform, 'system', lambda:system)
    monkeypatch.setattr(installer.platform, 'machine', lambda:machine)
    assert installer.node_target() == target
    assert re.fullmatch(r'[0-9a-f]{64}', installer.NODE_SHA256[target])


@pytest.mark.parametrize('system,machine', [('Windows','AMD64'),('Linux','s390x')])
def test_unsupported_automatic_target_has_manual_fallback(monkeypatch, system, machine):
    monkeypatch.setattr(installer.platform, 'system', lambda:system)
    monkeypatch.setattr(installer.platform, 'machine', lambda:machine)
    with pytest.raises(ValueError, match='manually'): installer.node_target()


@pytest.fixture
def temporary_tool(monkeypatch, tmp_path):
    target = ('darwin','arm64')
    name = f'node-v{installer.NODE_VERSION}-darwin-arm64'
    payload = archive_bytes(name)
    monkeypatch.setattr(installer, 'node_target', lambda:target)
    monkeypatch.setattr(installer.shutil, 'which', lambda name:None)
    original = installer.tempfile.TemporaryDirectory
    monkeypatch.setattr(installer.tempfile, 'TemporaryDirectory', lambda **kw:original(dir=tmp_path, **kw))
    monkeypatch.setitem(installer.NODE_SHA256, target, hashlib.sha256(payload).hexdigest())
    downloads=[]
    def download(url, path):
        downloads.append((url,path)); path.write_bytes(payload)
    monkeypatch.setattr(installer, 'download_node', download)
    monkeypatch.setattr(installer.subprocess, 'check_output', lambda *a, **kw:f'v{installer.NODE_VERSION}')
    return downloads, tmp_path, target


def test_missing_node_is_temporary_and_child_path_only(temporary_tool):
    downloads, _, _ = temporary_tool
    previous = dict(os.environ)
    with installer.node_environment() as environment:
        binary = Path(environment['PATH'].split(os.pathsep)[0])
        assert (binary/'node').is_file() and (binary/'npm').is_file()
        assert environment['PATH'].endswith(previous.get('PATH',''))
        assert os.environ == previous
        assert downloads[0][0] == f'https://nodejs.org/dist/v{installer.NODE_VERSION}/node-v{installer.NODE_VERSION}-darwin-arm64.tar.gz'
        directory = downloads[0][1].parent
        assert directory.stat().st_mode & 0o777 == 0o700
    assert not directory.exists() and os.environ == previous


def test_temporary_tool_is_removed_after_build_failure(temporary_tool):
    downloads, _, _ = temporary_tool
    with pytest.raises(subprocess.CalledProcessError):
        with installer.node_environment(): raise subprocess.CalledProcessError(1, ['npm','ci'])
    assert not downloads[0][1].parent.exists()


def test_checksum_failure_never_executes_downloaded_tools(temporary_tool, monkeypatch):
    downloads, _, target = temporary_tool
    monkeypatch.setitem(installer.NODE_SHA256, target, '0'*64)
    monkeypatch.setattr(installer.subprocess, 'check_output', lambda *a, **kw:pytest.fail('Unverified binary executed'))
    with pytest.raises(ValueError, match='checksum'):
        with installer.node_environment(): pytest.fail('Unverified tool accepted')
    assert not downloads[0][1].parent.exists()


def test_safe_extraction_rejects_archive_traversal(temporary_tool, monkeypatch):
    downloads, directory, target = temporary_tool
    payload = archive_bytes('ignored', unsafe=True)
    monkeypatch.setitem(installer.NODE_SHA256,target,hashlib.sha256(payload).hexdigest())
    def download(url,path): downloads.append((url,path));path.write_bytes(payload)
    monkeypatch.setattr(installer,'download_node',download)
    with pytest.raises(tarfile.FilterError):
        with installer.node_environment(): pytest.fail('Unsafe archive accepted')
    assert not (directory.parent/'escape').exists()
    assert not downloads[0][1].parent.exists()


@pytest.mark.parametrize('available', [None,'v22.1.0','v24.14.0','not-a-version'])
def test_missing_npm_or_incompatible_node_uses_temporary_tool(temporary_tool, monkeypatch, available):
    downloads, _, _ = temporary_tool
    monkeypatch.setattr(installer.shutil,'which',lambda name:'/existing/'+name if available or name=='node' else None)
    monkeypatch.setattr(installer.subprocess,'check_output',lambda command, **kw: available if command[0]=='/existing/node' else f'v{installer.NODE_VERSION}')
    with installer.node_environment(): assert len(downloads)==1


def test_compatible_existing_node_is_reused_without_download(monkeypatch):
    monkeypatch.setattr(installer.shutil,'which',lambda name:'/existing/'+name)
    monkeypatch.setattr(installer.subprocess,'check_output',lambda *a, **kw:'v24.15.0')
    monkeypatch.setattr(installer,'download_node',lambda *a:pytest.fail('Unexpected download'))
    with installer.node_environment() as environment: assert environment==os.environ
    # Build failures must propagate, not be mistaken for a failed Node probe.
    with pytest.raises(subprocess.CalledProcessError):
        with installer.node_environment(): raise subprocess.CalledProcessError(1,['npm','ci'])


def test_failed_download_cleans_temporary_directory(temporary_tool, monkeypatch):
    _, directory, _ = temporary_tool
    monkeypatch.setattr(installer,'download_node',lambda *a:(_ for _ in ()).throw(urllib.error.URLError('fixture network failure')))
    with pytest.raises(urllib.error.URLError):
        with installer.node_environment(): pytest.fail('Failed download accepted')
    assert not list(directory.iterdir())
