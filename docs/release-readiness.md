# v0.9 release readiness

[Documentation](README.md) · [Draft release notes](releases/v0.9.0-beta.1.md) · [Changelog](../CHANGELOG.md)

**Candidate:** `v0.9.0-beta.1`, proposed October 27, 2026. The operator authorized merging the preparation into main for testing; [PR #11](https://github.com/kf6ufo/wsjtx-dashboard/pull/11) merged at `a4d7ceb`. This is not a published release. Tagging, GitHub release publication and repository visibility changes still require separate approval.

## What the evidence supports

| Area | Actual status |
| --- | --- |
| Multi-instance focus, async lookups, SSE/reconnect, shared history | Implemented; automated and actual macOS station evidence |
| Station layout, Details, worked status, map, diagnostics/settings | Implemented; browser/desktop/mobile checks; basemap requires internet/WebGL |
| QRZ and pyhamtools | Implemented; actual QRZ/country-file evidence and offline fixture coverage; returned data depends on provider/account |
| Wavelog history and station matching | Actual API v2 reads and authorized location matches; exact external-resolution evidence |
| Direct Wavelog logging | Implemented and used in the operator configuration; six retained successful Dashboard receipts matched to exports during the field audit. This is not full isolated write/outage or every-field acceptance |
| ADIF history/logging and durable delivery | Implemented; extensive parser, append/recovery, independent destination and dedupe tests |
| UDP forwarding | Actual raw reception from two instances confirmed in GridTracker2 2.261019.5.991; isolated enriched receiver tests; not blanket compatibility with other versions/apps |
| macOS | Actual macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0 and Chrome evidence |
| Ubuntu | Operator-reported successful testing; exact version/architecture and detailed test matrix not recorded |
| Windows / Docker | No actual Windows or Docker acceptance. POSIX file locking limits native Windows assumptions |

## Before public publication

- [x] Operator guides describe implementation rather than milestone plans; Wavelog is optional.
- [x] Source has an MIT license; no new image license dependency is introduced by the original demo illustration.
- [x] Proposed package metadata version is consistent; Node range reflects installer behavior.
- [x] New examples/screenshot data are fictional; no credentials or live logbooks are deliberately included.
- [x] Complete fresh install/repeat-install, tests, screenshot and local document-link checks; exact results are below.
- [ ] Review the final diff and screenshot with the maintainer, then approve the release candidate commit/version.
- [x] Perform the reachable-history, GitHub text/assets and targeted security review at `8d315c3`; [findings and evidence](security-history-review.md) are recorded. No confirmed production credential exposure was found.
- [x] Resolve hostname/initial-file-permission findings with narrow trusted hosts, 0600 configuration/SQLite files and 0700 private directories; [hardening evidence](security-history-review.md#hardening-validation--october-27) records 199 backend tests, 35 frontend tests, 13 browser workflows, LAN-address/SSE checks and repeat-install preservation.
- [x] Record the operator's October 27 acceptance of publishing historical callsigns, private LAN addresses, machine paths and QSO-related development examples, retaining Git history.
- [x] Record the operator's explicit confirmation to keep existing Git attribution, including the personal email. Preserve history and attribution; this does not authorize visibility changes, release publication or credential disclosure.
- [ ] Confirm third-party dependency/data/attribution obligations for distribution. Basemap attribution must remain visible; source licensing does not grant rights to QRZ photographs or external datasets.
- [ ] Complete isolated Wavelog 3.2.3 write/retry/outage acceptance and ordinary post-field-audit contact/export verification, or explicitly retain experimental logging status in the published beta notes. Exporter omissions are not proof of failed submission.
- [x] Record the operator's successful Ubuntu testing report. Do not infer a specific Ubuntu version/architecture or verified systemd, Windows, Docker or MacLoggerDX support.
- [ ] Only after review: choose public visibility, create the approved tag and publish a GitHub **pre-release**. No binaries/container images are currently validated release artifacts.

Public release is intentionally **not yet ready for an unqualified production-logging claim**. The historical disclosure decisions are accepted. A limited beta may be published after separate approval with the remaining distribution, platform and integration limitations plainly stated; repository visibility and release publication have not been authorized by these confirmations.

## Known limits

Same-call repeat clicks may not produce Status changes. Current-band counts include all modes. Inline biography, reverse radio control, bulk backfill and ADIF/Wavelog synchronization are absent. No authentication/public hosting is provided. UDP has no acknowledgement, and uncertain remote writes reconcile rather than blindly retry. Wavelog 3.2.3 can normalize/omit values in exports; optional-field live acceptance is still pending. GridTracker receiver tests found Unicode-name/fractional-power limitations in the tested receiver path; other receiving applications need their own tests.

Historical field-coverage validation at application `b2338e6` passed **179 backend tests**, **35 frontend tests**, type checking/build and **five affected browser workflows**. Those results precede this documentation branch. A Starlette/httpx deprecation and a separately loaded map-renderer size advisory remain.

## Fresh candidate validation

On October 27, the documented installer was run from a **clean clone at `69e48aa`**, with a newly created virtual environment and `npm ci`, on actual macOS 26.6.1 arm64 / Python 3.13.1 / Node 24.21.0 / Chrome. Dependencies used the normal package caches where available; this is a clean installation, not an empty-cache download benchmark. Installation, type checking and production build passed. The built server served HTTP 200 on an isolated loopback port with receiver/providers/logging/forwarding disabled, and shut down gracefully. The live station on port 8787 was untouched.

A real repeat `./install.sh` preserved byte-identical configuration, a synthetic ADIF file and all four SQLite databases, including one pending delivery. Example TOML parsed successfully; the template's parsed defaults equal main's, package/lock versions agree, and dependency versions are unchanged.

| Check | Result |
| --- | --- |
| Backend suite, including installed shutdown | **179 passed** |
| Frontend unit suite | **35 passed** |
| Type checking / production build | Passed |
| Isolated browser workflows | **13 passed**: 3 demo, 1 foundation, 1 receiver, 3 enrichment, 1 Wavelog, 1 ADIF, 2 Steps 5/7, 1 mapping |
| Local Markdown file/image/anchor links | **172 checked across 37 Markdown files; zero errors** |
| Sanitized screenshot | Captured at 1560 × 1492 from actual built UI with fictional API/photo fixtures; visually inspected, basemap attribution retained |
| Public-facing example scan | No operator paths, station-specific LAN addresses, operator callsigns or credential/key patterns found in the new guides/capture fixture; this is not a full Git-history secret audit |

The initial demo browser test counted hidden Diagnostics rows as QSOs after opening Settings. Its row/header assertions were narrowed to the contact scroller; the full browser set then passed. This is a test-only correction with no UI change. Backend/unit/build results apply to the same application code and metadata; the selector correction was synchronized into the clean validation checkout before the passing browser run. Later screenshot/report additions do not change the application.

Warnings: existing Starlette/httpx adapter deprecation, separately loaded map-renderer size advisory, npm `whatwg-encoding` deprecation and an optional `fsevents` install-script advisory. `npm ci` reported zero known vulnerabilities in that run; this is not a comprehensive security audit. Actual Ubuntu/Windows/Docker execution and external write acceptance remain outside these results. The live station checkout, settings, QSO files and queues were not updated or used as a write-test target.

## Temporary Node installer

Validated installer source **`a4de9f4`**, approved for main testing through [PR #13](https://github.com/kf6ufo/wsjtx-dashboard/pull/13), removes the need to install Node separately on macOS/Ubuntu x64 or ARM64. It reuses compatible Node/npm, or verifies a pinned official Node 24.21.0 archive before execution, safely extracts it, scopes PATH to child processes and removes the private temporary toolchain afterward. No global packages or shell profiles are changed; Python/Git remain prerequisites. Ubuntu execution and macOS x64 execution remain unverified; their target selection/checksums have offline coverage and all four platform hashes were checked against the official release manifest.

On actual macOS arm64, a fresh install and real repeat install both passed with **neither Node nor npm on PATH**. Temporary tools were removed afterward; repeat installation preserved configuration, synthetic ADIF and all four SQLite stores byte-for-byte, including modes, ownership and pending delivery/receipt data. **215 backend tests**, **35 frontend tests**, type checking and production build passed. Backend tests cover existing-tool reuse, incompatible/missing tools, four platform mappings, checksum failures before execution, archive traversal rejection and cleanup on failure. The operating installation was untouched. This installer update does not change application behavior or the existing beta platform/integration limitations.

## Safe updater validation

Updater source **`dab0871`** adds `./update.sh` without changing the existing installer or runtime code. **235 backend tests passed**, including **20 isolated real-Git updater cases** covering clean/already-current updates, staged/unstaged edits, wrong branches/detached HEAD, missing/wrong origins, Git/installer failures, ahead/diverged history, ignored/untracked collisions, edits arriving during fetch and self-update safety. `sh -n update.sh` passed.

A separate actual macOS end-to-end run used a private local Git transport and the real installer: it printed the correct previous/updated hashes, fast-forwarded successfully, provisioned/removed temporary Node and built the frontend with neither Node nor npm on the parent PATH. Configuration, synthetic ADIF, all four SQLite stores and pending delivery/receipt state retained identical bytes, modes and ownership. No operating station or production QSO service was changed or restarted. At that validation run Ubuntu execution was unverified; the operator subsequently reports successful Ubuntu testing. Future systemd execution remains unverified; [operator update instructions](installation.md#updates-and-backups) explicitly keep stop/start and backup actions outside the script.

## Scope of preparation changes

README and user guides, changelog/release draft, readiness checklist, a reproducible sanitized screenshot and a local link checker. Configuration-template comments are clarified without changing defaults. Package version is proposed as `0.9.0-beta.1`; its Node engine range changes from `>=24.15.0` to `>=24.15.0 <25` to match the existing installer. Demo browser assertions now count only contact-table rows/headers, excluding hidden Diagnostics tables. No dependency versions, UI behavior, logging architecture or production configuration are changed.
