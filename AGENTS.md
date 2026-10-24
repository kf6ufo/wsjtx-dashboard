# Codex instructions for WSJT-X Dashboard

## Mission
Build a polished, self-hosted, real-time, browser-based companion to WSJT-X, integrated with Wavelog. Read `WSJTX-REBUILD-HANDOFF.md` and the current checkpoint before substantial work. The project develops through reviewed, visual milestones. The existing `kf6ufo/wsjtx-station-utility` is a reference implementation, not a codebase to overwrite.

## Current authority and development order
Read `WSJTX-REBUILD-HANDOFF.md`, `README.md` and `docs/current-checkpoint.md` before substantial work. The October 23 rebuild handoff replaces the old milestone/deployment plan. Preserve existing history and work. `main` holds the reviewed implementation; use feature branches for future steps.

Steps 0 and 1 have been reviewed with the operator, including actual selections from IC9100 and IC7300. Step 2 enrichment and QRZ photos have completed code review and publication checks and are the current `main` scope. Step 3 Wavelog work exists separately in PR #2; do not merge it or begin further milestone work without a request.

0. Visual Station/Diagnostics/Settings foundation, server-owned sample state, SSE/reconnect snapshots, real native macOS and Ubuntu install path. Show Step 0 for review before Step 1.
1. Configurable primary WSJT-X UDP reception and bounded diagnostics.
2. Configurable enrichment (pyhamtools and verified callbook capabilities).
3. Complete Wavelog read history across authorized locations/callsigns.
4. Complete real station/profile/contact area.
5. Complete shared lookup history.
6. Optional enriched QSO submission with durable queue, isolated validation and approved production cutover.
7. Optional one-way UDP forwarding with verified destination formats.

Support the same source/server/build/config/persistence on macOS and Ubuntu. Native foreground operation is sufficient initially; Docker is optional. Validate clean installation at an identified commit and upgrades preserving operator configuration/state. Report actual OS evidence separately from simulation. Keep production station services unchanged throughout early development.

## Core interaction contract
- Left panel: current focused callsign, operator details/profile image when available, and full scrollable previous Wavelog QSO history.
- Right panel: scrollable and clickable history of **deliberately selected** callsigns, shared across all WSJT-X rigs and browser clients. Deduplicate by callsign and place most recently selected first.
- Ordinary Decode messages must not insert Focus History entries or steal focus.
- The current callsign and Focus History update immediately upon a selection; QRZ and Wavelog information loads separately and asynchronously.
- Prevent stale asynchronous lookup results from replacing the newer focused callsign.
- Clicking Focus History navigates the dashboard without sending commands to WSJT-X.
- Display separate pending, empty, unavailable/error, and loaded states. API failures must never be interpreted as zero QSOs.

## Known radio behavior
- Verified Step 1 multicast group `239.255.0.73:2238`; Mac receiving interface `10.176.1.200`; Ubuntu interface `10.176.1.6` is historical and must be verified.
- Step 1 observed `WSJT-X - IC9100` and `WSJT-X - IC7300`, both from `10.176.1.5`. QRPLabsQDX at `10.176.1.7` is historical context. Additional rigs are expected. Identify instances by WSJT-X network ID rather than sender IP alone.
- WSJT-X Status `dx_call` changes were experimentally seen after clicks on both systems. A change is a practical selection signal, **not proof of a physical mouse click**. Treat initial Status as baseline; validate callsigns and handle cleared/unchanged values carefully.
- Step 0 uses SSE or an equivalent server push mechanism with a snapshot endpoint for reconnects.

## Data ownership and logging safety
- Wavelog is the authoritative QSO logbook; never create a second independent permanent QSO log or write to Wavelog's database directly.
- Production WaveLogGate is working. **Do not disable, replace, modify, or compete with its live QSO submissions.**
- No live QSO writes, legacy API submissions, credential handling, or changes to production radio configuration in Step 0.
- Future logging requires verified Logged ADIF parsing, durable queue, careful retries/idempotency, station-location mapping, exhaustive tests, an isolated test Wavelog instance, and explicit approval before cutover.
- Do not introduce automatic ADIF synchronization or a local ADIF destination in the initial release unless requested.

## Technology and maintainability
- Current preferences: Vue 3 + TypeScript + Bootstrap 5 for the dashboard; Python + FastAPI for future server work; pyhamtools selectively for radio enrichment; native macOS and Ubuntu installations, with Docker optional. These are recommendations, not permission to build all layers in Step 0.
- Mimic Wavelog's visual familiarity without copying its branding or legacy architecture.
- Keep event processing, focus/history logic, Wavelog/QRZ providers, presentation, and eventual logging separately testable.
- Prefer typed APIs, bounded caches/queues, and offline fixture-driven tests. Document tradeoffs and assumptions.

## Security and quality
- Never commit .env files, tokens, credentials, live operator QSO logs, SQLite runtime databases, virtual environments, or build outputs.
- Never expose server-side Wavelog/QRZ credentials to the browser; do not publicly expose the dashboard by default.
- Add tests for operator selection ordering, independent rig identities, delayed/out-of-order lookups, and browsing older entries.
- Keep changes scoped to the requested milestone. Provide exact startup instructions and identify tests run versus untested behavior.
- Don't claim external integration works until verified with its actual API.

## Working agreement
Prioritize immediate visual feedback and operator ergonomics: build something the operator can launch and critique at every milestone. Don't proceed into the next milestone or enable live integrations without review.

**Guiding phrase:** The callsign appears instantly. Everything else arrives without interrupting the operator.
