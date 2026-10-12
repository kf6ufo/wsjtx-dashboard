# Current checkpoint

**Date:** 2026-10-12
**Status:** Milestone 1 accepted. Milestone 2 implemented and checked offline; **live reception from both rigs and an operator-confirmed IC7300 selection are observed; full station acceptance remains pending**. Do not begin Wavelog/QRZ integration or logging.

## Accepted baseline

Milestone 1 was committed and pushed to `origin/main` as **`8a8c0df`** before Milestone 2 implementation. It preserves the reviewed compact console, collapsed/persisted Station Desk, separate accessible Demo tools dialog, immediate dialog closure on simulated selection, sortable QSO columns, completeness-aware sample band status, independent scrolling, and stable radio-only history ordering after browsing. Milestone 2 is being published as GitHub validation release `m2-validation-20261012`. The release target and embedded frontend metadata record its exact commit; release notes and the delivery message record the full hash after commit/push. A commit cannot contain its own hash.

## Milestone 2 delivered

- Separate Python/FastAPI backend with independently testable protocol parser, receive-only multicast socket, central focus/history state and HTTP/SSE routes. No Qt, pyhamtools, Wavelog or QRZ dependency.
- Explicit opt-in multicast configuration. Known group/port `239.255.0.73:2238`; Ubuntu interface `10.176.1.6` must be specified explicitly. Receiver defaults off. Mac development HTTP stays on loopback; the explicit Ubuntu station launcher binds 10.176.1.6:8000 for trusted LAN access. One worker owns state. Join/receive failures are visible, and shutdown closes the receiver cleanly.
- Verified reference packet behavior by inspecting `wsjtx-station-utility/wsjtx_parser.py` at `0df3e5c`, checking the official WSJT-X protocol definition, and executing isolated reference parser functions against synthetic schema 2/3 Status/Decode fixtures. No reference application/integration was launched or modified.
- Network-ID rig identity, first-Status baselines, conservative ASCII callsign normalization/validation, unchanged-call suppression, and blank clears that preserve displayed focus/history. Band/mode/frequency/time are captured on selection. Close resets that ID's baseline. Extra telemetry/Decode packets do not alter radio provenance.
- Deduplicated, most-recent-radio-selection-first central history. Dashboard clicks change the shared displayed focus and browsing time only, preserving list order, selection timestamps, rig provenance and rig Status. No outbound radio commands exist.
- SSE broadcasts complete snapshots with bounded/coalesced queues, initial atomic subscribe/snapshot, heartbeat comments, disconnect cleanup and instance/revision IDs. The browser fetches a complete snapshot at initial connection/reconnection; older HTTP responses cannot overwrite newer state. Browser offline/online events explicitly close/reopen the stream; transient SSE failures also reconnect automatically.
- Explicit separate UI modes: `/` is the accepted local demo; `/?mode=live` uses only central state, starts empty, and cannot dispatch demo selections. Live mode shows radio connectivity separately from **Sample profiles/QSOs**, labels radio callsigns, and marks sample worked/band comparisons. Unknown real calls get no fabricated sample QSO history.
- Independent sample profile/QSO loading and stale-result generation guards remain in place. Same-call telemetry snapshots update provenance without restarting lookups. Server restart resets central state; page reload/reconnection restores it. History is capped at 200 callsigns, rig identities and browser streams at 32 each.
- Full instructions and design tradeoffs: [Milestone 2 guide](milestone-2.md).

## Startup

Exact Mac and Ubuntu commands, configuration variables, SSH tunnel/browser URLs, and offline checks are in [docs/milestone-2.md](milestone-2.md).

Mac development: create `.venv`, install `requirements-dev.txt`, start `backend.app:app` on loopback port 8000 with `WSJTX_RECEIVER=off`, and run Vite on port 5173. Open `http://127.0.0.1:5173/?mode=live` for the central UI or `/` for the separate demo. Vite proxies `/api` to the backend. A production frontend build can be served directly by FastAPI. The Mac development backend was launched on port 8000 with UDP explicitly disabled for review; the separate demo remains available on port 5173.

