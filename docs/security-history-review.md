# Public-repository security and history review

Reviewed October 27, 2026, at main **`8d315c3`**. The repository was verified private. This is a review, not approval to change visibility, publish a release or rewrite history.

**Result:** no confirmed production credential exposure was found. Publication still needs an explicit decision about personal/station metadata in history and GitHub text. Two runtime hardening issues should be corrected before distributing the beta: HTTP hostname validation and restrictive initial file permissions. No application, operator configuration, QSO data or delivery queue was changed during this review.

## Findings requiring action

### 1. Validate HTTP hostnames before accepting API requests

**Priority: high hardening work before beta distribution.** [The same-origin middleware](../backend/app.py) compares Origin to the incoming request's base URL, but there is no trusted-host check. In an isolated ASGI test, an arbitrary hostname received a snapshot (200), and a settings write with that hostname and a matching Origin also succeeded (200). An explicitly foreign Origin and `Sec-Fetch-Site: cross-site` were correctly rejected (403).

This leaves a DNS-rebinding defense gap in an application with unauthenticated administrative APIs. The test establishes acceptance of an untrusted Host; it does **not** demonstrate a browser exploit. Browser/network protections affect exploitability. Loopback binding and the existing Origin check do not themselves validate Host.

Add a narrow allowed-host policy for the configured listener and supported local access names, retaining legitimate local/private-LAN access. Test unknown Host rejection for reads and writes, normal localhost/IP access, and foreign-Origin rejection. [Starlette documents trusted-host protection](https://starlette.dev/middleware/#trustedhostmiddleware). Authentication/public internet hosting remains outside the supported deployment model.

### 2. Restrict initial configuration and workspace permissions

**Priority: medium; shared-computer disclosure risk.** Under a typical `umask 022`, [the installer's exclusive config creation](../scripts/install-native.py) creates `config.toml` as **0644**. [Workspace creation](../backend/foundation.py) creates `data/` as **0755** and `workspace.sqlite3` as **0644**. This was reproduced using the same file-creation operations and actual workspace constructor in a temporary directory.

The example starts with empty credentials, and an API Settings save correctly replaces configuration with a **0600** file. However, credentials entered by manually editing the initial 0644 file would remain readable by other local users. Workspace history and stored photo URLs can also be locally readable. Other queue stores already set 0600.

Create new configuration/state files as 0600 and new private state directories as 0700. Review existing-file handling without overwriting content or changing ownership. Add tests under `umask 022`, including preservation of existing configuration, workspace and pending deliveries. Do not recursively change arbitrary operator paths or ADIF files as part of this fix.

### 3. Decide what personal/station history may become public

**Publication gate: operator disclosure decision, not a detected password leak.** Current and historical development records include station callsigns/grids, local usernames and machine paths, private network addresses, rig/source identities, and limited descriptions of real contact/delivery events. These are distinct from the fictional README screenshot fixtures. Author metadata also contains one personal email address; both author/committer email variants were inventoried privately.

| Surface | Examples of locations | Required decision |
| --- | --- | --- |
| Current development records | [Current checkpoint](current-checkpoint.md), [Step 4 checkpoint](step-4-checkpoint.md), [QSO preview](qso-preview-checkpoint.md), [Steps 5/7 review](steps-5-and-7-review-checkpoint.md) | Accept these disclosures, or sanitize the records |
| Project instructions and earlier history | [AGENTS.md](../AGENTS.md), [handoff](../WSJTX-REBUILD-HANDOFF.md), earlier versions of README/install/validation records | Review historical versions too; editing today's files does not remove old copies |
| Commit metadata | Author/committer identities across 103 reachable commits | Accept the personal email/name attribution or plan a coordinated metadata rewrite |
| GitHub pull-request text | PRs #5/#6 contain station network context; #8 contains specific failed-contact context | Accept or redact the descriptions separately from Git files |
| Existing historical pre-release | `m2-validation-20261012` release text and frontend archive | Review station network/operator context and distinguish this old milestone from the proposed v0.9 beta |

Callsigns and private LAN addresses are not authentication secrets; their publication may be acceptable to the operator. This review does not assume consent. No full live logbook file was found, but individual operating details in prose still deserve that decision.

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

## Before changing visibility

1. Correct findings 1 and 2, validate them with focused tests and review the resulting commit.
2. Record the operator's disclosure decision for finding 3. If redaction is required, perform and verify an explicitly approved cleanup before publication.
3. Review the old milestone release's text/assets alongside the new README and release notes.
4. Establish a private vulnerability-reporting channel. Review GitHub secret scanning/push protection and add a scoped recurring dependency/secret check; no workflow exists today.
5. Rerun scans at the exact publication commit after any cleanup. Retain the separate [release acceptance limitations](release-readiness.md), including Ubuntu and external write validation, and obtain explicit visibility/release approval.

## Limits and retained evidence

This is a targeted source/history review, not a penetration test, credential-validity check or full license/supply-chain audit. Dependency audits sent public package names/versions to advisory services, not application credentials or QSO data. Runtime probes used temporary configuration/databases with synthetic credentials, in-process ASGI requests and no background UDP/provider workers. The native Dashboard and station services were not restarted or reconfigured.

Detailed inventories, redacted scanner reports, private commit metadata, GitHub text, asset checks and isolated probe results are retained outside the repository. They are intentionally not included in this publication-facing report. Local-only generated fixtures/builds are excluded from Git; this review does not certify inaccessible server-side dangling objects, other people's clones, account-level secrets, branch protections, private-reporting configuration or unrelated services. GitHub warns that [Actions history/logs become visible when a repository becomes public](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
