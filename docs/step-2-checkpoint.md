# Current checkpoint — Step 2

**October 23, 2026. Step 2 is the reviewed publication scope for `main`.** The operator requested review and publication of the Work Session implementation from PR #1 (`feature/step-2-enrichment`). Step 3 Wavelog work exists separately in PR #2 and is excluded from this release.

The live-station observations below were recorded by the earlier Work Session. They are retained as prior evidence, not claimed as repeated during this code review.

## Publication code review

Reviewed Step 2 PR #1 at `3fdd97cd4f2b722d638407c3eb1bf3f2049c4eca` against Step 1 `9f7729224a1611776baa0499d7583654ebbae11b`. No blocking code findings. Review covered background lookup ordering, shared focus/history, cache bounds, provider failure states, reported versus callbook grids, credential redaction/storage, configuration compatibility and photo persistence. Documentation corrections promote the installation path to `main`, remove outdated QRZ verification statements, clarify LAN access to saved-provider operations and provider-timeout shutdown behavior, and keep Step 3 outside this release.

Fresh macOS validation in `/private/tmp/wsjtx-step2-review-clean` at that Step 2 commit:

- Documented native installer and production build passed with Python 3.13.1 / Node 24.21.0.
- **57 Python tests**, **16 frontend tests**, and **all seven offline browser workflows** passed using installed Chrome. The Python suite retains the existing Starlette/httpx adapter deprecation warning.
- Synthetic state created by the actual Step 1 code was carried through a repeated native install: custom TOML and SQLite database stayed byte-for-byte unchanged during installation. Step 2 production startup preserved focus, history/browsing provenance and preferences; production HTML/assets, disabled receiver/enrichment defaults, SQLite integrity and shutdown passed on isolated HTTP port 18787.
- Whitespace, local Markdown links, shell syntax and tracked-file hygiene were checked. No runtime databases, credentials, dependencies or build outputs are tracked.

Initial tests using this workspace's existing dependency directories stalled (frontend workers timed out); the independently installed checkout above completed successfully. No new live provider or actual-radio acceptance tests were performed during publication review. Earlier Work Session evidence follows. Ubuntu and live Club Log account access remain unverified. Existing station installations and production services were left running unchanged.

## Current implementation

The existing native server, Vue dashboard, shared SSE snapshots, persistent preferences/history and configurable WSJT-X reception remain in place. Step 2 adds one background enrichment worker, generation guards against stale results, source/freshness/partial-failure presentation, configurable primary and additional QRZ providers, separate provider/result cache policy, grid/distance/bearing/band calculations and an expandable display of every returned field.

Settings supports Country-files.com, Club Log XML/local files, Club Log API and QRZ XML, optional local data files, station-grid override, refresh/cache limits, field priority and opt-in approximate coordinates. QRZ uses username/password and an XML subscription, with private reusable sessions and renewal. Credential fields are write-only; snapshots contain only saved/not-saved indicators. Configuration saves preserve unrelated sections atomically with owner-only permissions. Old Step 0/1 config remains valid without an enrichment section. Saving enrichment adds it; rollback to Step 1 requires the pre-upgrade config backup.

Real radio selections use provider data, never sample identities or contacts. QRZ operator/license/image fields appear when available. Biography HTML retrieval and the final profile layout remain Step 4. Wavelog history, worked-before status, QSO submissions and forwarding remain unavailable. Production WaveLogGate, radio settings and Wavelog are unchanged. [Step 2 setup and review procedure](step-2.md).

## Verified so far on macOS

Host: macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0, installed Chrome.

- **56 Python tests**, **15 frontend tests**, production build, and **six offline browser workflows** passed: enrichment, receiver, shared workspace, and three fixture UI workflows. One existing Starlette/httpx test-adapter deprecation warning remains.
- Actual pyhamtools 0.13.2 parsers tested against country-file and Club Log XML fixtures; Club Log API mapping and QRZ HTTPS/session renewal tested with mocked responses. QRZ coverage includes the upstream large-serial Python 3 parser defect, full newer fields, XML namespaces and missing credentials. Field precedence, grid provenance, cache bounds, config upgrades, secret retention/redaction and unchanged receiver baselines are checked.
- A delayed old lookup cannot replace a newer focused callsign; Decode processing continues while that lookup waits. Browser checks cover two-window enrichment, history browsing without reorder/time/rig changes, partial QRZ failure, changing settings without UDP restart, and disabling enrichment while reception continues. Desktop non-overlap and mobile width checks passed; desktop layout was visually inspected and corrected.
- A real HTTPS Country-files.com download parsed successfully, returning United States/DXCC 291 for KF6UFO, Germany/230 for DL1ABC and Japan/339 for JA2FJP. This verifies actual source download and pyhamtools country enrichment, not any QRZ account access or actual contact distance.

