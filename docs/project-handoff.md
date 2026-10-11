# WSJT-X Dashboard
## Project vision, decisions, and Codex handoff

**Prepared:** 2026-10-11  
**Status:** Architecture and roadmap; Milestone 1 mock demo implemented locally. Operator refinements on 2026-10-11 supersede the original browsing-order proposal.
**Working repository name:** `wsjtx-dashboard`  
**Display name:** **WSJT-X Dashboard**  
**Alternative name retained:** WSJT-X Station Hub

## 1. Executive vision

Create a self-hosted, browser-based amateur-radio companion for multiple simultaneous WSJT-X instances, tightly integrated with **Wavelog** as the authoritative logbook. Begin with a beautiful, usable **UI-first dashboard**, integrating actual station events and lookup data incrementally. In later, separately validated phases, add a reliable, optionally enriched Wavelog logging gateway that could replace the currently working WaveLogGate.

The first great experience is simple: **select a station in any WSJT-X window; the dashboard immediately shows that station on the left and adds it to a shared, clickable Focus History on the right.** The left panel progressively fills with operator information, QRZ photo where accessible, and **all** previous QSOs from Wavelog. The operator can click an older entry on the right to inspect it again without interfering with WSJT-X. Incoming decodes must not steal focus.

A successful user experience matters as much as the data pipeline. The user previously developed `pskreporter-local` iteratively in Codex and enjoyed seeing the excellent UI develop continuously. Follow that development style here.

## 2. Firm product decisions

- **New project from scratch.** Do not mutate or repurpose the existing `wsjtx-station-utility` repository. Its tested behavior is a useful reference and safety net, not an architectural constraint.
- **UI-first.** Milestone 1 is an attractive, functional browser dashboard using clearly labeled mock data and interactive controls; live integration follows incrementally.
- **Wavelog-focused first release.** The target is self-hosted Wavelog and Wavelog Cloud as deployments of Wavelog, subject to actual API/access verification. Do not broaden v1 into a generic multi-logbook platform.
- **Wavelog remains authoritative for QSOs.** Do not create a second independent QSO logbook or write directly to Wavelog's SQL tables.
- **ADIF is a data format, not currently an output destination requirement.** An optional local ADIF output can be added later; it is not a priority in Wavelog-focused v1.
- **Cross-platform display.** Host centrally on Ubuntu; use ordinary browsers on Ubuntu, macOS, Windows. No separate desktop GUI needed.
- **Shared focus state.** One current focus and one chronological Focus History across all WSJT-X rigs and connected browser clients.
- **Operator-driven.** Add/reorder Focus History only on detected WSJT-X selection changes. Dashboard clicks change the displayed focus without changing list order, radio selection time or rig provenance. Routine Decode packets do not change either.
- **Instant focus, asynchronous enrichment.** Push the callsign and History change to connected browsers immediately; independently fetch/cache Wavelog and QRZ details. Old responses must never overwrite newer focus.
- **Existing QSO logging stays untouched initially.** WaveLogGate remains the sole live Wavelog submitter. The new app starts read-only/passive. Later logging replacement requires substantial testing and explicit production cutover.
- **Visual alignment, not technology imitation.** Bootstrap/Wavelog-like visual sensibility is useful, but do not copy Wavelog's legacy PHP/CodeIgniter technology merely for similarity.

## 3. Proposed initial technology (recommendations, not immutable requirements)

| Layer | Starting choice | Reason |
|---|---|---|
| Frontend | Vue 3 + TypeScript | Reactive focus cards, history, incremental updates |
| Styling | Bootstrap 5 plus small design tokens | Familiar Wavelog-ish look with custom operator-oriented layout |
| Backend | Python + FastAPI | Async HTTP, easy integration with Python amateur-radio packages |
| Amateur-radio helper | `pyhamtools` (selectively) | DXCC/country/zone lookups, grid heading/distance, band calculation, QRZ XML access where supported |
| Browser live updates | Server-Sent Events (SSE) initially | Server-to-browser focus and lookup result notifications |
| Small persistent store | SQLite when justified | Settings, possibly Focus History, and future durable outbound queue; never mirror the Wavelog QSO database |
| Deployment | Docker Compose on Ubuntu | Central operation alongside existing Wavelog Docker deployment |
| Tests | Pytest + frontend component/end-to-end tests | Offline fixtures and regressions, no radios required in CI |

Why Python? `https://github.com/dh1tw/pyhamtools` is a credible MIT-licensed library for ham-radio calculations and lookups. It supports callsign country/DXCC exceptions using sources such as country files and Club Log and includes locator/frequency calculations. Verify actual maintained APIs, dependencies and source licensing before adopting features. It does **not** replace Wavelog QSO history or guarantee QRZ profile photo access. Go remains a possible choice if a measured need emerges, but do not build a Go/Python two-service architecture speculatively.

