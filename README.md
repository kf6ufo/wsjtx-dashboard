# WSJT-X Dashboard

A self-hosted companion for the operating desk. **Reviewed baseline — Steps 0–5 and 7:** compact Station / Diagnostics / Settings navigation, photo-first station identity, populated scrollable details, worked-before/current-band indicators, a zoomable station map and complete contact history. Shared Focus History, live browser updates, saved preferences, multiple WSJT-X receiver identities, pyhamtools and QRZ enrichment are included. Fictional sample data is labeled and kept separate from actual radio selections.

**UDP reception, enrichment and Wavelog history are opt-in. Configure credentials locally in Settings.** Optional independent ADIF history, Wavelog fallback and durable enriched-QSO delivery infrastructure are also included. **Dashboard logging and Wavelog delivery default off; upgrades preserve existing operator settings.** WaveLogGate is not modified by installation or upgrades. Isolated real Wavelog write acceptance and a managed sole-uploader cutover remain unverified; radio commands remain excluded. Optional one-way UDP distribution and completed-contact observation/read reconciliation are included. [Approved requirements](WSJTX-REBUILD-HANDOFF.md) · [Remaining work and acceptance boundaries](docs/roadmap.md).

## Install and run

Install the reviewed baseline from **`main`**. Following the Steps 5/7 publication in PR #6, the operator approved the compact worked-status indicators, automatic Wavelog station mapping and distance/QSL routing corrections in [PRs #7–#9](https://github.com/kf6ufo/wsjtx-dashboard/pull/9), merged October 26, 2026. New submissions include calculated distance when valid grids are available and a missing `QSL_VIA` from QRZ manager information; existing values win. Earlier PRs #3/#4 supplied Step 4 and optional QSO infrastructure. Feature history is preserved. [Merge and runtime verification](docs/current-checkpoint.md).

[PR #10](https://github.com/kf6ufo/wsjtx-dashboard/pull/10) publishes the completed-QSO field coverage audit and corrections. Reliable missing contact data is included where supported, distance reaches both ADIF and Wavelog, and original WSJT-X values win. Unknown profile metadata and unobserved confirmations are omitted. Queue handling and duplicate protection are unchanged. The [field inventory and read-only export audit](docs/qso-field-audit.md) explain every mapping, omitted field and Wavelog 3.2.3 export limitation; live acceptance of newly added optional fields remains pending an ordinary contact/export check.

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

Open **Settings → Radio receiver**. Set the receiving computer's IPv4 interface, primary UDP port and multicast group, then enable and save. Changes apply immediately; only the receiver restarts, with a fresh Status baseline per instance. No WSJT-X configuration needs to change when joining an already configured multicast group. [Step 1 guide](docs/step-1.md).

**Diagnostics** shows sources, network IDs, last seen, packet/error counts and bounded packet details. Heard-instance and radio-activity dropdowns, clear packet badges and short signal/status previews make traffic easier to inspect. Pause/clear affects the diagnostic display only. A changed valid DX Call after the first Status updates two browsers without refresh; ordinary decodes never steal focus. History browsing preserves order/time/rig. Once activated, the radio workspace/history remains visible even if reception is disabled. The original sample workspace is retained separately; an isolated frontend fixture demo is at `/?mode=demo`.

Before first enabling reception, sample profiles/contacts load independently from offline fixtures; empty and failed sample histories remain distinct. VK3DEMO has no contacts, PY2DEMO simulates a failed lookup, and ZS6DEMO has no profile. These are illustrative callsigns with fictional identity/contact details. Actual radio selections use configured enrichment providers, never fixture profiles or contacts. Actual QSO history requires an enabled Wavelog connection or configured ADIF source; unavailable/incomplete history never establishes a new callsign.

[Operation, updates, backups, migration, rollback and troubleshooting](docs/install-macos.md#operation-and-updates) · [Development/checks](docs/development.md) · [Current tested/untested checkpoint](docs/current-checkpoint.md)

## Try Step 2

Open **Settings → Callbook & enrichment**. Enable Country-files.com for account-free DXCC/country/zone details. Optionally add QRZ XML and enter your QRZ username/password locally. Save, then test the saved provider settings. All returned fields, provenance, freshness, calculated band/distance/bearings and partial provider failures are visible in the station view. [Step 2 setup, source options and review guide](docs/step-2.md).

## Try Step 3

Open **Settings → Wavelog connection**. Save the application URL and a dedicated Wavelog **API v2 token** with `qso:read` and `station:read`, then test the saved connection. An ending `/api` is accepted and removed automatically. Leave scope at **All authorized station locations** to include former and current station callsigns. Optional `confirmation:read` supplies QSL details; `logbook:read` enables logbook selection where supported. [Step 3 setup and review guide](docs/step-3.md).

Radio selections and Focus History browsing load complete paginated contacts independently from QRZ. Failed or partial history never claims a new callsign/band. Read results are cached only in memory. Enabling history does not enable QSO submissions; existing logging settings are preserved. WaveLogGate is unchanged. See the checkpoint for verified and still untested behavior.

The worked-before summary and current-band status appear directly below identity in the compact left tile, beside the scrollable Details column. Station wording is independent of the selected history provider; its actual source and scope remain visible.

## Optional history and logging infrastructure

Included on **`main`**: independent ADIF history/logging, automatic Wavelog preference/fallback, strict incomplete-history states, per-rig identities, missing-only enrichment and a persistent per-destination outbox. Existing installations retain their configuration. Keep `logging_enabled = false` and `log_to_wavelog = false` until isolated write acceptance and an explicitly approved sole-uploader cutover. No isolated Wavelog test instance is currently available; production is not a write-test target. [Configuration, reliability, backups and validation](docs/qso-services.md) · [Full requested scope](docs/qso-architecture-request.md).

## Station display

The reviewed Step 4 layout is on **`main`**. It uses a compact top navigation bar and a centered photo-first station tile, prioritizes populated fields in a scrollable panel, and keeps worked-before/current-band status immediately below identity. The **Confirm via** display combines the former LoTW/QRZ entries into one compact indicator; the QRZ profile link remains with station basics. Scrollable QSO details remain below. A Leaflet station map using OpenStreetMap data sits beneath the profile/details columns, ahead of contacts, with buttons, drag/pinch, keyboard and Command/Ctrl-scroll zoom. Settings separates each save scope into tabs; Details sorts by Field (default) or Value in either direction. The map uses OpenFreeMap vector tiles with English-first labels and Latin-script fallback; the basemap requires WebGL and internet access, without an API key. [Display behavior and acceptance caveats](docs/step-4.md). Inline biography retrieval remains deferred; Ubuntu execution remains untested.

## Completed contacts, Focus History and UDP distribution

Main includes independent completed-contact observation/read reconciliation, configurable Focus History retention/clearing and optional one-way UDP destinations. These update the display without authorizing permanent QSO logging. Settings → Focus History controls the 50/100/200/500-entry limit and manual/7/30-day retention. Settings → UDP forwarding controls each destination independently; new installations have no enabled destinations. The operator confirmed real forwarding from both rigs into GridTracker2 2.261019.5.991 on the iMac. Fresh installations default to logging off, upgrades preserve operator settings, and WaveLogGate is unchanged. [Behavior and GridTracker2 setup](docs/steps-5-and-7.md) · [Actual validation, receiver limits and remaining work](docs/current-checkpoint.md).
