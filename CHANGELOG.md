# Changelog

## [Unreleased] — v0.9.0-rc.1 (RC1)

November 5, 2026: operator-approved Release Candidate 1 for testing from `main`. No release tag or GitHub release has been published.

### Added

- November 6 testing update: executable `run.sh` starts the installed server without virtual-environment activation and forwards `--config` arguments. Installer/updater output and current startup instructions point to the launcher.
- Refreshed standard/full-screen documentation imagery and a reception-map close-up show nine fictional PSKReporter dots, including the focus station’s inner dot, with retained map attribution.

- November 6 testing update: separate UDP and PSKReporter MQTT Diagnostics tabs, broker acknowledgement and message/filter counters, bounded report/rejection/connection activity, and scoped pause/clear controls. Version remains `0.9.0-rc.1`.

- Optional PSKReporter MQTT reception overlay: small amber receiver dots for your transmitted callsign on the focus band, including an inner dot when the focused station reports hearing you.
- Per-browser 5/15/30/60-minute windows, a saved 15-minute default, automatic per-rig identity and an explicit transmitting-callsign override.
- One shared TLS MQTT connection, bounded one-hour in-memory reception cache, reconnect/resubscribe and expiry during outages; no XML polling or focus-triggered upstream requests.
- Offline visual-preview script, focused collector/map tests and operator documentation. Map updates preserve pan/zoom and do not change focus/history or radio operation.

### Changed

- Package and lockfile versions advance from `0.9.0-beta.1` to `0.9.0-rc.1`; current operator documentation identifies RC1.

### Validation and limits

- Offline automated tests and desktop/mobile browser review passed. Actual MQTT connection/subscription succeeded, but no reports arrived in the brief check; ordinary live reception-data acceptance remains pending.
- Existing installation, logging, platform and external-integration limits remain in the [readiness checklist](docs/release-readiness.md). The operating installation is unchanged by publication.

See [RC1 notes](docs/releases/v0.9.0-rc.1.md) and [reception map setup](docs/pskreporter.md).

## Historical beta preparation — proposed v0.9.0-beta.1

First proposed public beta; **not tagged or published**. The application was previously developed through reviewed milestones rather than public releases.

### Included application

- Live multi-instance WSJT-X focus, shared Focus History and bounded Diagnostics.
- Responsive Station interface with photos, populated sortable Details, map, contact history and light/dark themes.
- Per-window Full screen/Exit full screen controls, compact navigation/status toolbar and reduced margins for dedicated station monitors.
- Source-aware callsign/current-band worked indicators that preserve pending/incomplete/unknown distinctions.
- Optional pyhamtools/QRZ enrichment and authorized Wavelog API v2 history.
- Independent ADIF history/logging and optional direct Wavelog submission.
- Automatic authorized station matching, explicit overrides, persistent per-destination queues, reconciliation and duplicate receipts.
- Reliable missing-only QSO fields, distance in both destinations, QSL routing, destination support rules and a read-only export audit.
- Optional one-way UDP forwarding with original/enriched formats and independent destination state.

### Release preparation

- Guarded `update.sh` for clean `main` checkouts: expected origin validation, fast-forward-only updates, no autostash/ignored-file overwrite, and explicit installer/service guidance.
- Automatic checksum-pinned temporary Node build tools when compatible Node/npm is unavailable; no global Node installation required for supported macOS/Ubuntu architectures.
- Narrow HTTP trusted-host validation for localhost, loopback and the configured LAN IP, retaining existing Origin restrictions.
- Owner-only configuration/SQLite files and private state directories, with repeat-install/restart preservation tests and no ADIF or ownership changes.

- Rewritten operator-focused README and navigable installation, configuration, operating, logging, troubleshooting and architecture guides.
- Sanitized Station screenshot using fictional demonstration records.
- Draft release notes and an explicit platform/integration readiness checklist.
- Proposed package metadata version `0.9.0-beta.1`; Node engine range aligned with the installer's actual 24.x requirement. No dependency upgrades, UI redesign or logging architecture changes.
- Corrected demo browser test selectors to exclude hidden Diagnostics rows from contact counts; the complete isolated browser suite passes.

### Known limitations

- Actual Ubuntu execution, Windows, Docker, MacLoggerDX integration and complete isolated Wavelog write/outage acceptance remain unverified.
- Newly added optional-field live export acceptance is pending; Wavelog 3.2.3 itself omits some accepted fields from exports.
- No inline biography retrieval, reverse radio controls, historical bulk backfill or ADIF/Wavelog synchronization.
- UDP is unacknowledged; remote uncertain outcomes reconcile instead of blindly resubmitting.

See [release readiness](docs/release-readiness.md) and [draft release notes](docs/releases/v0.9.0-beta.1.md) for evidence and remaining gates.