The exact implementation commit **`62b5475b3b8529a15736f0bda2dc02dc4e22b255`** was installed from a separate clean checkout using `./install.sh`. Production assets, Step 2 API, disabled defaults, workspace creation and graceful shutdown passed. The published feature branch was then cloned directly from GitHub into `/private/tmp/wsjtx-step2-github-validation` at that same commit; the documented installer, production assets and API startup/shutdown passed independently.

The actual Step 1 review server was stopped, its config/data backed up, and the unchanged files copied into `/private/tmp/wsjtx-step2-native`. Running the documented installer again preserved the old TOML and complete SQLite database **byte-for-byte**; SQLite integrity passed. Starting Step 2 preserved focus **PY2UTY**, all **five history entries** including prior browsing/selection timestamps and rig/band provenance, plus shared preferences. Enabling account-free enrichment did not reset receiver baselines or change history. Both actual network IDs resumed reception with zero malformed packets and receiver errors. The current station enriched as **Brazil / DXCC 108 / CQ 11 / ITU 15**, with reported DX grid **GG66** and station grid **DM57NS** kept distinct from provider coordinates. The two-browser read-only actual-station workflow passed. A later measured **162 additional real Decodes** left focus/history unchanged (snapshot: 310 packets, 200 Decodes, zero malformed/receiver errors).

A durable copy of the cold pre-upgrade backup is retained in the feature source checkout's ignored `backups/before-step2-20261023/`; `/private/tmp/wsjtx-step2-upgrade-record.json` records the original temporary backup location. Installation verification used the identified implementation commit above; subsequent changes only update documentation and the read-only browser screenshot readiness assertion. At the initial preview no live QRZ or Club Log credentials had been supplied; that initial verification did not establish account/image access. The operator subsequently entered QRZ credentials locally and reported that configuration tests work. The live dashboard now returns a loaded QRZ record with a photo URL. Club Log live account access remains unverified. Ubuntu execution remains untested, including dependencies/build, upgrades, multicast and browser/tunnel access.

## Prior station evidence and temporary review installations

Step 1 previously verified actual multicast **239.255.0.73:2238**, Mac receiving interface **10.176.1.200**, separate network IDs **WSJT-X - IC9100** and **WSJT-X - IC7300** from **10.176.1.5**, and operator-confirmed selections with shared newest-first history and Decode stability. These are prior Step 1 observations, not a new physical-click test of Step 2. QRPLabsQDX has not been observed in this session.

The earlier Step 2 review ran at **http://127.0.0.1:8787/** in `/private/tmp/wsjtx-step2-native`. Temporary review paths, ports and running processes are historical observations; this publication review does not restart or replace them. Later Step 3 development has its own installation outside this release.

Use `main` and the [macOS installation guide](install-macos.md) or [Ubuntu directions](install-ubuntu.md) for a durable installation. Back up configuration and `data/` with the dashboard stopped. Credentials, live workspace databases, dependencies and build outputs remain excluded from Git. Step 3 requires its own review before merging.

## Photo follow-up requested by the operator

The operator requested small profile photos in Focus History and a larger photo in the main station area. The main header now places the photo beside the callsign, QRZ name/location/license details and radio provenance. History uses 58-pixel uncropped thumbnails and a neutral placeholder for missing or failed images. Valid HTTPS photo URLs are saved separately from selection provenance in the existing live workspace payload, retained only for callsigns still in bounded history. No image binaries or QRZ credentials are added to history. Browsing or receiving a delayed photo cannot reorder history or change selection time/rig.

Validation: **57 Python tests**, **16 frontend tests**, the production build and both enrichment browser workflows pass. Coverage includes saved URLs after restart, rejecting unsafe image URLs, recovery after a failed image, late lookup photos without stealing focus, two-browser thumbnails, and desktop/tablet/mobile layout. Existing entries fill in after their next normal lookup; no background sweep of QRZ history is performed. Step 3 is outside this release.

The photo follow-up was installed at **`a5a319a8253deeab4719ec1091493886b59a7387`** through the documented native installer. The operator's QRZ configuration and complete database remained byte-for-byte unchanged through installation. Startup preserved the focused **NA6Y**, all **six history entries** with their browsing/selection provenance, and shared preferences. The actual QRZ record and photo loaded, and the photo URL was confirmed in both the server snapshot and saved workspace payload. The two-window read-only actual-station check passed again. The original configuration/database are backed up in ignored `backups/before-photos-20261023-172156/` in the feature source checkout. Only the dashboard review process was restarted; radio and Wavelog configuration were not changed.
