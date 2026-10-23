# Native macOS installation — Step 0

This installs a built frontend served by the Python server, independent of VS Code/Codex. Keep any existing station installation running and use a separate directory and unused HTTP port. The default is loopback port 8787. No radio/network/service settings are changed by the installer.

## Prerequisites

Supported target: macOS 14+ with Python 3.12–3.14, Git, and Node 24 LTS (24.15+) with npm. The checkpoint records the actual tested macOS/Python/Node versions, not a claim that every supported combination was exercised.

Install Python from [python.org](https://www.python.org/downloads/macos/) and Node 24 LTS from [nodejs.org](https://nodejs.org/en/download), or use your existing package manager. Git is available through Apple's command line tools (`xcode-select --install` if missing). Reopen Terminal after installing. Verify:

```sh
python3 --version
node --version
npm --version
git --version
```

If your Python command selects another version, use e.g. `PYTHON=python3.13 ./install.sh`. Do not run the installer with sudo. It creates an isolated virtual environment; no global Python packages are installed. Internet access to GitHub, PyPI and npm is required while building.

## Private repository access

Use your configured GitHub credential manager or SSH key. For HTTPS prompts, enter your GitHub username and a repository-authorized personal access token as the password, never an account password. A fine-grained token limited to this repository with Contents read permission suffices to clone/pull. Do not embed credentials in command URLs, configuration, screenshots or chat. See [GitHub authentication](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github).

## Install

**Until publication is approved**, the branch is local to the development Mac. For a durable independent installation on this Mac, use:

```sh
git clone --shared --branch rebuild/step-0 /Users/jerryjoplin/Documents/GitHub/wsjtx-dashboard ~/wsjtx-dashboard-rebuild
cd ~/wsjtx-dashboard-rebuild
./install.sh
.venv/bin/python -m backend.server
```

This local clone shares the preserved repository's Git object storage to avoid copying cloud-evicted historical objects, but gets its own source files, dependencies, configuration and workspace. Keep the source repository intact. The server needs no editor. Normal GitHub clones below are independent repositories and become usable once the branch is published. Stop the temporary review server first, or choose another HTTP port in your new checkout's config.

Run each command and stop if it fails. If the destination exists, choose a different directory; do not delete or reset it.

```sh
git clone --branch rebuild/step-0 https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard-rebuild
cd ~/wsjtx-dashboard-rebuild
git rev-parse HEAD
./install.sh
.venv/bin/python -m backend.server
```

Compare the commit to the current checkpoint. For an exact reviewed commit, run `git checkout --detach COMMIT` before installation, substituting its full hash. Success prints `Installation complete`, the start command and URL. Open **http://127.0.0.1:8787/**. This is the server serving the production build, not Vite. Keep the terminal open. Ctrl+C stops cleanly; the application does not depend on an editor. A foreground command is the supported initial macOS installation, with no launchd/autostart changes.

`./install.sh` creates `config.toml` exclusively only if missing. Existing files are validated and preserved byte-for-byte. An old configuration with enabled reception fails clearly instead of activating it. For a rebuild alongside an older station installation, use the new checkout's default config; leave the old checkout/config untouched.

## Configuration and saved settings

```toml
[http]
host = "127.0.0.1"
port = 8787

[wsjtx]
enabled = false
group = "239.255.0.73"
port = 2238
interface = "127.0.0.1"
```

Edit the ignored `config.toml`, then restart the server to change the HTTP address/port. A specific private LAN IPv4 is allowed for trusted LAN clients; loopback is the default. No wildcard/public address, public hosting or router changes. Step 0 is unauthenticated, so anyone with access to the bound interface can select samples and edit workspace preferences. Browser writes reject cross-origin requests; this is not a substitute for LAN access control. Keep loopback unless you deliberately want trusted LAN access.

The `[wsjtx]` section is reserved compatibility structure, with historical example group/port only. `enabled=true` is refused in Step 0, even if an old environment variable requests reception. Nothing joins the group or listens on UDP.

Settings saves station title, default appearance and compact strip visibility to `data/workspace.sqlite3` alongside the config. Shared sample focus/history and provenance are stored there too and restored after restart. Installation configuration and browser preferences are separate scopes in one documented configuration system. No credentials are collected. Sample contacts are fixtures, not a second logbook. History is deduplicated and bounded (200 entries; six sample calls available). Seed data is created only for a new workspace. Header Theme/Station Desk buttons preview locally; Save in Settings establishes shared defaults.

## Operation and updates

Stop this foreground server with Ctrl+C. Restart with:

```sh
cd ~/wsjtx-dashboard-rebuild
.venv/bin/python -m backend.server
```

Startup, request and error logs appear in that terminal. To retain a local log, append `2>&1 | tee -a dashboard.log`; Ctrl+C stops it. Do not commit logs.

Before updating, stop only this dashboard and record `git rev-parse HEAD`. Back up configuration and state with the server stopped:

```sh
mkdir -p backups
backup_stamp=$(date +%Y%m%d-%H%M%S)
mkdir "backups/$backup_stamp"
cp config.toml "backups/$backup_stamp/"
cp -R data "backups/$backup_stamp/"
git status --short
git pull --ff-only
./install.sh
.venv/bin/python -m backend.server
```

This update command assumes the tracking rebuild branch. For a detached reviewed commit, choose the next reviewed commit explicitly with `git fetch origin` and `git checkout --detach COMMIT`. Stop on local changes, divergent Git history or any installer error. Do not recopy example defaults. Failed installs are not automatically rolled back; do not start a partially built update. Repeated installs preserve configuration/state. No service is stopped/started by the installer.

For rollback, stop the dashboard, preserve the failed checkout and current data, check out the recorded prior **rebuild** commit (or clone it separately), restore that revision's backed-up config/data, rerun `./install.sh`, then start. Never use `git reset --hard` or delete user work. A pre-rebuild rollback uses the preserved predecessor checkout and its historical installation procedure; do not point predecessor code at the new workspace database. No predecessor persistent history existed to migrate. Upgrade preservation from Step 0 to Step 1 must be validated when Step 1 exists.

## Moving to Ubuntu

With the server stopped, copy only `config.toml` and `data/` to a clean checkout of the same revision on Ubuntu. Adjust HTTP binding for that host; keep reception disabled. Build dependencies there with `./install.sh`. Do not copy `.venv`, `node_modules`, `.tools` or `dist` across platforms. No pending-QSO queue exists in Step 0; Step 6 must document queue migration before enabling it. The application never imports production QSO logs.

## Troubleshooting and validation

- `node`/`npm` missing or unsupported: install Node 24 LTS, reopen Terminal, and check PATH. The installer reports the failure and can be rerun.
- Python/venv/pip failure: verify supported Python and internet access. Use the same interpreter for repeat installs. Do not share virtual environments across OS/interpreter installations.
- `Address already in use`: identify the listener with `lsof -nP -iTCP:8787 -sTCP:LISTEN`; choose another port in this checkout's config. Do not kill station services to free a port.
- Config error: the message includes the file. Compare keys with the example; repair the file rather than overwrite your settings. Changes require restart.
- Missing built frontend: rerun the installer successfully. A build failure exits nonzero.
- Disconnected/stale banner: confirm the server is running and `/api/snapshot` loads. EventSource reconnects with a complete snapshot; no refresh should be necessary. There is a 32-stream limit, bounded one-snapshot queues, and a 15-second heartbeat.
- Database error: stop, back up `data/`, check permissions/free disk. Unknown schema versions fail without replacing data. Do not delete a database as an automatic repair.

Review with two windows: select samples in Demo tools; browse an older card; take one window offline while another selects; reconnect and check current focus/order; save Settings, restart, and verify preferences/history. [Current checkpoint](current-checkpoint.md) records automated and actual platform evidence.
