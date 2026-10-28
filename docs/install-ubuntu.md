# Native Ubuntu installation — reviewed Steps 0–4

> Historical milestone guide. Use [current installation instructions](installation.md#ubuntu-prerequisites) and the [readiness checklist](release-readiness.md). Actual Ubuntu execution remains unverified; the dated installation states below are not current operator defaults.
> Current installer: compatible Node/npm is reused, or a checksum-verified temporary toolchain is downloaded automatically. A separate Node installation is optional.

**Ubuntu execution is untested for this rebuild.** These instructions use the same core installer/server/config/data as macOS. Mac reception and previous receiver experiments do not validate this installation or Linux behavior. Keep all current station services running; install separately on loopback port 8787. No systemd unit is installed or replaced.

Target Ubuntu 24.04+ with Python 3.12–3.14, Git and internet access; the installer obtains temporary Node build tools when needed. Install prerequisites as needed:

```sh
sudo apt update
sudo apt install git python3 python3-venv ca-certificates
```

No separate Node installation is required. See [temporary build tools](installation.md#temporary-node-build-tool) for automatic setup and the optional manual fallback. Verify `python3 --version` and `git --version`. Run the installer as an ordinary user, without sudo; it does not change global packages, radio settings or services.

Follow the [private GitHub authentication instructions](install-macos.md#private-repository-access), then run:

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard
cd ~/wsjtx-dashboard
git rev-parse HEAD
./install.sh
.venv/bin/python -m backend.server
```

Use the checkpoint's reviewed commit if pinning an installation. Success prints `Installation complete` and the URL. Open **http://127.0.0.1:8787/** on Ubuntu itself. This serves the production build. Stop with Ctrl+C, restart using the same command. Logs appear in the terminal. For a remote Mac browser without changing the bind address, open a second Mac terminal and tunnel:

```sh
ssh -N -L 8788:127.0.0.1:8787 jerry@YOUR_UBUNTU_HOST
```

Open **http://127.0.0.1:8788/** on the Mac. Replace host/user with authorized SSH access; close the tunnel with Ctrl+C. SSH authentication/tunneling has not been validated in this rebuild. Alternatively deliberately bind a specific trusted private LAN IPv4 in config, following the macOS guide's access limitations. No firewall/router changes are needed for the loopback/tunnel approach.

[Configuration, operations, updates, backup, migration, rollback and troubleshooting](install-macos.md#configuration-and-saved-settings) apply identically. For an occupied port use `ss -ltnp '( sport = :8787 )'` to identify it and select another port. Leave the old dashboard/WaveLogGate service untouched. A future optional systemd service needs its own validation, especially write access for persistent data; service management is outside this validated release.

Pending actual Ubuntu validation: prerequisites, dependency installation, production build, foreground start/stop/restart, saved settings/history, update preservation, LAN/tunnel access, and two-browser SSE/reconnection. UDP/multicast must be validated on each actual OS/interface. Mac results do not establish Ubuntu reception or socket sharing.

## Enrichment configuration

Step 3 includes the Step 2 enrichment and profile-photo work. Follow the [Step 2 guide](step-2.md) for provider options, QRZ XML credentials and cache policy. Existing Step 0/1 configurations remain valid, with enrichment disabled until configured. To roll back to Step 1, restore its pre-upgrade config/data backup because that revision rejects the enrichment section. Protect QRZ/Club Log credentials in config and backups.

## Step 3 configuration

Step 3 is included on **`main`**. For an existing clean checkout, stop only this dashboard, make the cold config/data backup above, then run `git fetch origin`, `git switch main` and `git pull --ff-only`, followed by `./install.sh`. Do not replace your config with the example. Step 0–2 configurations remain valid, with Wavelog disabled by default.

Configure the URL, API v2 token, station/logbook scope and cache limits in **Settings → Wavelog QSO history**. See [Step 3 setup](step-3.md). Saving this section applies immediately without restarting UDP or changing radio baselines. Tokens are stored only in the server’s ignored `config.toml`; protect backups too. History read results use memory caches; preserve the entire `data/` directory, including the durable delivery outbox, and any independently located ADIF file. See [optional QSO services](qso-services.md).

The installation commands use `main`. The update `git pull --ff-only` command follows whichever branch is currently checked out; verify `git branch --show-current` and the checkpoint before upgrading. To roll back to Step 2, stop the dashboard, preserve current files, use the prior revision and its pre-upgrade config/data backup, then rerun the installer. Step 2 rejects the new `[wavelog]` section, so restore its backed-up configuration too.

## Current baseline and optional delivery

`main` includes reviewed Steps 0–5 and 7 plus the disabled ADIF/history/durable delivery infrastructure. Both `logging_enabled` and `log_to_wavelog` default to false and remain false in the active installation. Keep them disabled while production WaveLogGate uploads contacts. Isolated real Wavelog write validation and explicit cutover approval are pending. See the [current checkpoint](current-checkpoint.md).

Back up any configured ADIF file in addition to `config.toml` and the entire `data/` directory, with this Dashboard stopped. Protect these backups as they contain credentials and operating data. Upgrades preserve the outbox and existing log files; never replace configuration with example defaults or delete pending work. For rollback, preserve current files first, restore the matching prior configuration/data/ADIF backup and run that revision’s installer.

## Steps 5 and 7 on main

The operator accepted Steps 5/7 and the display refinements for main through PR #6 on October 26, 2026. Use main for new installations and updates; the reviewed application source is `2890e02`. Back up the entire `data/` directory, including the new observation and forwarding-receipt SQLite databases, plus configuration and any configured ADIF file. Old configs load unchanged with 200-entry/manual history and no forwarding destinations. New history/forwarding Settings apply immediately and preserve unrelated sections. Rollback to older code requires its matching configuration backup because it rejects the new optional TOML sections. Dashboard Wavelog submissions remain disabled and WaveLogGate remains unchanged. See [behavior, configuration and GridTracker2 verification](steps-5-and-7.md).