Ubuntu runtime: stable checkout `/home/jerry/wsjtx-dashboard`, isolated `.venv`, source from GitHub and matching prebuilt frontend from a tagged GitHub release. No Ubuntu Node/Codex app is required. Use `python3 scripts/install-ubuntu.py m2-validation-20261012`, then foreground `./scripts/start-station.sh`; Ctrl+C stops only this dashboard. Mac browser: **http://10.176.1.6:8000/?mode=live**. No router/firewall changes or automatic service installation. The temporary Uvicorn receiver (observed PID 60357 in `/home/jerry/wsjtx-m2-validation.JrNjUo/wsjtx-dashboard`) must be stopped in its terminal before installation. Keep all temporary files and the separate Downloads focus probe; keep WaveLogGate untouched.


## Offline validation

- `.venv/bin/python -m pytest backend/tests -q`: **14 passed** (9 receiver/state tests plus 5 release archive safety cases). Covers schema 2/3 fixtures, reference-compatible fields, append-only extensions, null strings, every truncation of the stable Status prefix, bad magic/schema/IDs/UTF-8/lengths, multiple IDs, baselines including invalid initial calls, valid/unchanged/blank changes, selection ordering/deduplication, passive Decode/other/QSO message types, Close, stable browsing provenance, queue/history/rig caps, complete reconnect snapshots, receive-loop recovery, configuration/socket construction, API navigation/origin rejection, and visible join/receive failure.
- `npm test`: **14 passed**. Includes the accepted 11 UI/state/QSO regressions plus live snapshot revision/epoch handling, stale provider results, simulation exclusion and refusal to invent sample history for unknown calls.
- `npm run build`: TypeScript and Vite production build passed.
- `npm run test:e2e`: **3 Chrome workflows passed**, preserving the accepted demo interactions, sorting/band states, stable history/radio provenance, preferences, dialog accessibility and immediate close with slow lookup states.
- `npm run test:e2e:live`: **1 offline Chrome workflow passed** using two isolated browser contexts and the separately hosted loopback fixture application with UDP disabled. Covers initial empty/baseline state, multiple IDs, synchronized selections and browsing, unchanged/blank calls, passive decodes, malformed data, deduplication/provenance, genuinely disconnected stale display, missed updates, a new snapshot request on reconnect, reload recovery, and unknown-call sample-data limits.
- Visually reviewed the 1920 × 1080 live-mode fixture screenshot with separate radio/sample labels and an older focused entry highlighted in place. Browser screenshots/build outputs/virtual environment remain ignored.
- Reference comparison: isolated reference Reader/header/Status/Decode functions agreed with schema 2/3 synthetic fixtures, without importing its runtime application.
- Python tests currently emit one Starlette TestClient deprecation warning about its httpx adapter; assertions pass. Python 3.13.1, FastAPI 0.143.0, Uvicorn 0.54.0, pytest 9.1.1, httpx 0.28.1 and Node 24.21.0 were used. Other platforms/browsers are untested.

## Actual station validation still required

Actual multicast reception and temporary Ubuntu deployment have now been observed (see live results below). The new GitHub installation, direct LAN browser access, explicit initial-baseline suppression, passive-decode stability, dashboard browsing/provenance and two-browser station operation still need validation. The exact live schema was not captured. “Listening” only means a successful socket join, not reception proof. No production radio settings, Wavelog/QRZ service, credentials, QSO submissions or WaveLogGate configuration were accessed/modified.