Prefer a single manageable backend process initially; keep receiver, focus, lookup, and future logging components independently testable. Docker networking for UDP multicast on Linux needs early verification (host networking or an explicitly validated equivalent). Choose local HTTP port after checking conflicts. Store secrets on the server, never send API tokens to browser clients.

## 4. Proven station environment and observations

The older project successfully received WSJT-X **primary UDP multicast** on:

- Multicast group: `239.255.0.73`
- UDP port: `2238`
- Ubuntu receiver LAN interface: `10.176.1.6`
- Windows WSJT-X `WSJT-X - IC7300` sender: `10.176.1.5`
- macOS WSJT-X `WSJT-X - QRPLabsQDX` sender: `10.176.1.7`
- Additional rigs/WSJT-X IDs may exist or be added; do not hard-code the two as the only possible sources.
- Proven current packet magic: `0xADBCCBDA`, schema 2.

The user ran a **read-only focus probe** that listened for WSJT-X Status changes. Real output included:

```text
19:40:21  WSJT-X - IC7300  DX Call: PU2VGB -> FW1P  [FT8 24.915000 MHz, from 10.176.1.5]
19:41:46  WSJT-X - QRPLabsQDX  DX Call: PU6PSK -> PY5TZT  [FT8 28.074000 MHz, from 10.176.1.7]
19:44:09  WSJT-X - IC7300  DX Call: FW1P -> K5WBM  [FT8 24.915000 MHz, from 10.176.1.5]
```

**Conclusion:** The Status message's `dx_call` field is a practical and experimentally supported focus-change signal across both tested platforms. It is *not a formal guarantee that every change is a mouse click*. Initial Status packets reflect preexisting state and must not be counted as new clicks. Further tests should check clearing DX Call, same-call reselection, idle activity, and multiple simultaneous rigs. Do not substitute Decode traffic for selections.

The older Python parser supports Heartbeat (0), Status (1), Decode (2), and lists Logged ADIF (12) as future work. Preserve known-correct multicast/protocol behavior via tests, but a fresh implementation is allowed.

### Working logging state

- Wavelog is the authoritative logbook, hosted on Ubuntu in Docker. Local app URL has been `http://127.0.0.1:8086/index.php` **when accessed from the Ubuntu host**. Inside another Docker container, localhost will mean that container and may be incorrect: determine appropriate Docker network/service URL.
- Previous Wavelog read integration used API v2 GET QSO endpoint with Bearer `qso:read` token and paginated results; inspect/verify current Wavelog behavior when implementing full QSO records.
- Historical QSOs have been migrated and checked; older call KF0TKE and newer KF6UFO must be included under the authorized Wavelog scope for accurate 'worked before' results.
- WaveLogGate is currently correctly submitting new contacts with station location mapping. Keep it running while the dashboard is developed. QRZ/LoTW/eQSL operations belong to Wavelog's existing workflow.
- User is content with **manual Wavelog Update from Callbook and manual ADIF exports**, then manual scripts to update WSJT-X `wsjtx_log.adi` on Windows/macOS. Do not introduce synchronization automation unrequested.
- Missing Wavelog Operator and Antenna Azimuth on some QSOs are **not a current blocker**.

## 5. Main screen: UI behavior contract

### Left panel: currently focused callsign

- Large, prominent callsign.
- QRZ/profile name, location, country, grid, available picture, clickable source link, and source/last-updated indicators; clear placeholders for unavailable fields.
- Originating WSJT-X rig and current known band/mode, where relevant.
- Wavelog-backed 'worked before' status, count, most recent QSO, unique bands/modes, and **every matching QSO record** (scrollable and optionally filterable/sortable) rather than just a summary of three contacts.
- Dates/times in clearly indicated UTC or explicitly user-selected time zone, band, mode, reports, and later LoTW/eQSL/QRZ confirmation fields if API supports them.
- Clickable individual QSO details. Sort every displayed data column with visible/accessibility direction state; default newest first, dates/reports by underlying values, bands by frequency.
- Current-band status evaluates the focused station’s latest selection band across all modes. Only complete history can show worked count or new-on-band; zero total QSOs also identifies a new callsign. Pending, failed, incomplete and unknown-band states must remain explicit.
- Display immediately on selection with independent Wavelog/QRZ loading/error states. Never mark a station 'not worked' on a timeout, authorization failure or incomplete pagination; show 'unavailable'.

### Right panel: Focus History

