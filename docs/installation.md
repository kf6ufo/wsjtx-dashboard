# Installation and updates

[Documentation](README.md) · [Next: quick start](quick-start.md)

## Platforms and requirements

| Platform | Status |
| --- | --- |
| Native macOS | Verified on macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0 and Chrome; earlier guides target macOS 14+, but other combinations have not all been exercised |
| Native Ubuntu 24.04+ | Intended target using the same installer/configuration/storage; actual Ubuntu execution is not yet verified |
| Windows | No verified native installation; the ADIF writer uses POSIX file locking |
| Docker | No maintained, verified container installation in this pre-release |

Install Git and **Python 3.12–3.14**. Node/npm need not be installed beforehand: the installer can fetch a temporary build toolchain for macOS or Ubuntu on x64/ARM64. Map rendering needs a modern browser with WebGL. Installation downloads dependencies from PyPI/npm and, when needed, Node.js. Online enrichment and basemap tiles need internet access. No editor or global Python package installation is required.

### macOS prerequisites

Install Git through Apple's Command Line Tools if needed (`xcode-select --install`). Obtain Python from [python.org](https://www.python.org/downloads/macos/) or use your established package manager. Reopen Terminal, then check:

```sh
git --version
python3 --version
```

### Ubuntu prerequisites

These instructions await execution on Ubuntu:

```sh
sudo apt update
sudo apt install git python3 python3-venv ca-certificates
```

No Node apt package is needed for the automatic build-tool setup. Verify Git/Python using the commands above. Use sudo for OS packages only, not for the Dashboard installer/server. Actual Ubuntu execution remains unverified.

### Temporary Node build tool

The installer reuses Node **24.x, at least 24.15**, when both `node` and `npm` are available on PATH. Otherwise it downloads the appropriate **Node 24.21.0** archive from the [official release directory](https://nodejs.org/dist/v24.21.0/), verifies SHA-256 against the platform-specific hash pinned in the installer, and extracts it with Python's safe data filter. Downloads have size/time bounds; checksum failure stops installation before executing the downloaded tools.

The toolchain lives in a private temporary directory and is added only to the installer's child-process PATH. It is removed on completion or failure; shell profiles and global packages are unchanged. A later install/update downloads it again if no compatible Node/npm is available. The Python server needs only the built frontend afterward.

For offline/restricted-download environments or unsupported automatic-download architectures, install compatible Node/npm manually using [Node's instructions](https://nodejs.org/en/download), then check `node --version` and `npm --version`. Dependency installation still needs network access or suitable local package caches. Development commands such as `npm test` and `npm run dev` require Node/npm on PATH independently of the installer's temporary toolchain.

## Install from source

Choose a new directory so an existing station installation remains intact. The repository currently requires authorized access; use your GitHub credential manager or SSH setup, never a token embedded in a URL.

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git
cd wsjtx-dashboard
git rev-parse HEAD
./install.sh
.venv/bin/python -m backend.server
```

If `python3` selects an unsupported version, for example use `PYTHON=python3.13 ./install.sh`. Run one command at a time and stop on failure. The proposed beta tag is not published: these commands use `main`. Once a release is approved, select the actual published revision rather than assuming a proposed tag exists.

The installer creates `.venv`, installs pinned Python dependencies, runs `npm ci` and builds `dist`. It copies `config.example.toml` to `config.toml` **only if absent** and validates existing configuration. It does not start the server, enable integrations, open UDP reception or install launchd/systemd services.

## Start, stop and restart

From the installation directory:

```sh
.venv/bin/python -m backend.server
```

Open **http://127.0.0.1:8787/**. Keep the terminal open. Ctrl+C stops the server; allow time for open browser streams and in-flight requests to settle. Rerun the same command to restart. Logs appear in the terminal.

An alternative configuration location is supported:

```sh
.venv/bin/python -m backend.server --config /absolute/path/to/config.toml
```

The `data/` directory lives beside that configuration file; built frontend assets come from the source checkout. Start the intended checkout/configuration combination. HTTP host/port changes require restart; most Settings changes apply immediately.

The default HTTP listener is loopback. The server has **no user authentication**. A specific private LAN address is allowed for trusted clients, but anyone who can reach it can use administrative settings. Keep it off the public internet. Protect configuration, backups and logs; they may contain credentials or QSO data.

The installer/startup restricts configuration and private SQLite files to `0600`, and app-owned private data directories to `0700`. Existing contents/ownership are preserved; ADIF files and unrelated paths are not swept. Configuration/database files and private directory targets must be regular files/directories rather than symlinks. Access the server through `localhost`, `127.0.0.1` or its configured LAN IP; custom DNS names are rejected by the trusted-host policy.

## Files to preserve

- `config.toml`: configuration and server-side credentials.
- The entire `data/` directory: workspace, pending deliveries, observations, forwarding receipts and provider files. Include SQLite WAL/SHM sidecars if present.
- Every configured ADIF destination, including an older path still referenced by queued work. Files may be outside the installation directory.

Do not copy virtual environments or `node_modules` between operating systems. Do not delete a database or queue to fix an update problem.

## Updates and backups

Stop **only this Dashboard**, record `git rev-parse HEAD`, and make a private backup of all files listed above. This illustrates the configuration/data part; **also copy each ADIF file to that backup**, recording its original path:

```sh
mkdir -p backups
backup_stamp=$(date +%Y%m%d-%H%M%S)
mkdir "backups/$backup_stamp"
cp config.toml "backups/$backup_stamp/"
cp -R data "backups/$backup_stamp/"
git status --short
```

Inspect local changes before continuing. On a clean checkout tracking `main`:

```sh
git pull --ff-only
./install.sh
.venv/bin/python -m backend.server
```

Do not replace configuration with defaults or reset local changes. Stop on installer failure; do not start a partially built update. A detached release checkout needs an explicit `git fetch origin` and selection of the next reviewed commit. Repeated installation preserves settings/state, including previously enabled integrations.

## Rollback or move to another host

Stop Dashboard, preserve current files, and use the earlier source revision with its matching configuration/data backup. Rebuild dependencies there. ADIF is an independent log: restoring an older copy can erase later contacts, so retain the current file and reconcile any logging interval first. Restoring older receipts also needs review; uncertain Wavelog outcomes must not be blindly resubmitted.

For migration, copy configuration, complete stopped `data/` and ADIF files to the same revision on the destination. Rebuild there, select its receiving interface, and verify reception before logging. Pending targets retain absolute ADIF paths and Wavelog destinations; path changes hold work rather than redirect it. Actual macOS-to-Ubuntu migration remains untested. [Logging recovery](logging.md#delivery-and-recovery) explains held destinations.
