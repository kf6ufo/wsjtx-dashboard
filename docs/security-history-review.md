# Public-repository security and history review

Reviewed October 27, 2026, at main **`8d315c3`**. The repository was verified private. This is a review, not approval to change visibility, publish a release or rewrite history.

**Current result:** no confirmed production credential exposure was found. The October 27 security-hardening update fixes the hostname and initial-permission findings, with validation at application commit **`b7b8599`** described below. The operator explicitly accepts publication of historical callsigns, private LAN addresses, machine paths and QSO-related development examples. Git history is preserved. The personal email in commit attribution remains a separate publication decision; this acceptance does not authorize exposing credentials, changing visibility or publishing a release.

## Initial findings and resolutions

### 1. Validate HTTP hostnames before accepting API requests

**Resolved by the hardening update.** At the initial review commit, [the same-origin middleware](../backend/app.py) compared Origin to the incoming request's base URL without a trusted-host check. In an isolated ASGI test, an arbitrary hostname received a snapshot (200), and a settings write with that hostname and a matching Origin also succeeded (200). An explicitly foreign Origin and `Sec-Fetch-Site: cross-site` were correctly rejected (403).

This leaves a DNS-rebinding defense gap in an application with unauthenticated administrative APIs. The test establishes acceptance of an untrusted Host; it does **not** demonstrate a browser exploit. Browser/network protections affect exploitability. Loopback binding and the existing Origin check do not themselves validate Host.

The update adds Starlette's trusted-host middleware before Origin checks and routes. It accepts only `localhost`, `127.0.0.1` and the configured `[http].host` address, with normal port handling. Host identifies the requested server, so clients on other computers need not be allowlisted. Unexpected hosts receive 400 for reads, writes and SSE; foreign-Origin/cross-site writes still receive 403. No wildcard hosts or new configuration keys are introduced. [Starlette documents trusted-host protection](https://starlette.dev/middleware/#trustedhostmiddleware). Authentication/public internet hosting remains outside the supported deployment model.

### 2. Restrict initial configuration and workspace permissions

