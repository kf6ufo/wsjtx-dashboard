"""Real Git repositories and local transports only; no station or GitHub writes."""
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'https://github.com/kf6ufo/wsjtx-dashboard.git'
GIT = shutil.which('git')


@pytest.fixture
def installation(tmp_path):
    environment = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=str(tmp_path/'gitconfig'),
                       GIT_AUTHOR_NAME='Fixture Operator', GIT_AUTHOR_EMAIL='operator@example.invalid',
                       GIT_COMMITTER_NAME='Fixture Operator', GIT_COMMITTER_EMAIL='operator@example.invalid', GIT_TERMINAL_PROMPT='0')
    def git(path, *args):
        return subprocess.check_output([GIT,'-C',str(path),*args],env=environment,stderr=subprocess.PIPE,text=True).strip()
    origin=tmp_path/'origin.git'; seed=tmp_path/'seed'; checkout=tmp_path/'checkout with spaces'
    subprocess.run([GIT,'init','--bare','--initial-branch=main',str(origin)],env=environment,check=True,capture_output=True)
    subprocess.run([GIT,'init','--initial-branch=main',str(seed)],env=environment,check=True,capture_output=True)
    git(tmp_path,'config','--file',environment['GIT_CONFIG_GLOBAL'],f'url.{origin.as_uri()}.insteadOf',ORIGIN)
    (seed/'backend').mkdir();(seed/'backend/server.py').write_text('# Expected fixture layout\n')
    (seed/'config.example.toml').write_text('# Synthetic template\n')
    (seed/'.gitignore').write_text('config.toml\ndata/\n*.adi\ninstall-runs\n')
    (seed/'install.sh').write_text('#!/bin/sh\nprintf "installed\\n" >> install-runs\n')
    (seed/'install.sh').chmod(0o755)
    shutil.copyfile(ROOT/'update.sh',seed/'update.sh');(seed/'update.sh').chmod(0o755)
    (seed/'version.txt').write_text('old\n')
    git(seed,'add','.');git(seed,'commit','-m','Initial fixture')
    git(seed,'remote','add','origin',ORIGIN);git(seed,'push','origin','main')
    subprocess.run([GIT,'clone',ORIGIN,str(checkout)],env=environment,check=True,capture_output=True)
    (checkout/'config.toml').write_text('operator configuration preserved\n')
    (checkout/'data').mkdir()
    for name in ['workspace','delivery','observations','forwarding']:
        with sqlite3.connect(checkout/f'data/{name}.sqlite3') as db:
            db.execute('CREATE TABLE retained (value TEXT)');db.execute("INSERT INTO retained VALUES ('pending or delivered fixture')")
    (checkout/'history.adi').write_text('synthetic operator ADIF\n')
    preserved={p:p.read_bytes() for p in [checkout/'config.toml',checkout/'history.adi',*sorted((checkout/'data').iterdir())]}
    def publish():
        git(seed,'add','.');git(seed,'commit','-m','Fixture update');git(seed,'push','origin','main')
        return git(seed,'rev-parse','HEAD')
    def update(extra_environment=None):
        return subprocess.run([str(checkout/'update.sh')],cwd=checkout,env=environment | (extra_environment or {}),capture_output=True,text=True,timeout=20)
    return checkout,seed,git,publish,update,preserved,environment


def test_clean_update_preserves_operator_data_and_uses_new_installer(installation):
    checkout,seed,git,publish,update,preserved,_=installation
    previous=git(checkout,'rev-parse','HEAD')
    (seed/'version.txt').write_text('new\n')
    (seed/'install.sh').write_text('#!/bin/sh\nprintf "new installer\\n" >> install-runs\n')
    expected=publish();result=update()
    assert result.returncode==0,result.stderr
    assert git(checkout,'rev-parse','HEAD')==expected
    assert previous in result.stdout and expected in result.stdout and 'Update successful' in result.stdout
    assert (checkout/'install-runs').read_text()=='new installer\n'
    assert all(p.read_bytes()==before for p,before in preserved.items())
    assert git(checkout,'stash','list')==''


