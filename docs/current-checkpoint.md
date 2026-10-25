# Current checkpoint — reviewed main baseline

**October 25, 2026.** The operator approved [merging the reviewed features](main-baseline-merge-request.md) while preserving the single operating Dashboard and keeping all Dashboard submissions disabled. Both PRs are merged; the installed Dashboard is on `main`. UDP reception has a host-interface blocker described below.

## Published history

- [PR #3](https://github.com/kf6ufo/wsjtx-dashboard/pull/3), Step 4 station details/map: merge commit **`42220f0a048180ddf84506b2077a290c67cfa96e`**, head `18d4177206acc6d1a80667c177c0846a154781d5`.
- [PR #4](https://github.com/kf6ufo/wsjtx-dashboard/pull/4), optional QSO architecture: retargeted from Step 4 to `main`, then merged at **`e9fa332c8e9ec09e7fc244ee39b5b06238d65cf7`**, head `7189020ac8dcbb1643e85035780ada7a7f0c0e09`.

Both drafts were marked ready and merged with merge commits, preserving published ancestry and feature branches. The retargeted PR #4 diff was byte-for-byte identical to its reviewed stacked diff (38 files); its conflict-free proposed merge tree and final main tree both matched tested head `7189020`. No force pushes or feature changes were needed. Subsequent baseline documentation commits update these notes without changing the tested application tree.

## Validation

Actual platform: **macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0**, Chrome. At PR #4 head `7189020`:

- **93 backend tests passed**, including read-only Wavelog pagination, ADIF history/fallback/recovery, source precedence, duplicate protection, independent destinations, persistent queue/restart/uncertain outcomes, and multiple network IDs.
- **27 frontend tests passed**; TypeScript checking and production build passed.
- **All ten browser workflows passed**: foundation (1), dashboard (3), receiver (1), enrichment/photo/map (3), Wavelog (1), ADIF/delivery (1). These use isolated synthetic providers and loopback ports; they do not establish real Wavelog write acceptance.
- After PR #4 retargeting, the full backend/frontend suites and build passed again, along with the affected Wavelog and ADIF browser workflows. One existing Starlette/httpx test-adapter deprecation warning remains.
- Clean native `./install.sh` at identified commit `7189020` passed in `/private/tmp/wsjtx-main-baseline-install`. Repeating it preserved synthetic configuration, workspace SQLite, a pending-delivery SQLite row and ADIF bytes exactly. Both databases passed integrity checks. Installed production assets, restored preferences, retained pending work and disabled logging were verified on temporary port 8799; that test process was stopped.

Historical evidence is retained in [Step 4 checkpoint](step-4-checkpoint.md), [QSO preview checkpoint](qso-preview-checkpoint.md), and [Step 3 checkpoint](step-3-checkpoint.md). Ubuntu execution remains untested.

## Single operating installation and preservation

The sole installed Dashboard is **http://127.0.0.1:8787/**, serving checkout `/private/tmp/wsjtx-step3-native`, branch `main`, process **40123** at verification. Application source/build is merge `e9fa332`; later documentation-only updates need no backend restart. The former 8798 fixture preview remains stopped. Fixture validation servers were temporary and stopped after their workflows.

Before branch changes, configuration, complete data, built assets and consistent online SQLite copies were backed up privately at `/private/tmp/wsjtx-before-main-baseline-7jk_yv5q`. After gracefully stopping only Dashboard PID 34517, a complete cold backup was added in its `stopped/` subdirectory. The prior source revision is `f266d54`. No ADIF file is configured in this installation; no synthetic file/path was migrated.

The supported installer ran in the serving checkout. Its old `origin` referenced a historical local clone; this was corrected to `https://github.com/kf6ufo/wsjtx-dashboard.git` before fetching/building the verified main revision. Configuration and all data files remained byte-for-byte identical through installation. Both SQLite integrity checks passed. Immediately after startup, the focused call/source, all **88 Focus History entries** (including the earlier 86), shared preferences and **64 photo references** matched the stopped database exactly. Provider read caches and volatile receiver baselines naturally restart.

Read-only live API/Chrome checks confirmed actual authenticated Wavelog history (complete, one matching contact), QRZ data/profile photo and calculated radio enrichment, populated two-column details, worked-before display, contact dialog, map, history/contact panel alignment, Settings/Diagnostics navigation, narrow-screen width and no page errors. No provider write/retry/outage experiment was performed.

## UDP interface blocker

The preserved Dashboard configuration enables multicast `239.255.0.73:2238` on receiving interface **10.176.1.200**. After restart, macOS reports **10.176.1.91** as its current LAN address; 10.176.1.200 is not assigned. Receiver startup therefore reports `Can't assign requested address`. The old process had retained its previously opened socket; its earlier listening status does not prove fresh reception on the changed host address.

A temporary receive-only socket on 10.176.1.91 received 21 real packets from both `WSJT-X - IC7300` and `WSJT-X - IC9100`, then closed. This verifies a working receiving interface without modifying Dashboard configuration or launching another Dashboard.

Configuration was deliberately preserved, rather than silently changing the saved interface. The operator has been asked whether to update only Dashboard's receiving interface to 10.176.1.91. Until that choice is resolved, **live UDP reception and post-restart multiple-rig telemetry are blocked**, although the Dashboard and provider reads work. No WSJT-X, Wavelog or WaveLogGate settings/services were changed. Historical actual IC9100/IC7300 selection evidence and current isolated multiple-rig test passes remain separate from this live restart limitation.

## Logging safety and rollback

Both **`logging_enabled = false`** and **`log_to_wavelog = false`** were checked in saved configuration, API snapshot and Settings. The active outbox is empty. Production WaveLogGate remains unchanged and remains the uploader. Wavelog historical reads are enabled; credentials stay server-side. No production QSOs were submitted by Dashboard.

To roll back, stop only this Dashboard, preserve current files, use source `f266d54` (or its existing feature branch), restore matching `stopped/config.toml`, the complete `stopped/data/` and the previous build from the private backup, then run that revision's installer and restart. Do not overwrite later operating data or pending work without preserving it first. A source rollback does not resolve the changed host interface. Backups include credentials/operating data and are intentionally outside Git.

## Remaining work

- **Steps 0–4:** implemented and reviewed baseline. Inline biography retrieval remains deferred; actual Ubuntu install/upgrade/network acceptance remains untested. Resolve the current receiving-interface mismatch before claiming the live receiver healthy.
- **Step 5:** shared persistent, bounded, deduplicated Focus History already works, with thumbnails and preserved radio provenance while browsing. Retention/clear enhancements and final Step 5 acceptance remain unfinished.
- **Step 6:** independent ADIF history and durable enriched delivery infrastructure is implemented and tested offline. No isolated Wavelog instance currently exists. Real field acceptance/normalization and outage/reconciliation validation require an isolated instance, followed by explicit sole-uploader production cutover approval. This is not operational completion; keep Dashboard logging disabled and WaveLogGate unchanged.
- **Step 7:** UDP forwarding is not implemented.

Future development uses feature branches. No new feature development was part of this merge task.