**Resolved by the hardening update.** At the initial review commit, under a typical `umask 022`, [the installer's exclusive config creation](../scripts/install-native.py) created `config.toml` as **0644**. [Workspace creation](../backend/foundation.py) created `data/` as **0755** and `workspace.sqlite3` as **0644**. This was reproduced using the same file-creation operations and actual workspace constructor in a temporary directory.

The example starts with empty credentials, and an API Settings save correctly replaces configuration with a **0600** file. However, credentials entered by manually editing the initial 0644 file would remain readable by other local users. Workspace history and stored photo URLs can also be locally readable. Other queue stores already set 0600.

The update creates/opens configuration and all four SQLite stores through [private storage helpers](../backend/private_storage.py). Configuration/database files use **0600**, named private data/provider directories use **0700**, and existing SQLite sidecars are restricted before opening. Existing named configuration/state paths are tightened without replacing their contents or changing ownership. There is no recursive permissions sweep, no ADIF permission change and no schema/data migration. Symlink/non-regular configuration or database files and symlinked private directory targets are rejected rather than following them into operator files.

### 3. Decide what personal/station history may become public

**Station-context disclosure accepted; commit-email decision remains separate.** In the October 27 hardening request, the operator accepts publishing historical callsigns, private LAN addresses, machine paths and QSO-related development examples. Current and historical development records contain this context, distinct from the fictional README screenshot fixtures. Author metadata also contains one personal email address; both author/committer email variants were inventoried privately. This request does not explicitly accept that email disclosure, so it remains open before visibility changes.

| Surface | Examples of locations | Decision/status |
| --- | --- | --- |
| Current development records | [Current checkpoint](current-checkpoint.md), [Step 4 checkpoint](step-4-checkpoint.md), [QSO preview](qso-preview-checkpoint.md), [Steps 5/7 review](steps-5-and-7-review-checkpoint.md) | Historical station/QSO context accepted; retain records |
| Project instructions and earlier history | [AGENTS.md](../AGENTS.md), [handoff](../WSJTX-REBUILD-HANDOFF.md), earlier versions of README/install/validation records | Historical station/network/path context accepted; retain Git history |
| Commit metadata | Author/committer identities across 103 initially reviewed reachable commits | Personal email disclosure remains a separate decision; no rewrite is authorized |
| GitHub pull-request text | PRs #5/#6 contain station network context; #8 contains specific failed-contact context | Covered by accepted historical station/QSO examples |
| Existing historical pre-release | `m2-validation-20261012` release text and frontend archive | Historical station context accepted; keep this old milestone distinct from the proposed v0.9 beta |

Callsigns and private LAN addresses are not authentication secrets. The operator's acceptance covers the stated historical station context, including the related development examples in GitHub text and the older milestone. No full live logbook file was found. No history rewrite or new credential disclosure is authorized.

If removal is chosen, cleaning the current branch alone is insufficient. A coordinated cleanup must consider branches, tags, commit metadata, pull-request references/text, release assets and other clones. Preserve a private backup first. GitHub documents the side effects and additional steps for [removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository). No rewrite, force push, release deletion or credential rotation was performed.

## What was checked

| Check | Evidence/result |
| --- | --- |
| Reachable history | **103 commits, 695 unique blobs, 173 historical paths**; fetched current branches/tags and all **11 PR heads**; GitHub advertised no retained PR merge refs |
| Historical file inventory | No committed `config.toml`, `.env` file, runtime SQLite database, standalone ADIF logbook, private-key file, virtual environment or dependency/build tree was found; inline ADIF records were test fixtures |
| Gitleaks 8.30.1 | Official release binary checked against its published SHA-256; default rules, redacted output, no external config override. Git diff scan reported **7** findings; independent complete-blob scan reported **15** versioned occurrences. All were manually identified as synthetic tokens in two mocked Wavelog test files; no broad allowlist was added |
| Supplemental credential inspection | **68 literal-assignment occurrences / 12 distinct candidate values**, all synthetic test credentials or deliberately invalid validation inputs. Local exact-value comparison found **zero** matches for the saved Wavelog token or QRZ password in historical blobs; their values were never included in reports or sent to a service |
| Commit messages and GitHub text | Secret scans found none; reviewed all **11 PRs**, their issue representations, release text and commit metadata. Issue comments, inline PR comments and submitted reviews were empty |
| Existing release assets | Downloaded `frontend.tar.gz` and its checksum from the historical pre-release; checksum matched. Inspected all members without executing the bundle; secret scan found none. Operator context remains in the bundle |
| Actions | GitHub reported **zero workflow runs and zero artifacts**; no workflow files were found in reachable Git trees |
| npm advisory audit | Locked dependency audit returned **zero known vulnerabilities**, including development dependencies |
| Python advisory audit | `pip-audit` checked **25 pinned runtime packages**, with **zero known vulnerabilities and no skipped packages** |
| README images | Only the two sanitized PNG paths occurred as historical binary assets. Both current images have no EXIF/text metadata; capture fixtures use fictional data and an original illustration |
| Isolated API checks | Foreign-Origin/cross-site writes rejected (403); saved synthetic Wavelog/QRZ credentials absent from snapshots; direct config/traversal requests not served (404); arbitrary Host acceptance confirmed as finding 1 |

The Git diff scanner reports 91 scanned commit diffs; the separate tree/blob inventory covers all 103 reachable commits, including unchanged/merge snapshots. Scanner matches were not automatically treated as real credentials, and a zero advisory count is not a security guarantee.

## Existing protections and operating boundaries

The installer defaults to loopback with integrations/logging/forwarding disabled. Saved provider credentials are omitted from public settings/snapshots and dataclass representations. Provider requests use bounded reads/timeouts and reject redirects; QRZ uses HTTPS POST, and XML handling rejects DOCTYPE. Vue interpolation and URL validation avoid rendering arbitrary provider HTML or unsafe link schemes. Durable logging receipts and existing duplicate protection were not changed or exercised against production.

Wavelog URLs permit HTTP as well as HTTPS. Use HTTPS when traffic crosses an untrusted network: bearer tokens are not encrypted by HTTP. Any client able to reach the Dashboard has administrative access; publishing its source does not make public hosting supported. UDP reception also assumes a trusted station network.

## Hardening validation — October 27

Validation used a clean native macOS checkout at **`b7b8599`**, with the actual installer and pinned dependencies, separate from the operating station. No synthetic contact was sent to production Wavelog.

| Check | Actual result |
| --- | --- |
| Backend tests | **199 passed**, including host allow/reject cases, remote-client identity, settings writes, Origin restrictions, all four SQLite stores/sidecars, symlink/non-regular rejection, queue receipts and duplicate protection |
| Frontend tests | **35 passed**; type checking and production build passed |
| Isolated browser workflows | **13 passed**: demo, foundation, receiver, enrichment/QRZ fixtures, Wavelog fixtures, independent ADIF, Steps 5/7 and station mapping |
| Configured LAN address | Actual server bound to the Mac's LAN IPv4 on an isolated port; two independent browser contexts received SSE/focus changes from synthetic IC7300/IC9100 identities, browsed shared history and saved settings. Invalid-host read/write/SSE returned 400; foreign-Origin write returned 403 |
| Installation/restart preservation | Fresh install under `umask 022` created 0600 config. A real repeat install preserved config, synthetic ADIF and all four SQLite files byte-for-byte, including ownership/modes, pending delivery and receipt data. Automated tests also restarted the real server twice with an open SSE stream and reopened seeded history/queue state |
| Live station | The existing 8787 endpoint refused connections during this task; it was not started, restarted, updated or reconfigured. Its source revision and saved configuration are preserved |

The LAN-address check ran both client contexts on the same Mac. Actual access from a second physical computer and live reception from the operating radios were **not verified for this candidate**. Provider/browser fixtures and existing historical API evidence do not establish new production acceptance. Actual Ubuntu/Windows/Docker execution and full isolated Wavelog write/outage validation remain unverified. Existing Starlette/httpx and separate map-renderer size advisories remain.

## Before changing visibility

1. Review the hardening diff and validation evidence; the operator authorized merging after checks pass. Deployment to the operating installation is a separate action and was excluded from this task.
2. Retain the accepted historical station context and resolve the remaining personal commit-email decision before publication. Do not rewrite history without explicit authorization.
3. Review the old milestone release's text/assets alongside the new README and release notes.
4. Establish a private vulnerability-reporting channel. Review GitHub secret scanning/push protection and add a scoped recurring dependency/secret check; no workflow exists today.
5. Rerun scans at the exact publication commit after any cleanup. Retain the separate [release acceptance limitations](release-readiness.md), including Ubuntu and external write validation, and obtain explicit visibility/release approval.

## Limits and retained evidence

This is a targeted source/history review, not a penetration test, credential-validity check or full license/supply-chain audit. Dependency audits sent public package names/versions to advisory services, not application credentials or QSO data. Runtime probes used temporary configuration/databases with synthetic credentials, in-process ASGI requests and no background UDP/provider workers. The native Dashboard and station services were not restarted or reconfigured.

Detailed inventories, redacted scanner reports, private commit metadata, GitHub text, asset checks and isolated probe results are retained outside the repository. They are intentionally not included in this publication-facing report. Local-only generated fixtures/builds are excluded from Git; this review does not certify inaccessible server-side dangling objects, other people's clones, account-level secrets, branch protections, private-reporting configuration or unrelated services. GitHub warns that [Actions history/logs become visible when a repository becomes public](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