On Ubuntu, follow the [station validation checklist](milestone-2.md#station-validation-status-and-remaining-acceptance): confirm initial real-rig baselines, later callsign changes across IC7300/QRPLabsQDX/additional IDs, captured bands/modes, passive decodes/clears, stable browsing provenance, two-browser updates and reconnects, and continued existing WaveLogGate operation.

Status changes indicate practical selections, **not guaranteed physical mouse clicks**. An unchanged-call reselection may be undetectable. Unannounced rig restarts retain the previous baseline; an explicit Close or service restart resets it. There is no persistence, heartbeat timeout heuristic, replay log, authentication/TLS packaging or public hosting. UDP assumes a trusted station LAN. Complete receiver/SSE acceptance has been checked offline; live station evidence is limited to the results recorded below.

## Next action

Review Milestone 2 and perform the documented controlled Ubuntu reception checks without changing production radio/logging settings. Keep WaveLogGate as sole live QSO submitter. Stop before Milestone 3 until separately authorized.

## Station readiness session

The following readiness notes describe pre-deployment checks; the subsequent live validation section records the newer station results.

Implementation and guide reviewed for controlled station validation. Re-ran 9 Python tests, 14 frontend tests and production build successfully. SSH TCP port 22 at 10.176.1.6 is reachable from the Mac, but authenticated Ubuntu access is not yet established. No files have been transferred and no Ubuntu receiver has been started in this session.

Milestone 2 remains uncommitted on the Mac. A dedicated packaging script prepares a source/prebuilt-UI archive with checksums, excluding credentials/runtime data and the test injection server. Transfer will use a fresh Ubuntu validation folder rather than overwrite a station checkout. The guide now uses Mac SSH tunnel port 18000 to avoid the local development backend on 8000.

All five live acceptance checks remain pending on the actual station: initial baselines, selections from both rigs, passive decodes, stable history browsing/provenance, and two-browser synchronization/reconnection. Profiles/QSOs remain sample data. Operator preflight confirms Ubuntu user `jerry`, Python 3.12.3, interface `enxc8a362d3c546` UP at 10.176.1.6/24, TCP 8000 free, and an existing Python UDP listener on 2238 (PID 17225). Operator inspection identifies it as `/home/jerry/Downloads/wsjtx_focus_probe.py`, launched from a terminal. Its socket sets `SO_REUSEADDR` before wildcard binding and joins multicast on its configured interface. This supports attempting shared passive reception; actual coexistence remains untested. The probe remains untouched. Agent SSH authentication using noninteractive public-key/agent credentials was rejected; continuing through operator-run terminal steps. No files transferred and no new receiver started.

## Live station validation in progress

Operator copied the uncommitted validation bundle into fresh Ubuntu directory `/home/jerry/wsjtx-m2-validation.JrNjUo`, verified its archive checksum, extracted it, and installed requirements in its own Python 3.12 virtual environment. Bundle SHA-256: `ba9913dae4fe453dbd865d2800f3d728d2111e39de83272891510a3a3a22d751`. The bundled checkpoint predates these live results; this Mac working-copy checkpoint is the updated record.

Operator started one Uvicorn worker (PID 60357) on loopback TCP 8000 with receiver enabled at 239.255.0.73:2238 on 10.176.1.6. The existing probe was instructed to remain running; no production radio or WaveLogGate changes were requested.

First supplied live `/api/snapshot` (epoch `98554f3d708f424e97709c9b4fa0e451`, revision 262) confirms actual reception: 261 packets, 156 Decode messages, zero malformed, receiver listening without error. Both network IDs are present: IC7300 at 24.915 MHz/12m/FT8 with W0PE, and QRPLabsQDX at 28.074 MHz/10m/FT8 with KQ4ZIO. Focus/history contains one radio selection, W0PE from IC7300. The operator subsequently confirmed clicking W0PE after receiver startup, explaining the single selection. This verifies a real IC7300 selection in the receiver/state path, but does not establish browser latency, initial-baseline suppression or decode stability. Immediate dashboard updates, sample labeling on Ubuntu, history browsing/provenance, and two-browser synchronization/reconnection remain pending.


## GitHub runtime workflow revision (2026-10-12)

The archive-transfer workflow is retired. All development, reviews, checks, commits and frontend builds stay on macOS. GitHub holds source and commit-matched frontend release assets. Ubuntu only installs/runs the dedicated checkout and isolated Python environment. No remote station changes were performed during this workflow preparation. The former archive packaging script is replaced by `scripts/package-frontend.py`, `scripts/install-ubuntu.py` and `scripts/start-station.sh`; the complete repeatable procedure and manual shutdown are in the Milestone 2 guide.

Observed live results remain limited to receipt of both rig IDs and the operator-confirmed W0PE selection from IC7300. All five full live acceptance checks still need controlled verification: initial empty baselines; immediate dashboard selection from **both** instances with correct rig; routine decodes preserving focus/history; dashboard browsing preserving ordering/provenance; two browsers synchronizing and recovering after reconnect. Sample labels on the actual station dashboard also await operator confirmation. The new LAN-bound installation has not yet run on Ubuntu.


Publication checks on 2026-10-12: 14 Python cases passed (receiver/state/API plus frontend release commit/path/link validation); 14 frontend tests passed; production build passed; all 3 accepted demo Chrome workflows and the offline two-browser live synchronization/reconnection workflow passed again. `sh -n scripts/start-station.sh` and `git diff --check` passed. The installer itself has not yet been executed on Ubuntu; these offline checks do not assert successful GitHub authentication, LAN HTTP reachability, or the remaining live acceptance checks. Python tests retain the documented Starlette/httpx adapter deprecation warning.