- **Only intentionally focused stations**, not all heard stations. Global across 2–3+ WSJT-X instances.
- Chronological most-recent-first, scrollable, clickable, photo thumbnail where available, callsign, brief location, QSO count/status, originating rig, selection time.
- If the same callsign is selected again, move it to the top, do not create duplicate cards; update originating rig and time.
- Clicking an older card displays it on the left. Do **not** send commands to or change the selected callsign within WSJT-X.
- Browser navigation changes displayed focus only. Preserve the existing list order, selection timestamps, selection band and rig provenance; highlight the displayed entry wherever it sits. Only a subsequent WSJT-X selection moves a callsign to the top and updates radio provenance. Keep a coherent global displayed focus across clients in the future shared-state milestone.
- Ordinary decodes may populate *separate internal Heard History/statistics later*; they must not insert Focus History entries or steal active focus.
- Reuse cached results instantly on returning to a previous callsign, refreshing them asynchronously according to explicit TTL policy.

### Multi-rig event semantics

- Every WSJT-X client is identified by its network ID, not solely by sender IP/UDP port.
- First Status per rig supplies baseline, **not** a new selection.
- Subsequent meaningful `dx_call` changes are candidate focus events. Validate/normalize callsigns conservatively; ignore unchanged values and handle blank clears intentionally.
- Cross-rig selections are ordered centrally by reception/event time.
- Prevent stale async responses from changing the currently displayed callsign.
- Avoid having WSJT-X change selected calls when the user clicks cards in dashboard.
- Connected browsers update automatically without reload. SSE is an appropriate initial choice. On reconnect, fetch a complete state snapshot; do not rely on event history alone.
- If same callsign is selected a second time in a *single* WSJT-X rig without changing `dx_call`, Status-only change detection may not observe it. Document as a limitation and investigate if operators care.

## 6. UX-first Codex milestones

### Milestone 0: New repository, specification and runnable skeleton

- Establish `wsjtx-dashboard` as a **new** GitHub repo/Codex project (no destructive changes to the old repo).
- Add `AGENTS.md`, developer setup, user-facing README, test/build scripts, architecture notes, example settings, `.gitignore`, secret hygiene.
- Minimal app launches reliably in local development; no production logging.

### Milestone 1: **UI FIRST** (no radios or Wavelog required)

- Build the attractive two-panel responsive dashboard with realistic **clearly labeled mock/fixture data**.
- Working click behavior for Focus History cards; 2–3 rig identities and interleaved focus examples; sample operator photos/placeholders; independently scrollable QSO and Focus History lists.
- Distinct loading/loaded/no-QSO/unavailable/error states and skeletons.
- Dark mode, strong legibility on a large Ubuntu monitor, responsive use on macOS/Windows, familiar Bootstrap/Wavelog visual vocabulary without copying their assets or trademarks.
- Add a developer-only action for simulating incoming focus events and slow/out-of-order data loads; prove the UI never jumps backwards.
- Component tests and a basic end-to-end smoke test.

### Milestone 2: Live events and cross-browser focus

- Connect actual primary WSJT-X multicast via a separate, tested receiver module.
- Normalize Status change events per rig, matching observed probe behavior; keep non-Status decodes passive.
- Connect backend state to browser(s) via SSE and snapshot endpoint; prove two browser windows synchronize.
- No Wavelog writes; logging path untouched.

### Milestone 3: Wavelog read-only integration

- Configure self-hosted or cloud Wavelog endpoint and least-privilege read token.
- Retrieve complete matching QSO records using verified API behavior; accurate pagination across older/current callsigns/locations in authorized account.
- Independent async lookups, caching and explicit error states; test empty vs failed/incomplete query.
- Display real records, with details and optional filters.

### Milestone 4: QRZ / radio enrichment

- Introduce pyhamtools for useful verified features (DXCC exceptions, country, zones, locator heading/distance, band mapping) and evaluate QRZ XML lookup through it or a dedicated provider.
- Verify QRZ credentials/subscription and profile-picture availability. Use placeholders where photos cannot be retrieved legally/technically. Do not scrape indiscriminately.
- Focus History thumbnails and cached profile data.

### Milestone 5: Passive QSO recording and enrichment testing

- Parse WSJT-X Logged ADIF messages (type 12) from the **primary** UDP stream; no writes.
- Compare parsed QSO data with WaveLogGate-submitted Wavelog records, including sender/rig-to-Wavelog station location mapping.
- Define field-by-field enrichment policy (never fabricate measurements; calculated azimuth is bearing, not measured antenna heading).
- Test malformed packets/ADIF, retries, duplicates, interleaving and station restarts. Record diagnostics safely.

### Milestone 6: Controlled Wavelog logging gateway

- Add durable, recoverable outbound queue (SQLite suitable) with retry strategy and duplicate safeguards. Idempotency cannot be assumed from the HTTP API alone: explicitly verify semantics and ambiguous timeout behavior.
- Verify the supported Wavelog legacy submission endpoint and payload against deployed Wavelog version; use a **test** Wavelog instance for actual sends.
- Keep submission disabled by default until approved. Never run WaveLogGate and new submission concurrently for live production contacts.
- Validate and document rollback and cutover. **Logging correctness and QSO safety outrank feature velocity.**

