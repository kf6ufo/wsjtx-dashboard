# Native Ubuntu installation — Steps 0–3

**Ubuntu execution is untested for this rebuild.** These instructions use the same core installer/server/config/data as macOS. Mac reception and previous receiver experiments do not validate this installation or Linux behavior. Keep all current station services running; install separately on loopback port 8787. No systemd unit is installed or replaced.

Target Ubuntu 24.04+ with Python 3.12–3.14, Git, Node 24 LTS (24.15+) and npm. Install prerequisites as needed:

```sh
sudo apt update
sudo apt install git python3 python3-venv ca-certificates
```

Install Node 24 LTS for your architecture using [official Node instructions/downloads](https://nodejs.org/en/download); Ubuntu's default Node package may not meet the required version. Verify `node --version`, `npm --version`, and `python3 --version`. Native installer commands run as an ordinary user, without sudo. It does not upgrade global packages, modify radio/network settings or manage services.

Follow the [private GitHub authentication instructions](install-macos.md#private-repository-access), then run:

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard
cd ~/wsjtx-dashboard
git switch feature/step-3-wavelog
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

## Step 2 preview and configuration

For the unreviewed Step 2 preview, select `feature/step-2-enrichment` after cloning and before running the installer. Existing Step 0/1 TOML and workspace data remain compatible; enrichment defaults disabled until configured. Follow the [Step 2 guide](step-2.md) for providers, QRZ XML credentials, cache policy and operator review. Back up config/data before upgrading; restoring a Step 1 revision also requires its pre-upgrade configuration backup because Step 1 does not accept the new enrichment section. QRZ and Club Log credentials in config/backups need the same care as other account passwords.

## Step 3 preview and configuration

The current preview branch is **`feature/step-3-wavelog`**, including Step 2 enrichment/photos. Choose it after cloning and before installation. For an existing clean checkout, stop only this dashboard, make the cold config/data backup above, then run `git fetch origin` and `git switch feature/step-3-wavelog`, followed by `./install.sh`. Do not replace your config with the example. Step 0–2 configurations remain valid, with Wavelog disabled by default.

Configure the URL, API v2 token, station/logbook scope and cache limits in **Settings → Wavelog QSO history**. See [Step 3 setup](step-3.md). Saving this section applies immediately without restarting UDP or changing radio baselines. Tokens are stored only in the server’s ignored `config.toml`; protect backups too. Contacts are held only in bounded memory caches, so there is no QSO database to migrate.

The installation commands select the preview branch. The update `git pull --ff-only` command follows whichever branch is currently checked out; verify `git branch --show-current` and the checkpoint before upgrading. To roll back to Step 2, stop the dashboard, preserve current files, use the prior revision and its pre-upgrade config/data backup, then rerun the installer. Step 2 rejects the new `[wavelog]` section, so restore its backed-up configuration too.