def test_already_current_installation_still_runs_installer(installation):
    checkout,_,git,_,update,_,_=installation
    previous=git(checkout,'rev-parse','HEAD');result=update()
    assert result.returncode==0 and 'Already up to date' in result.stdout
    assert git(checkout,'rev-parse','HEAD')==previous
    assert (checkout/'install-runs').read_text()=='installed\n'


@pytest.mark.parametrize('staged',[False,True])
def test_local_tracked_changes_stop_without_stashing(installation,staged):
    checkout,_,git,_,update,preserved,_=installation
    previous=git(checkout,'rev-parse','HEAD');(checkout/'version.txt').write_text('my edits\n')
    if staged:git(checkout,'add','version.txt')
    git(checkout,'config','merge.autoStash','true')
    result=update()
    assert result.returncode!=0 and 'uncommitted changes' in result.stderr
    assert git(checkout,'rev-parse','HEAD')==previous and (checkout/'version.txt').read_text()=='my edits\n'
    assert not (checkout/'install-runs').exists() and git(checkout,'stash','list')==''
    assert all(p.read_bytes()==before for p,before in preserved.items())


@pytest.mark.parametrize('branch',['feature/operator','detached'])
def test_wrong_branch_or_detached_checkout_stops(installation,branch):
    checkout,_,git,_,update,_,_=installation
    if branch=='detached':git(checkout,'checkout','--detach')
    else:git(checkout,'switch','-c',branch)
    result=update()
    assert result.returncode!=0 and 'main' in result.stderr
    assert not (checkout/'install-runs').exists()


def test_wrong_repository_or_missing_expected_layout_stops(installation):
    checkout,_,git,_,update,_,_=installation
    git(checkout,'remote','set-url','origin','https://github.com/example/other.git')
    assert 'origin must identify' in update().stderr
    git(checkout,'remote','set-url','origin',ORIGIN)
    git(checkout,'rm','backend/server.py');git(checkout,'commit','-m','Remove expected layout')
    result=update()
    assert result.returncode!=0 and 'installation files' in result.stderr
    assert not (checkout/'install-runs').exists()


@pytest.mark.parametrize('failure',['status','fetch','merge'])
def test_git_failures_are_reported_without_installation(installation,tmp_path,failure):
    checkout,seed,git,publish,update,_,environment=installation
    (seed/'version.txt').write_text('new\n');publish()
    previous=git(checkout,'rev-parse','HEAD')
    binary=tmp_path/'bin';binary.mkdir();wrapper=binary/'git'
    wrapper.write_text(f'#!/bin/sh\nif [ "$1" = {shlex.quote(failure)} ]; then echo "fixture Git failure" >&2; exit 42; fi\nexec {shlex.quote(GIT)} "$@"\n');wrapper.chmod(0o755)
    result=update({'PATH':str(binary)+os.pathsep+environment['PATH']})
    assert result.returncode!=0 and 'Update failed during' in result.stderr
    assert previous in result.stderr and git(checkout,'rev-parse','HEAD')==previous
    assert not (checkout/'install-runs').exists()


@pytest.mark.parametrize('remote_update',[False,True])
def test_local_commits_ahead_or_diverged_are_left_alone(installation,remote_update):
    checkout,seed,git,publish,update,_,_=installation
    (checkout/'local.txt').write_text('my local commit');git(checkout,'add','local.txt');git(checkout,'commit','-m','Local work')
    previous=git(checkout,'rev-parse','HEAD')
    if remote_update:(seed/'version.txt').write_text('remote\n');publish()
    result=update()
    assert result.returncode!=0 and 'ahead of or has diverged' in result.stderr
    assert git(checkout,'rev-parse','HEAD')==previous and not (checkout/'install-runs').exists()


