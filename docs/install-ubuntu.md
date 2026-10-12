# Install on Ubuntu

Install directly from GitHub source. The same command installs and updates the backend, builds the frontend **on Ubuntu**, and installs the systemd service. No GitHub release files, frontend checksum downloads, matching-commit checks, Mac-built assets, Node source edits, or Codex/ChatGPT app are required.

Live WSJT-X selection handling is implemented. **Profile/QSO enrichment is still sample data**, clearly labeled in the dashboard; unknown real calls have unavailable sample history rather than invented contacts. The app never submits QSOs or commands radios. Keep WSJT-X, WaveLogGate and other station services/configuration untouched.

## Prerequisites and privileges

- Ubuntu **24.04 or newer**, Python **3.12+**, running systemd, and a normal user with sudo rights. Ubuntu's standard Python is suitable.
- Git for cloning. If missing: `sudo apt update` then `sudo apt install git`. Use a preferred text editor (`nano` in the examples; `sudo apt install nano` if missing).
- Clone access to the private GitHub repository. Reuse authorized HTTPS/SSH Git access; GitHub CLI is not an application prerequisite. Never put access tokens in clone URLs or paste credentials into chat.
- Internet access during installation for Ubuntu packages, PyPI, npm, and (if needed) nodejs.org.

Run `./install.sh` **without sudo**. It checks the host, configuration, service state and configured HTTP port before installation. Missing `python3-venv`, `ca-certificates`, Git and `xz-utils` packages are installed through sudo apt. It reuses Node **24 LTS, version 24.15+**, if available; otherwise it installs official Node **24.21.0 LTS** into this checkout's ignored `.tools` directory (x86_64/arm64), without replacing system Node or changing shell startup files. [Node's download page](https://nodejs.org/en/download) identifies the supported LTS release. Node is only needed during frontend builds.

The installer creates/refreshes `.venv`, installs Python requirements, runs `npm ci` and `npm run build`, verifies the generated unit with `systemd-analyze verify`, then uses sudo to install `/etc/systemd/system/wsjtx-dashboard.service` and reload systemd. The server runs as the user who installed it, **not root**. Sudo may request your Ubuntu password. No package-wide upgrade, radio/firewall/router changes, service start/stop, or automatic boot enablement is performed.

## GitHub authentication for HTTPS cloning

GitHub account passwords do not work at Git's HTTPS password prompt. For this private repository, use a [fine-grained personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), or reuse already configured GitHub SSH access.

On a Mac browser, sign in to GitHub as `kf6ufo` and open [Fine-grained personal access tokens](https://github.com/settings/personal-access-tokens/new). Give the token a recognizable name and expiry. Choose resource owner `kf6ufo`, **Only select repositories → wsjtx-dashboard**, and repository permission **Contents → Read-only**. Generate and keep the token in your password manager; GitHub displays it once. This read-only permission is enough for cloning and later pulls.

On Ubuntu, run the documented `git clone` command. At the prompts enter username `kf6ufo` and paste the **token** at the password prompt. Terminal input is hidden. Do not use your account password, embed the token in a URL/command, or paste it into chat. If authentication fails, verify repository access, token expiry and Contents permission before retrying. If a retry reports that the destination exists, inspect/preserve it rather than deleting it.

## Existing installations and migration

Use stable directory **`~/wsjtx-dashboard`** (`/home/jerry/wsjtx-dashboard` for our station). If it already exists, do not clone over it or delete it. Inspect it first. If you want a fresh checkout, stop only an identified dashboard and rename the existing directory to a unique backup before cloning. Preserve `config.toml` from any existing installation. Leave all temporary validation folders intact.

Before migration, identify listeners using `ss -ltnp '( sport = :8000 )'` (or the configured HTTP port). An older manually started dashboard must be stopped in its own terminal with Ctrl+C, after confirming it belongs to this project. Do not kill an old PID blindly or stop unrelated listeners. The installer refuses an occupied configured HTTP port and refuses to overwrite a service unit that lacks its managed marker. Existing production station services must stay running.

A checkout from the retired release-based installer may be detached at an old tag. Inspect `git status` and preserve local files before switching it back to `main`; the normal update procedure requires a branch. Fresh clones already use `main`. No old installation has been migrated by preparing these instructions.

## First installation

Run each command **on Ubuntu as your normal user**. Stop on an error instead of continuing in the wrong directory.

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard
cd ~/wsjtx-dashboard
cp config.example.toml config.toml
nano config.toml
./install.sh
sudo systemctl start wsjtx-dashboard
```

Success: the installer prints `Installation complete`, followed by the start command and configured browser URL. `sudo systemctl status wsjtx-dashboard` should show `active (running)` after start. The installer does not start the service; service startup still needs checking. A frontend build or dependency failure exits nonzero with `Installation failed` and leaves the service stopped; resolve the reported issue and rerun the same command. Failed updates are not automatically rolled back. The unit is updated only after dependencies and frontend build succeed.

## One configuration file

The **only installed runtime configuration** is `config.toml` in the checkout. It is ignored by Git and preserved by `./install.sh` and `git pull`. Copy the example only on first installation. The service reads the TOML directly; it is not sourced as shell code.

```toml
[http]
host = "10.176.1.6"
port = 8000

[wsjtx]
enabled = true
group = "239.255.0.73"
port = 2238
interface = "10.176.1.6"
```

`http.host` is a specific private LAN/loopback **IPv4** address owned by Ubuntu. Wildcard/public addresses are refused. Both ports must be integers from 1024 through 65535 so the service needs no root networking privileges. `wsjtx.group` must be multicast. `wsjtx.interface` is the local receiver IPv4 address, never a sending radio's IP. Set `enabled = false` to run without joining multicast. Bad/missing configuration fails with its file path and a clear explanation.

Check `ip -br -4 addr` if unsure of the Ubuntu address. Do not change production network/radio settings to match the example. Edit the file to match the host. Restart the dashboard after configuration changes; no source edits or reinstallation is needed for address/port changes.

## Browser access and operation

On a **Mac browser** on the same trusted LAN, open:

**http://10.176.1.6:8000/?mode=live**

Use your configured HTTP address/port if different. HTTP binds only to that specific address. No router port forwarding or public hosting is needed. This is unauthenticated HTTP intended for the trusted LAN. If an existing Ubuntu firewall blocks Mac access, inspect it before proposing a narrow LAN-only rule; do not disable the firewall or expose the service publicly.

Run **on Ubuntu**:

```sh
sudo systemctl start wsjtx-dashboard
sudo systemctl stop wsjtx-dashboard
sudo systemctl restart wsjtx-dashboard
sudo systemctl status wsjtx-dashboard
```

Each service restart resets in-memory focus/history and establishes fresh per-rig baselines. The service restarts after an unexpected failure, but an explicit `systemctl stop` keeps it stopped. The installer does not enable startup at boot.

## Updates

Run **on Ubuntu**:

```sh
sudo systemctl stop wsjtx-dashboard
cd ~/wsjtx-dashboard
git pull --ff-only
./install.sh
sudo systemctl start wsjtx-dashboard
```

Use the same installation command every time. Do not recopy `config.example.toml` over your configuration. Stop if Git reports local changes/divergence; inspect rather than reset/delete files. Stop if installation fails; never start a partially updated deployment. `./install.sh` does not change branches, download releases, or discard configuration.

## Logs and troubleshooting

Run **on Ubuntu**:

```sh
sudo journalctl -u wsjtx-dashboard -n 100 --no-pager
sudo journalctl -u wsjtx-dashboard -f
```

Ctrl+C exits the log viewer only. Config errors, missing frontend, HTTP bind errors and Uvicorn startup/shutdown appear in the journal. A multicast join/receive failure appears in the dashboard/API receiver status; inspect `http://10.176.1.6:8000/api/snapshot` using the configured address. `listening` means the socket joined, not proof of received packets.

If the installer reports a running dashboard, stop it with `sudo systemctl stop wsjtx-dashboard` before retrying. If the configured port is occupied by another process, identify it; never stop WaveLogGate or another station service to free the port. If prerequisites/downloads/build fail, the failing command is printed by the exception and its own output is retained. Fix the issue and rerun `./install.sh`. A configuration edit does not require copying or modifying service files.

The deployment is tested offline on macOS as far as practical. Actual Ubuntu package installation, local Linux Node execution, systemd unit verification/privileges/start-stop-restart, multicast under the service sandbox, LAN HTTP access, and remaining live acceptance checks require Ubuntu verification. [Current checkpoint](current-checkpoint.md) separates observed radio reception from pending acceptance.
