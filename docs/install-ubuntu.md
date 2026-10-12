# Install on Ubuntu

This is the complete fresh-install procedure for the station Ubuntu host **10.176.1.6**, using GitHub source and a matching prebuilt frontend. Ubuntu needs **no Node, Codex or ChatGPT app**. Development/builds remain on macOS. Run each numbered step separately and check its result before continuing.

The stable installation is **`/home/jerry/wsjtx-dashboard`** for user `jerry` (`$HOME/wsjtx-dashboard` below). This guide targets Ubuntu 24.04 with Python 3.12 and the station interface 10.176.1.6. The explicit launcher receives multicast **239.255.0.73:2238** on that interface. Other station addresses require a separately reviewed configuration.

Install release [m2-validation-20261012](https://github.com/kf6ufo/wsjtx-dashboard/releases/tag/m2-validation-20261012), source commit **`f06ba397b9f508b0e5722b856295d6c9064c85fc`**. Its required assets are `frontend.tar.gz` and `frontend.tar.gz.sha256`. Archive SHA-256: `cacf903dca90f170c05df41f57a081d831a5e5bd95a38375815da0987f0be854`. The installer downloads/checks these assets and installs both backend dependencies and frontend. This guide on GitHub main may contain newer documentation than the pinned application release; that is intentional.

No steps below change WSJT-X, WaveLogGate, radio settings, router settings or other station services. Keep temporary validation folders and the separate `Downloads/wsjtx_focus_probe.py`. Profiles and QSO history remain clearly labeled **samples**; no Wavelog/QRZ access or QSO submission is implemented.

## 1. Inspect existing processes and installation

**Where:** an Ubuntu terminal, including an SSH terminal opened from the Mac. **Purpose:** identify any prior dashboard and determine whether the stable directory already exists. This step is read-only.

```sh
ss -ltnp '( sport = :8000 )'
python3 - <<'PY'
from pathlib import Path
root = Path.home() / 'wsjtx-dashboard'
print(f'Installation path: {root}')
if root.exists() or root.is_symlink():
    print('EXISTS: preserve this path before a fresh installation.')
    print(f'Symlink: {root.is_symlink()}')
else:
    print('ABSENT: available for a fresh installation.')
found = False
for process in Path('/proc').iterdir():
    if not process.name.isdigit():
        continue
    try:
        args = (process / 'cmdline').read_bytes().split(b'\0')
        if b'backend.app:app' in args:
            cwd = (process / 'cwd').readlink()
            print(f'Dashboard candidate PID {process.name}; directory {cwd}')
            found = True
    except (OSError, PermissionError):
        pass
if not found:
    print('No accessible backend.app:app process found.')
PY
```

**Success:** the commands show the directory as `ABSENT` or `EXISTS` and list any accessible dashboard candidates. A free port shows only the `ss` header. An occupied port shows its listener/PID. A candidate is not permission to stop it: confirm its working directory belongs to this dashboard. If the port is occupied by something else, stop here and inspect; never free it by stopping unrelated services. If a suspected dashboard is inaccessible, inspect its identity before proceeding.

The previous temporary dashboard was Uvicorn PID **60357**, working directory `/home/jerry/wsjtx-m2-validation.JrNjUo/wsjtx-dashboard`, listening on 127.0.0.1:8000. These are historical observations, not assumptions about what is running now. The separate focus probe (previously PID 17225, working directory Downloads) is not this server and should remain untouched.

## 2. Stop only an identified dashboard

**Where:** Ubuntu, preferably its original server terminal. **Purpose:** avoid competing dashboards and allow a safe fresh installation.

Press **Ctrl+C** in the identified dashboard's original terminal. **Success:** Uvicorn reports shutdown complete/process finished and returns to a shell prompt.

If that terminal is unavailable, use the **current PID from step 1**, first checking its working directory again:

```sh
readlink /proc/CONFIRMED_PID/cwd
```

Replace `CONFIRMED_PID` with the actual number; do not type the placeholder. Only when that directory is confirmed as this dashboard, stop that same process with `kill -TERM CONFIRMED_PID`. Do not blindly reuse 60357, use `pkill`, or stop all Python processes. If several dashboard candidates exist, identify and stop each dashboard individually. Do not remove any files.

In an Ubuntu terminal, repeat:

```sh
ss -ltnp '( sport = :8000 )'
```

**Success:** only the header remains. Recheck step 1 if anything still listens.

## 3. Preserve an existing stable installation

**Where:** Ubuntu. **Purpose:** create a fresh stable checkout without overwriting an old installation. Do this only after any dashboard using the old directory is stopped. Skip renaming if step 1 reported `ABSENT`.

```sh
python3 - <<'PY'
from pathlib import Path
import tempfile
root = Path.home() / 'wsjtx-dashboard'
if root.exists() or root.is_symlink():
    backup = Path(tempfile.mkdtemp(prefix='wsjtx-dashboard.previous.', dir=Path.home()))
    destination = backup / 'wsjtx-dashboard'
    root.rename(destination)
    print(f'Preserved existing installation at {destination}')
else:
    print(f'No existing installation; {root} is available.')
PY
```

**Success:** prints the preserved location (record it), or confirms there was nothing to preserve. It renames only the stable dashboard path, including its environment/configuration; it never deletes it or touches temporary validation folders. Stop on any error. No merge, reset or cleanup is needed.

## 4. Check and install prerequisites

**Where:** Ubuntu. **Purpose:** ensure the runtime and GitHub download tools exist.

```sh
whoami
python3 --version
git --version
gh --version
ip -br -4 addr
```

**Success:** user `jerry`, Python 3.12 or newer, Git and GitHub CLI version lines, and an UP interface with **10.176.1.6**. Do not alter network/radio settings if that address is absent; investigate first.

If Git, GitHub CLI or Python venv support is missing, install the prerequisites on Ubuntu:

```sh
sudo apt update
sudo apt install git gh python3-venv
```

**Success:** packages install or are reported already current. This does not upgrade the whole system or install Node/Codex. Python's `.venv` creation is checked during step 6; if Ubuntu reports missing venv support, install `python3-venv` and repeat step 6 before starting.

## 5. Authenticate to GitHub

**Where:** Ubuntu terminal; complete any device authorization in a **Mac browser**. **Purpose:** allow this private repository and its release assets to be downloaded.

```sh
gh auth status --hostname github.com
```

**Success:** an authorized GitHub account is listed. If not authenticated, run:

```sh
gh auth login --hostname github.com --git-protocol https --web
```

Use the displayed GitHub device URL/code in your Mac browser if Ubuntu cannot open one. The account must have access to `kf6ufo/wsjtx-dashboard`. Then run:

```sh
gh auth setup-git
gh repo view kf6ufo/wsjtx-dashboard --json nameWithOwner
```

**Success:** authentication completes, Git setup exits without error, and repository output contains `kf6ufo/wsjtx-dashboard`. Do not paste passwords, tokens or device codes into chat or embed credentials in URLs. This is GitHub CLI authentication, not a Codex/ChatGPT installation.

## 6. Install source, backend and built frontend

**Where:** Ubuntu. **Purpose:** install the pinned GitHub release into the now-available stable directory.

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git "$HOME/wsjtx-dashboard"
```

**Success:** clone completes without errors. Only then continue:

```sh
cd "$HOME/wsjtx-dashboard"
python3 scripts/install-ubuntu.py m2-validation-20261012
```

**Success:** the installer downloads the frontend assets, verifies their checksum and source revision, creates `.venv`, installs Python dependencies, and prints:

```text
Installed m2-validation-20261012 at f06ba397b9f508b0e5722b856295d6c9064c85fc. Start manually: ./scripts/start-station.sh
```

The installer refuses a dirty/unexpected checkout, an occupied dashboard port, unsafe archive paths/links or a mismatched frontend. It never starts services. A Git clone by itself is not a complete installation. If clone fails, stop before the `cd`/installer commands; do not run them from another checkout. If installation fails, keep the error output and resolve it before starting. Never use `git reset --hard`, remove the stable directory, or modify other services to force success.

## 7. Verify the complete installation

**Where:** Ubuntu, in `$HOME/wsjtx-dashboard`. **Purpose:** confirm the frontend/backend revision and isolated dependencies before enabling reception.

```sh
git rev-parse HEAD
.venv/bin/python -m pip check
.venv/bin/python - <<'PY'
import json
from pathlib import Path
import subprocess
import fastapi
import uvicorn
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert Path('dist/index.html').is_file(), 'Missing frontend'
assert json.loads(Path('dist/frontend.json').read_text())['commit'] == commit, 'Revision mismatch'
print(f'Frontend and backend ready at {commit}')
PY
```

**Success:** the exact commit above, `No broken requirements found.`, and `Frontend and backend ready at ...`. Do not start if any check fails.

## 8. Start manually

**Where:** Ubuntu, in `$HOME/wsjtx-dashboard`. **Purpose:** start one receive-only process serving both dashboard and API.

```sh
./scripts/start-station.sh
```

**Success:** Uvicorn reports application startup complete and running on **http://10.176.1.6:8000**. Leave this terminal running. No systemd/autostart service is installed. Startup alone does not prove radio reception. Do not change either WSJT-X selection until you check the initial baselines in step 9.

## 9. Open from the Mac and check initial state

**Where:** a **Mac browser** on the trusted station LAN. **Purpose:** access the real Ubuntu runtime without a tunnel or any public exposure.

Open **http://10.176.1.6:8000/?mode=live**.

**Success:** the dashboard loads with live radio connectivity and **Sample profiles/QSOs** clearly visible. Before any new DX-call selection, expect `Waiting for a WSJT-X selection` and empty Focus History. Expand Station Desk to see rigs once their Status packets arrive. The first Status from each rig must establish a baseline without a history entry. Wait for both IDs before testing subsequent selections. A missing initial Status needs investigation, not a change to production radio configuration.

For evidence, run in a second **Ubuntu terminal**:

```sh
curl -fsS http://10.176.1.6:8000/api/snapshot | python3 -m json.tool
```

**Success:** receiver `listening` without an error; packet counters increase; both rig IDs appear after their Status packets; initial `call` is empty and `history` is `[]` before any later selection. Listening without packets is not verified reception.

HTTP binds specifically to **10.176.1.6**, not every interface. No router port forwarding, SSH tunnel or public hosting is needed. The service is unauthenticated plain HTTP for the trusted LAN. If the Mac cannot connect, inspect the existing Ubuntu firewall/network before any narrow LAN-only rule is proposed; never disable the firewall or open a router port as an installation workaround.

## 10. Validate and stop manually

**Where:** actual WSJT-X windows and two browsers. **Purpose:** finish live acceptance separately from installation success.

Select a different valid callsign in each WSJT-X instance and verify immediate dashboard updates with the correct rig. Let routine decodes arrive with no selections: focus/history must stay unchanged. Browse an older dashboard history entry: both browsers should display it without reordering history or changing radio timestamps/provenance. Disconnect/reconnect one browser and verify recovery to the complete shared state. Check samples remain labeled and existing WaveLogGate operation continues. See [Milestone 2 evidence and remaining checks](milestone-2.md#station-validation-status-and-remaining-acceptance).

**To stop:** press **Ctrl+C** in the Ubuntu dashboard terminal. **Success:** shutdown completes and the shell prompt returns. Other station services stay running. To start again, run `cd "$HOME/wsjtx-dashboard"` then `./scripts/start-station.sh`. Each restart resets in-memory focus/history and establishes new rig baselines.

## Later updates

Use the [published GitHub update procedure](milestone-2.md#ubuntu-repeatable-updates) after stopping only this dashboard. Install a new explicit release tag with matching frontend assets. Keep the preserved previous installation and temporary validation folders until separately authorized to remove them.
