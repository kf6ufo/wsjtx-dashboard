# v0.9 release readiness

[Documentation](README.md) · [Draft release notes](releases/v0.9.0-beta.1.md) · [Changelog](../CHANGELOG.md)

**Candidate:** `v0.9.0-beta.1`, proposed October 27, 2026. This is preparation for review, not a published release. No tag, GitHub release, visibility change or merge is authorized by this task.

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
| Ubuntu / Windows / Docker | Ubuntu documented target only; no actual Ubuntu, Windows or Docker acceptance. POSIX file locking limits native Windows assumptions |

## Before public publication

- [x] Operator guides describe implementation rather than milestone plans; Wavelog is optional.
- [x] Source has an MIT license; no new image license dependency is introduced by the original demo illustration.
- [x] Proposed package metadata version is consistent; Node range reflects installer behavior.
- [x] New examples/screenshot data are fictional; no credentials or live logbooks are deliberately included.
- [ ] Complete fresh install/repeat-install, tests, screenshot and local document-link checks; record exact results below.
- [ ] Review the final diff and screenshot with the maintainer, then approve the release candidate commit/version.
- [ ] Review **all historical documents and Git history** before making the repository public. Existing development records include station callsigns, LAN addresses and machine-specific paths. This branch does not rewrite history or change visibility.
- [ ] Confirm third-party dependency/data/attribution obligations for distribution. Basemap attribution must remain visible; source licensing does not grant rights to QRZ photographs or external datasets.
- [ ] Complete isolated Wavelog 3.2.3 write/retry/outage acceptance and ordinary post-field-audit contact/export verification, or explicitly retain experimental logging status in the published beta notes. Exporter omissions are not proof of failed submission.
- [ ] Obtain actual Ubuntu acceptance before advertising it as tested. Do not advertise verified Windows/Docker/MacLoggerDX support.
- [ ] Only after review: choose public visibility, create the approved tag and publish a GitHub **pre-release**. No binaries/container images are currently validated release artifacts.

Public release is intentionally **not yet ready for an unqualified production-logging claim**. A limited beta may be published after approval with these limitations plainly stated; the privacy/history review and maintainer release approval remain publication gates.

## Known limits

Same-call repeat clicks may not produce Status changes. Current-band counts include all modes. Inline biography, reverse radio control, bulk backfill and ADIF/Wavelog synchronization are absent. No authentication/public hosting is provided. UDP has no acknowledgement, and uncertain remote writes reconcile rather than blindly retry. Wavelog 3.2.3 can normalize/omit values in exports; optional-field live acceptance is still pending. GridTracker receiver tests found Unicode-name/fractional-power limitations in the tested receiver path; other receiving applications need their own tests.

Historical field-coverage validation at application `b2338e6` passed **179 backend tests**, **35 frontend tests**, type checking/build and **five affected browser workflows**. Those results precede this documentation branch. A Starlette/httpx deprecation and a separately loaded map-renderer size advisory remain.

## Fresh candidate validation

Pending execution in an isolated checkout. Record the tested commit, clean/repeat native installation, exact tests, document checks, screenshot provenance and any failures here before review. macOS evidence must not be relabeled as Ubuntu evidence. The live station checkout, settings, QSO files and queues are outside this validation environment.

## Scope of preparation changes

README and user guides, changelog/release draft, readiness checklist, a reproducible sanitized screenshot and a local link checker. Configuration-template comments are clarified without changing defaults. Package version is proposed as `0.9.0-beta.1`; its Node engine range changes from `>=24.15.0` to `>=24.15.0 <25` to match the existing installer. No dependency versions, UI behavior, logging architecture or production configuration are changed.