def test_ignored_operator_file_cannot_be_overwritten_by_upstream(installation):
    checkout,seed,git,publish,update,preserved,_=installation
    previous=git(checkout,'rev-parse','HEAD');(seed/'config.toml').write_text('upstream must not overwrite operator data')
    git(seed,'add','-f','config.toml');publish();result=update()
    assert result.returncode!=0 and 'Fast-forward failed' in result.stderr
    assert git(checkout,'rev-parse','HEAD')==previous
    assert all(p.read_bytes()==before for p,before in preserved.items())
    assert not (checkout/'install-runs').exists()


def test_installer_failure_reports_updated_commit_without_rollback(installation):
    checkout,seed,git,publish,update,preserved,_=installation
    previous=git(checkout,'rev-parse','HEAD');(seed/'install.sh').write_text('#!/bin/sh\necho "fixture installer failure" >&2\nexit 23\n')
    updated=publish();result=update()
    assert result.returncode!=0 and 'Installer failed (exit 23)' in result.stderr
    assert previous in result.stderr and updated in result.stderr and 'no rollback' in result.stderr
    assert git(checkout,'rev-parse','HEAD')==updated
    assert all(p.read_bytes()==before for p,before in preserved.items())


def test_updater_can_replace_its_own_script_safely(installation):
    checkout,seed,git,publish,update,_,_=installation
    (seed/'update.sh').write_text('#!/bin/sh\nexit 77\n'+'# replacement padding\n'*1000)
    expected=publish();result=update()
    assert result.returncode==0,result.stderr
    assert git(checkout,'rev-parse','HEAD')==expected
    assert (checkout/'install-runs').read_text()=='installed\n'


@pytest.mark.parametrize('url',['git@github.com:kf6ufo/wsjtx-dashboard.git','ssh://git@github.com/kf6ufo/wsjtx-dashboard.git'])
def test_expected_ssh_origin_is_supported_without_network(installation,url):
    checkout,seed,git,_,update,_,environment=installation
    bare=(seed.parent/'origin.git').as_uri()
    git(checkout,'config','--file',environment['GIT_CONFIG_GLOBAL'],'--add',f'url.{bare}.insteadOf',url)
    git(checkout,'remote','set-url','origin',url)
    assert update().returncode==0


def test_missing_origin_stops_and_does_not_install(installation):
    checkout,_,git,_,update,_,_=installation
    git(checkout,'remote','remove','origin');result=update()
    assert result.returncode!=0 and 'origin remote is missing' in result.stderr
    assert not (checkout/'install-runs').exists()


def test_untracked_path_conflicts_are_not_overwritten(installation):
    checkout,seed,git,publish,update,_,_=installation
    (checkout/'new.txt').write_text('my untracked file')
    (seed/'new.txt').write_text('upstream file');publish();result=update()
    assert result.returncode!=0 and 'Fast-forward failed' in result.stderr
    assert (checkout/'new.txt').read_text()=='my untracked file'
    assert not (checkout/'install-runs').exists()


def test_edits_during_fetch_are_not_stashed_or_installed(installation,tmp_path):
    checkout,seed,git,publish,update,_,environment=installation
    (seed/'version.txt').write_text('upstream');publish()
    git(checkout,'config','merge.autoStash','true')
    binary=tmp_path/'bin';binary.mkdir();wrapper=binary/'git'
    wrapper.write_text(f'#!/bin/sh\nif [ "$1" = fetch ]; then\n  {shlex.quote(GIT)} "$@" || exit $?\n  printf "operator edit" > version.txt\n  exit 0\nfi\nexec {shlex.quote(GIT)} "$@"\n');wrapper.chmod(0o755)
    result=update({'PATH':str(binary)+os.pathsep+environment['PATH']})
    assert result.returncode!=0 and 'uncommitted changes' in result.stderr
    assert (checkout/'version.txt').read_text()=='operator edit'
    assert git(checkout,'stash','list')=='' and not (checkout/'install-runs').exists()
