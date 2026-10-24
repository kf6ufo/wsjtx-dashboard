# Current checkpoint — Step 3 preview

**October 23, 2026.** Steps 0/1 are reviewed on `main`. Step 2 enrichment and the profile-photo follow-up are on `feature/step-2-enrichment`; the operator tested QRZ and requested Step 3. The new **`feature/step-3-wavelog`** branch includes those changes and adds read-only Wavelog configuration/history. Its draft PR is stacked against the Step 2 branch until that branch merges. Do not proceed to QSO submission or forwarding. [Prior Step 2 evidence](step-2-checkpoint.md).

## Implementation

Settings adds the Wavelog application URL, write-only API v2 token, station/logbook scope, connection testing and bounded cache/pagination controls. Old Step 0–2 configs load without migration; Wavelog defaults disabled. Saves preserve receiver and QRZ settings atomically. Server-side credentials never return in snapshots or contact results. [Setup and operator review](step-3.md).

The default scope reads exact-callsign contacts across all locations authorized by the token, including previous KF0TKE and current KF6UFO. Optional logbook selection resolves its station IDs. Hidden locations can be resolved individually. All matching pages load before a complete result is declared. Failed/partial/pending/complete-empty/complete-loaded remain separate; worked-before and band status require a complete result within the selected scope. Optional confirmation failure leaves QSL unavailable independently of contact completeness.

Contacts load separately from enrichment and UDP processing. Small result metadata travels through SSE; each browser fetches the matching versioned contact result once, rather than resending contacts on Decode traffic. Server generation guards and browser request guards reject delayed results for older callsigns. Contacts are memory-only, with bounded caches, request/page/record/response-size/time limits. The table initially renders 100 contacts, with more available on request; sorting and read-only details use actual returned records. Production Wavelog/WaveLogGate and radio settings remain unchanged. No QSO writes, ADIF sync or forwarding exist.

## Verification

Host remains macOS 26.6.1 arm64, Python 3.13.1, Node 24.21.0 and installed Chrome. **77 backend tests**, **17 frontend tests** and the production build pass. One existing Starlette/httpx adapter deprecation warning remains.

Backend fixtures exercise exact callsign/full pagination, both station callsigns, optional confirmations, selected and hidden locations/logbooks, late focus changes, cache expiry/bounds, first/later-page failures, inconsistent totals/duplicates/empty pages, authentication/access/rate-limit failures, safety limits, safe errors and preservation of QRZ/receiver configuration. A two-browser workflow covers the real installed entry point with an offline Wavelog gateway and actual loopback UDP: 213 contacts, all pages, progressive rendering, details, incomplete history, genuine empty results, delayed focus, browsing provenance, connection settings, restricted scope, mobile width and continued UDP reception after disabling Wavelog. All eight offline browser workflows passed, including the existing enrichment/photo, receiver, foundation and fixture regressions. Browser-fetch coverage additionally verifies that a late HTTP result cannot replace a newer result even after returning to the same callsign.

**Live capability evidence:** the operator supplied `http://10.176.1.6:8086/api`; the installation’s actual public `/api/v2/status` returned HTTP 200 with Wavelog API status `ok`. This verifies API v2 reachability, not authenticated QSO reads. No production Wavelog token has been supplied to this implementation. The operator will enter a dedicated token locally in Settings; real station/location access, contact counts and confirmations remain to be verified. No production contact data is used in automated fixtures.

Native installation/upgrade and GitHub verification are being recorded below before handoff. Ubuntu execution remains untested, including dependencies/build, upgrades, multicast and browser/tunnel access. API v2 is required (Wavelog 3.1.0+); legacy API fallback is not implemented. Numeric version is not inferred from public status: supported endpoints/scopes are tested directly.

## Review installation

The review address remains **http://127.0.0.1:8787/**. The new source is `/Users/jerryjoplin/Documents/ChatGPT/WSJT-X Dashboard/wsjtx-dashboard-step2` on `feature/step-3-wavelog` (directory name retained). The operator’s VS Code checkout `/Users/jerryjoplin/Documents/GitHub/wsjtx-dashboard` is left intact. For a clean checkout, fetch and switch to `feature/step-3-wavelog`, then follow the native installer. Stop the existing dashboard before starting another on port 8787; cold-copy config/data as documented when moving the workspace.

Do not send tokens in chat. Use **Settings → Wavelog QSO history**, retain **All authorized station locations**, save the API v2 token with `qso:read` and `station:read` (optional `confirmation:read`/`logbook:read`), and test. Then enable history and select/browse a station. Review complete history against Wavelog before treating the integration as live-verified.