### Later, not first release

- LoTW/eQSL/QRZ confirmation indicators if supported by Wavelog read APIs.
- Passive decode statistics, propagation openings, alerts.
- Optional ADIF-file logging destination.
- Additional digital-mode clients or browser settings/dashboard expansions.

## 7. Nonfunctional requirements and testing

- **Reliability first:** no missed/duplicated completed QSOs when future logging enabled; auditable diagnostics, recovery after restarts and outages.
- **Read-only until deliberate cutover:** current WaveLogGate and Wavelog production logging remain authoritative.
- **Cross-platform access:** Ubuntu-hosted browser UI works on current macOS and Windows clients.
- **Async isolation:** QRZ/Wavelog slowness must not block UDP reception, focus events or the logging queue.
- **Security:** Wavelog/QRZ credentials server-side only; authenticate/protect LAN dashboard and admin features appropriately; bind only to intended interfaces; do not publicly expose it by default.
- **Resource efficiency:** bounded queues, caches/TTLs, pagination caps with explicit error state rather than silently truncating QSO history; SSE reconnect/state synchronization.
- **Offline testability:** simulated WSJT-X packets, fixture Wavelog/QRZ responses, focus interleaving, packet truncation, Wavelog errors, reconnection, duplicate QSO submission scenarios.
- **No undocumented live dependencies in early milestones:** mock data first, then opt-in integrations.
- **Maintainability:** provider abstractions and explicit typed schemas between backend and frontend; separate modules for protocol, state, lookup, presentation and later submission.

## 8. Open questions (do not block UI-first development)

1. **Visual preference:** exact Wavelog light/dark aesthetic vs a distinctive dashboard theme; start dark, polished and Wavelog-adjacent, solicit feedback on real mockups.
2. **QRZ images:** confirm supported source, entitlements, usage rights and fallback behavior.
3. **Focus persistence:** should Focus History survive service restart? Recommendation: yes, via small SQLite state in a later milestone; for Milestone 1, in-memory history is sufficient.
4. **Browser-wide control:** global focused station is desired. Confirm semantics if different browsers click different historical callsigns simultaneously; recommended latest intentional interaction wins.
5. **Repeated same callsign:** Status `dx_call` changing back to a prior call is proven; clicking the already-selected call may not emit a distinguishable event. Evaluate if user sees a problem.
6. **Cloud Wavelog access:** authenticate, verify API version and network access on an actual cloud deployment before claiming full compatibility.
7. **Enrichment authority:** exact fields and rule priorities should be configurable and confirmed with real ADIF/Wavelog examples before enabling writes.
8. **Framework/package choices:** Vue/FastAPI/pyhamtools are informed recommendations, not sacred. Codex should document any deviation and avoid unnecessary complexity.

## 9. Relevant reference projects

- Existing proof-of-concept: `https://github.com/kf6ufo/wsjtx-station-utility` — known-working Python WSJT-X protocol parser, multicast, focus model and Wavelog read-only lookup; **reference, not base repository**.
- Ham radio helper library: `https://github.com/dh1tw/pyhamtools` — MIT license, callsign/DXCC data, locator and frequency calculations, QRZ XML capabilities.
- Wavelog: `https://github.com/wavelog/wavelog` and `https://docs.wavelog.org/` — authoritative logbook and API contract.
- `pskreporter-local` — user's successful UI-first Codex development precedent; use its workflow inspiration, not assume code reuse.

## 10. Recommended initial Codex instruction

> Create a **new** repository/project named `wsjtx-dashboard` for **WSJT-X Dashboard**. Read this handoff first. We are deliberately starting over rather than modifying `wsjtx-station-utility`. Begin with **Milestone 1: UI FIRST**. Build a polished, responsive, Wavelog-adjacent two-panel dashboard using Vue 3, TypeScript and Bootstrap 5 (or justify a simpler alternative). The left side displays the currently focused station, profile/photo placeholder, and complete scrollable sample QSO history. The right side displays an independently scrollable, clickable, global Focus History across multiple radios, with thumbnail placeholders. Make interactions work using mock data, including a developer-mode simulation of incoming selections and deliberately delayed lookups. Immediately switch focus while independently loading sections; stale asynchronous responses must never overwrite newer focus. Provide loading, unavailable and empty-history states. Add sensible tests and instructions to run and view it. **Do not yet integrate live UDP, Wavelog/QRZ credentials, or submit any real QSO.** Show the interface for review before proceeding to backend integration.

---

**Guiding phrase:** *The callsign appears instantly. Everything else arrives without interrupting the operator.*
