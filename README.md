# WSJT-X Dashboard

A browser dashboard for live WSJT-X station selections across your radios. **Radio selection data is real; operator profiles and QSO history are still clearly labeled sample data.** No Wavelog/QRZ integration, QSO submissions or radio commands. WaveLogGate remains untouched.

## Install on Ubuntu

Ubuntu **24.04+**, Python **3.12+**, Git and a user with sudo access are required. Run these commands **on Ubuntu as your ordinary user**, not as root. The repository is private; HTTPS cloning requires a personal access token at the password prompt ([authentication steps](docs/install-ubuntu.md#github-authentication-for-https-cloning)). [Complete installation details](docs/install-ubuntu.md).

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard
cd ~/wsjtx-dashboard
cp config.example.toml config.toml
nano config.toml
./install.sh
sudo systemctl start wsjtx-dashboard
```

The example is populated for our station: HTTP **10.176.1.6:8000**, multicast **239.255.0.73:2238**, Ubuntu receiver interface **10.176.1.6**. Edit these in `config.toml` for the receiving host; no application-source edits are needed. The installer preserves this file on updates, creates `.venv`, checks/installs prerequisites, builds the frontend on Ubuntu with Node 24 LTS, and installs the service. It requests sudo for missing Ubuntu packages and service installation, and does not start it automatically. Ubuntu needs no Codex/ChatGPT app or GitHub release assets.

**On your Mac browser**, open **http://10.176.1.6:8000/?mode=live** after starting the service. Use the configured address/port if changed. Access stays on the trusted LAN; no router changes or public exposure. The first Status per rig is a baseline; a later changed DX callsign focuses the station.

## Operate

Run **on Ubuntu**:

```sh
sudo systemctl start wsjtx-dashboard
sudo systemctl stop wsjtx-dashboard
sudo systemctl restart wsjtx-dashboard
sudo systemctl status wsjtx-dashboard
```

Edit `~/wsjtx-dashboard/config.toml` and restart to apply configuration changes. Focus/history is memory-only and resets on service restart.

## Update

Run **on Ubuntu**, in the same checkout:

```sh
sudo systemctl stop wsjtx-dashboard
cd ~/wsjtx-dashboard
git pull --ff-only
./install.sh
sudo systemctl start wsjtx-dashboard
```

Stop if any command fails; fix the reported error before continuing. Do not recopy the example configuration during updates. The installer rebuilds the frontend and updates dependencies/service; it does not fetch tags, switch branches, or reset local files.

## View logs

Run **on Ubuntu**:

```sh
sudo journalctl -u wsjtx-dashboard -n 100 --no-pager
sudo journalctl -u wsjtx-dashboard -f
```

Ctrl+C exits the log viewer; it does not stop the service. [Troubleshooting and prerequisites](docs/install-ubuntu.md) cover failed installs, occupied ports, and existing installations.

## Development and validation

[Mac development](docs/development.md) · [Separate offline demo](docs/demo.md) · [Milestone 2 architecture and acceptance](docs/milestone-2.md) · [Current checkpoint](docs/current-checkpoint.md) · [Historical validation](docs/validation-history.md)
