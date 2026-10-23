# WSJT-X Dashboard

A self-hosted companion for the operating desk. **Rebuild Step 0 is ready for review:** a responsive Station / Diagnostics / Settings dashboard, clearly labeled fictional profiles and contacts, shared server selections, live browser updates, and saved workspace preferences/history.

**No WSJT-X, QRZ or Wavelog integration is connected in Step 0.** Production radios, WaveLogGate and station services remain unchanged. The installed server refuses UDP enablement. [Approved requirements](WSJTX-REBUILD-HANDOFF.md) replace the old milestone and Ubuntu-only assumptions; [Steps 1–7 remain the roadmap](docs/roadmap.md).

## Install and run

Use a **separate checkout**, preserving any existing installation. Requires Git, Python **3.12–3.14**, and Node **24 LTS, 24.15+** with npm. Dependencies build on the target host. No editor, Codex, Docker, release asset or privileged installer is required.

[Complete macOS installation](docs/install-macos.md) · [Ubuntu installation](docs/install-ubuntu.md)

```sh
git clone --branch rebuild/step-0 https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard-rebuild
cd ~/wsjtx-dashboard-rebuild
./install.sh
.venv/bin/python -m backend.server
```

Open **http://127.0.0.1:8787/**. Ctrl+C stops; rerun the server command to restart. `./install.sh` creates `config.toml` only if absent, builds the frontend, and preserves settings/data on repeated installs. For a specific reviewed revision, see the [checkpoint](docs/current-checkpoint.md). This private repository needs authorized HTTPS token/credential-manager or SSH access; never put a token into the clone URL.

## Review Step 0

Open two browser windows at the same URL. Use **Demo tools → Simulate a station selection**: both callsigns and history update without refresh. Click an older history card: both windows browse it while order and radio provenance stay fixed. Disconnect one browser, change the selection in the other, reconnect: it catches up automatically. Settings saves real shared preferences; the header Theme/Station Desk buttons are local previews. Diagnostics identifies future integrations as not implemented/connected.

Profiles/contacts load independently from offline fixtures; empty and failed sample histories remain distinct. VK3DEMO has no contacts, PY2DEMO simulates a failed lookup, and ZS6DEMO has no profile. These are illustrative callsigns with fictional identity/contact details.

[Operation, updates, backups, migration, rollback and troubleshooting](docs/install-macos.md#operation-and-updates) · [Development/checks](docs/development.md) · [Current tested/untested checkpoint](docs/current-checkpoint.md)

Old notes are retained as historical references. Stop at Step 0 review before enabling Step 1.
