# Native macOS installation — Steps 0–3

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

Run each command and stop if it fails. If the destination exists, choose a different directory; do not delete or reset it.

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard
cd ~/wsjtx-dashboard
git rev-parse HEAD
./install.sh
.venv/bin/python -m backend.server
```

Compare the commit to the current checkpoint. For an exact reviewed commit, run `git checkout --detach COMMIT` before installation, substituting its full hash. Success prints `Installation complete`, the start command and URL. Open **http://127.0.0.1:8787/**. This is the server serving the production build, not Vite. Keep the terminal open. Ctrl+C stops (allow up to five seconds for open browser streams, plus any in-flight provider network timeout); the application does not depend on an editor. A foreground command is the supported initial macOS installation, with no launchd/autostart changes.

`./install.sh` creates `config.toml` exclusively only if missing. Existing files are validated and preserved byte-for-byte. The installer never opens a receiver socket. On startup, an enabled receiver in config is honored; review preserved settings before starting. For a new installation alongside an older station installation, use the new checkout's default config; leave the old checkout/config untouched.

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
listen = "0.0.0.0"
retention = 200
```

Edit the ignored `config.toml`, then restart the server to change the HTTP address/port. A specific private LAN IPv4 is allowed for trusted LAN clients; loopback is the default. No wildcard/public address, public hosting or router changes. The dashboard is unauthenticated, so anyone with access to the bound interface can change receiver/provider settings and use saved provider credentials through lookups, as well as browse history and edit workspace preferences. Browser writes reject cross-origin requests; this is not a substitute for LAN access control. Keep loopback unless you deliberately want trusted LAN access.

The `[wsjtx]` section is the actual receiver configuration. Step 0 files remain valid; new `listen` and `retention` keys default to `"0.0.0.0"` and `200`. Settings saves these fields into this same TOML and applies changes immediately. Choose the receiving host interface before enabling multicast. See the [Step 1 guide](step-1.md) for restart/baseline, coexistence, retention and troubleshooting behavior. Installed operation reads TOML, not old receiver environment variables.

Settings saves default appearance and compact strip visibility to `data/workspace.sqlite3` alongside the config. Shared sample history is retained separately from the new persistent radio history. Preferences and both histories survive restart; packet logs, telemetry and receiver baselines are memory-only. Installation configuration and browser preferences are separate scopes in one documented configuration system. Optional callbook credentials are configured in Settings and saved only on the server; see [Step 2](step-2.md). Sample contacts are fixtures, not a second logbook. Each history is deduplicated and bounded (200 entries; six sample calls available). After the first receiver activation, the radio workspace remains active on disable/restart; it never seeds sample selections. Seed data is created only for a new workspace. Theme in the header and Station Desk in Settings preview locally; Save in Settings establishes shared defaults. The Step 4 preview hides the legacy station-title setting while preserving its stored value.

## Operation and updates

Stop this foreground server with Ctrl+C. Restart with:

```sh
cd ~/wsjtx-dashboard
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

This update command assumes the tracking `main` branch. For a detached reviewed commit, choose the next reviewed commit explicitly with `git fetch origin` and `git checkout --detach COMMIT`. Stop on local changes, divergent Git history or any installer error. Do not recopy example defaults. Failed installs are not automatically rolled back; do not start a partially built update. Repeated installs preserve configuration/state. No service is stopped/started by the installer.

For rollback, stop the dashboard, preserve the failed checkout and current data, check out the recorded prior reviewed commit (or clone it separately), restore that revision's backed-up config/data, rerun `./install.sh`, then start. Never use `git reset --hard` or delete user work. A pre-rebuild rollback uses the preserved predecessor checkout and its historical installation procedure; do not point predecessor code at the new workspace database. No predecessor persistent history existed to migrate. For an existing Step 0 or `rebuild/step-1` checkout, stop only that dashboard, back up config/data, then switch to the reviewed installation branch:

```sh
git fetch origin
git switch main
git pull --ff-only
```

If Git reports local changes or divergence, stop and inspect; do not reset or force it. Run the installer, then start. Old config keys require no manual migration; sample history/preferences and existing radio history are retained. A Step 0 workspace starts with empty radio history. To roll back to Step 0, disable reception before stopping and restore its pre-upgrade config/data backup.

## Moving to Ubuntu

With the server stopped, copy only `config.toml` and `data/` to a clean checkout of the same revision on Ubuntu. Adjust HTTP binding for that host; keep reception disabled. Build dependencies there with `./install.sh`. Do not copy `.venv`, `node_modules`, `.tools` or `dist` across platforms. No pending-QSO queue exists in Step 3; Step 6 must document queue migration before enabling it. The application never imports production QSO logs.

## Troubleshooting and validation

- `node`/`npm` missing or unsupported: install Node 24 LTS, reopen Terminal, and check PATH. The installer reports the failure and can be rerun.
- Python/venv/pip failure: verify supported Python and internet access. Use the same interpreter for repeat installs. Do not share virtual environments across OS/interpreter installations.
- `Address already in use`: identify the listener with `lsof -nP -iTCP:8787 -sTCP:LISTEN`; choose another port in this checkout's config. Do not kill station services to free a port.
- Config error: the message includes the file. Compare keys with the example; repair the file rather than overwrite your settings. HTTP edits require a server restart; receiver changes in Settings apply immediately.
- Missing built frontend: rerun the installer successfully. A build failure exits nonzero.
- Disconnected/stale banner: confirm the server is running and `/api/snapshot` loads. EventSource reconnects with a complete snapshot; no refresh should be necessary. There is a 32-stream limit, bounded one-snapshot queues, and a 15-second heartbeat.
- Database error: stop, back up `data/`, check permissions/free disk. Unknown schema versions fail without replacing data. Do not delete a database as an automatic repair.

Review with two windows using the [Step 1 acceptance procedure](step-1.md#operator-check). Save receiver settings, inspect actual packets in Diagnostics, then change a DX Call in each WSJT-X instance; browse older entries and verify reconnect recovery. [Current checkpoint](current-checkpoint.md) records automated and actual platform evidence.

## Enrichment configuration

Step 3 includes the Step 2 enrichment and profile-photo work. Follow the [Step 2 guide](step-2.md) for provider options, QRZ XML credentials and cache policy. Existing Step 0/1 configurations remain valid, with enrichment disabled until configured. To roll back to Step 1, restore its pre-upgrade config/data backup because that revision rejects the enrichment section. Protect QRZ/Club Log credentials in config and backups.

## Step 3 configuration

Step 3 is included on **`main`**. For an existing clean checkout, stop only this dashboard, make the cold config/data backup above, then run `git fetch origin`, `git switch main` and `git pull --ff-only`, followed by `./install.sh`. Do not replace your config with the example. Step 0–2 configurations remain valid, with Wavelog disabled by default.

Configure the URL, API v2 token, station/logbook scope and cache limits in **Settings → Wavelog QSO history**. See [Step 3 setup](step-3.md). Saving this section applies immediately without restarting UDP or changing radio baselines. Tokens are stored only in the server’s ignored `config.toml`; protect backups too. Contacts are held only in bounded memory caches, so there is no QSO database to migrate.

The installation commands use `main`. The update `git pull --ff-only` command follows whichever branch is currently checked out; verify `git branch --show-current` and the checkpoint before upgrading. To roll back to Step 2, stop the dashboard, preserve current files, use the prior revision and its pre-upgrade config/data backup, then rerun the installer. Step 2 rejects the new `[wavelog]` section, so restore its backed-up configuration too.
