# WSJT-X Dashboard

A self-hosted companion for the operating desk. **Current implementation — Step 1:** a responsive Station / Diagnostics / Settings dashboard, clearly labeled fictional profiles and contacts, shared server selections, live browser updates, saved workspace preferences/history, and configurable receive-only WSJT-X UDP with packet diagnostics.

**UDP reception is opt-in. QRZ and Wavelog are not connected.** Production radios, WaveLogGate and station services remain unchanged. There are no QSO submissions, radio commands or forwarding. [Approved requirements](WSJTX-REBUILD-HANDOFF.md) replace the old milestone and Ubuntu-only assumptions; [Steps 2–7 remain the roadmap](docs/roadmap.md).

## Install and run

The reviewed implementation is installed from **`main`**. Previous attempts remain available in Git history; obsolete documentation and the superseded test server are removed from the current tree.

Use a **separate checkout**, preserving any existing installation. Requires Git, Python **3.12–3.14**, and Node **24 LTS, 24.15+** with npm. Dependencies build on the target host. No editor, Codex, Docker, release asset or privileged installer is required.

[Complete macOS installation](docs/install-macos.md) · [Ubuntu installation](docs/install-ubuntu.md)

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git ~/wsjtx-dashboard
cd ~/wsjtx-dashboard
./install.sh
.venv/bin/python -m backend.server
```

Open **http://127.0.0.1:8787/**. Ctrl+C stops; rerun the server command to restart. `./install.sh` creates `config.toml` only if absent, builds the frontend, and preserves settings/data on repeated installs. For a specific reviewed revision, see the [checkpoint](docs/current-checkpoint.md). This private repository needs authorized HTTPS token/credential-manager or SSH access; never put a token into the clone URL.

## Try Step 1

Open **Settings → WSJT-X receiver**. Set the receiving computer's IPv4 interface, primary UDP port and multicast group, then enable and save. Changes apply immediately; only the receiver restarts, with a fresh Status baseline per instance. No WSJT-X configuration needs to change when joining an already configured multicast group. [Step 1 guide](docs/step-1.md).

**Diagnostics** shows sources, network IDs, last seen, packet/error counts and bounded packet details. Pause/clear affects the diagnostic display only. A changed valid DX Call after the first Status updates two browsers without refresh; ordinary decodes never steal focus. History browsing preserves order/time/rig. Once activated, the radio workspace/history remains visible even if reception is disabled. The original sample workspace is retained separately; an isolated frontend fixture demo is at `/?mode=demo`.

Before first enabling reception, sample profiles/contacts load independently from offline fixtures; empty and failed sample histories remain distinct. VK3DEMO has no contacts, PY2DEMO simulates a failed lookup, and ZS6DEMO has no profile. These are illustrative callsigns with fictional identity/contact details. In the radio workspace every profile/QSO lookup stays explicitly not connected, even for a callsign matching a fixture.

[Operation, updates, backups, migration, rollback and troubleshooting](docs/install-macos.md#operation-and-updates) · [Development/checks](docs/development.md) · [Current tested/untested checkpoint](docs/current-checkpoint.md)

Steps 0 and 1 are reviewed. Step 2 requires a separate request.
