# Changelog

## [Unreleased] — proposed v0.9.0-beta.1

First proposed public beta; **not tagged or published**. The application was previously developed through reviewed milestones rather than public releases.

### Included application

- Live multi-instance WSJT-X focus, shared Focus History and bounded Diagnostics.
- Responsive Station interface with photos, populated sortable Details, map, contact history and light/dark themes.
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
