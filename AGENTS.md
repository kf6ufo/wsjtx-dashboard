# Codex instructions for WSJT-X Dashboard

## Mission
Build a polished, self-hosted, real-time, browser-based companion to WSJT-X, integrated with Wavelog. Read `docs/project-handoff.md` before planning or implementing any substantial work. The project is new and UI-first. The existing `kf6ufo/wsjtx-station-utility` is a reference implementation, not a codebase to overwrite.

## Development order
1. **Milestone 1 is UI FIRST.** Implement a beautiful, responsive two-panel dashboard with clearly identified mock data. Make the interactions real before adding external services.
2. Add live WSJT-X multicast Status-driven focus events and browser-wide live updates only after the UI is reviewed.
3. Add read-only, complete Wavelog QSO history, then QRZ/pyhamtools integrations.
4. Develop a replacement logging gateway only in later, explicitly authorized phases with passive comparisons, isolated tests, and a controlled cutover.

## Core interaction contract
- Left panel: current focused callsign, operator details/profile image when available, and full scrollable previous Wavelog QSO history.
- Right panel: scrollable and clickable history of **deliberately selected** callsigns, shared across all WSJT-X rigs and browser clients. Deduplicate by callsign and place most recently selected first.
- Ordinary Decode messages must not insert Focus History entries or steal focus.
- The current callsign and Focus History update immediately upon a selection; QRZ and Wavelog information loads separately and asynchronously.
- Prevent stale asynchronous lookup results from replacing the newer focused callsign.
- Clicking Focus History navigates the dashboard without sending commands to WSJT-X.
- Display separate pending, empty, unavailable/error, and loaded states. API failures must never be interpreted as zero QSOs.

## Known radio behavior
- The already tested WSJT-X multicast group is `239.255.0.73:2238`; Ubuntu receiver interface `10.176.1.6`.
- Existing senders include `WSJT-X - IC7300` (`10.176.1.5`) and `WSJT-X - QRPLabsQDX` (`10.176.1.7`). Additional rigs are expected. Identify instances by WSJT-X network ID rather than sender IP alone.
- WSJT-X Status `dx_call` changes were experimentally seen after clicks on both systems. A change is a practical selection signal, **not proof of a physical mouse click**. Treat initial Status as baseline; validate callsigns and handle cleared/unchanged values carefully.
- The UI should eventually use SSE or an equivalent server push mechanism with a snapshot endpoint for reconnects.

## Data ownership and logging safety
- Wavelog is the authoritative QSO logbook; never create a second independent permanent QSO log or write to Wavelog's database directly.
- Production WaveLogGate is working. **Do not disable, replace, modify, or compete with its live QSO submissions.**
- No live QSO writes, legacy API submissions, credential handling, or changes to production radio configuration in Milestone 1.
- Future logging requires verified Logged ADIF parsing, durable queue, careful retries/idempotency, station-location mapping, exhaustive tests, an isolated test Wavelog instance, and explicit approval before cutover.
- Do not introduce automatic ADIF synchronization or a local ADIF destination in the initial release unless requested.

## Technology and maintainability
- Current preferences: Vue 3 + TypeScript + Bootstrap 5 for the dashboard; Python + FastAPI for future server work; pyhamtools selectively for radio enrichment; Docker Compose on Ubuntu. These are recommendations, not permission to build all layers in Milestone 1.
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
