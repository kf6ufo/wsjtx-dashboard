# Current checkpoint — Step 2 preview

**October 23, 2026. Steps 0 and 1 are reviewed on `main`.** The operator requested Step 2 with the full available pyhamtools/callbook fields, configurable provider options and QRZ XML setup. Implementation is on **`feature/step-2-enrichment`**, awaiting operator review. Step 3 has not begun.

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

Clean installation at a feature commit and the Step 1 → Step 2 live workspace upgrade are the remaining deployment checks for this preview. No live QRZ or Club Log credentials were supplied. Their account/subscription access, QRZ images and full returned records remain unverified. Ubuntu execution remains untested, including dependencies/build, upgrades, multicast and browser/tunnel access.

## Existing station evidence and review server

Step 1 previously verified actual multicast **239.255.0.73:2238**, Mac receiving interface **10.176.1.200**, separate network IDs **WSJT-X - IC9100** and **WSJT-X - IC7300** from **10.176.1.5**, and operator-confirmed selections with shared newest-first history and Decode stability. These are prior Step 1 observations, not a new physical-click test of Step 2. QRPLabsQDX has not been observed in this session.

The existing Step 1 review server is now at **http://127.0.0.1:8787/** in `/private/tmp/wsjtx-step1-native`. The former Step 0 server is stopped; port 8789 is no longer the review address. Only this dashboard will be replaced for Step 2 review, after installation validation and a configuration/state backup. The operator's VS Code source checkout remains unchanged on `main`.

Use the [macOS installation guide](install-macos.md) or [Ubuntu directions](install-ubuntu.md), choosing the feature branch for this preview. Back up configuration and `data/` with the server stopped. Credentials, live workspace databases, dependencies and build outputs remain excluded from Git. Do not proceed to Wavelog integration until Step 2 is reviewed.
