# WSJT-X Dashboard

A self-hosted companion for the operating desk. **Current implementation — Step 3:** a responsive Station / Diagnostics / Settings dashboard, clearly labeled fictional profiles and contacts, shared server selections, live browser updates, saved workspace preferences/history, and configurable receive-only WSJT-X UDP with packet diagnostics, configurable pyhamtools enrichment, optional QRZ XML callbook details, and read-only Wavelog QSO history.

**UDP reception, enrichment and Wavelog history are opt-in. Configure credentials locally in Settings.** Production radios, WaveLogGate and station services remain unchanged. There are no QSO submissions, radio commands or forwarding. [Approved requirements](WSJTX-REBUILD-HANDOFF.md) replace the old milestone and Ubuntu-only assumptions; [Steps 4–7 remain the roadmap](docs/roadmap.md).

## Install and run

The reviewed Step 3 implementation is installed from **`main`**. Previous attempts remain available in Git history; obsolete documentation and the superseded test server are removed from the current tree.

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

Before first enabling reception, sample profiles/contacts load independently from offline fixtures; empty and failed sample histories remain distinct. VK3DEMO has no contacts, PY2DEMO simulates a failed lookup, and ZS6DEMO has no profile. These are illustrative callsigns with fictional identity/contact details. Actual radio selections use configured enrichment providers, never fixture profiles or contacts. QSO history remains explicitly unavailable until Wavelog is connected.

[Operation, updates, backups, migration, rollback and troubleshooting](docs/install-macos.md#operation-and-updates) · [Development/checks](docs/development.md) · [Current tested/untested checkpoint](docs/current-checkpoint.md)

## Try Step 2

Open **Settings → pyhamtools enrichment**. Enable Country-files.com for account-free DXCC/country/zone details. Optionally add QRZ XML and enter your QRZ username/password locally. Save, then test the saved provider settings. All returned fields, provenance, freshness, calculated band/distance/bearings and partial provider failures are visible in the station view. [Step 2 setup, source options and review guide](docs/step-2.md).

## Try Step 3

Open **Settings → Wavelog QSO history**. Save the application URL and a dedicated Wavelog **API v2 token** with `qso:read` and `station:read`, then test the saved connection. An ending `/api` is accepted and removed automatically. Leave scope at **All authorized station locations** to include former and current station callsigns. Optional `confirmation:read` supplies QSL details; `logbook:read` enables logbook selection where supported. [Step 3 setup and review guide](docs/step-3.md).

Radio selections and Focus History browsing load complete paginated contacts independently from QRZ. Failed or partial history never claims a new callsign/band. Contacts are cached only in memory. This release does not submit QSOs or replace WaveLogGate. See the checkpoint for verified and still untested behavior.

The worked-before summary and current-band status appear directly beneath the focused station details, ahead of Station enrichment.

## Step 4 preview

The initial station-details preview is on **`feature/step-4-station-details`**. It prioritizes populated fields in a scrollable panel, keeps worked-before/current-band status first, and adds clearer contact/QSL/license information and scrollable QSO details. The map is deferred. [Preview installation and operator review](docs/step-4.md). `main` remains the reviewed Step 3 release.
