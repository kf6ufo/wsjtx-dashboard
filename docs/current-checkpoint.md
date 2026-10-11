# Current checkpoint

**Date:** 2026-10-11
**Status:** Milestone 1 interaction behavior reviewed and accepted by the operator. Milestone 2 explicitly authorized on 2026-10-11. This commit preserves the accepted Milestone 1 checkpoint before implementation begins.

## Delivered

- Vue 3 + TypeScript + Bootstrap 5 with a compact, single-row desktop header and station-first two-panel dashboard. The header keeps “Demo · No live connections” visible; the large header tagline and separate demonstration banner are removed. Dark/light themes are switchable and remembered locally.
- Station Desk starts collapsed on a fresh browser and retains its open/closed preference in localStorage. The expanded desk preserves the three simulated rig summaries. The button exposes `aria-expanded` and `aria-controls`; storage failures fall back to session-only preferences.
- Demo tools live in a separate native modal dialog, closed by default and never reserving space above the station. Plain-language actions and explanations identify demonstration-only effects. Supports keyboard focus wrapping, Escape, close button, and return focus to the opener. “Simulate a station selection” dispatches and closes immediately, restoring focus to the opener while profile/QSO loading continues on the dashboard, including with Slow lookups.
- Large illustrative profile placeholder, instant callsign focus, location, originating network-ID rig, last simulated radio-selection time, worked-before summary and complete scrollable sample QSO history. Clickable QSO detail dialog supports close, Escape, focus return and keyboard focus containment.
- Independently scrollable Focus History with six fixture stations, thumbnails and sample contact hints, deduplicated and ordered only by most recent simulated WSJT-X selection. The displayed station stays highlighted at its existing position after browsing.
- Three independent simulated rig identities. Dashboard history clicks change displayed focus and separate browsing time only, preserving the most recent radio-selection rig/time and every rig’s selection. Browsing never changes list order. A subsequent simulated selection moves the callsign to the top and updates selecting rig, time and captured band.
- Separate profile/QSO providers and presentation-independent focus state. Each lookup has pending, loaded, empty and error states. Generation guards discard late results, including requests for a callsign revisited later.
- Sortable QSO data columns (separate numeric sent/received reports), visible direction arrows and accessible `aria-sort`. Default newest first; frequency-ordered bands. Latest-contact summary is independent of table order.
- Current-band indicator uses the focused station’s latest simulated selection band across modes: worked/count, new-on-band and new-callsign only for complete history; checking, unavailable/incomplete and explicit unknown-band states otherwise. Providers explicitly report history completeness.
- Demo controls: explicit selections, interleaved rigs, passive routine decodes, slow lookups, and out-of-order responses.
- Empty QSO fixture (VK3DEMO), failed QSO fixture (PY2DEMO), and missing profile fixture (ZS6DEMO). Failed QSO lookups show unknown worked-before status.
- No live APIs, backend, credentials, persistence, browser synchronization, radio commands or logging submissions. WaveLogGate and production configuration untouched.

## Launch

Requires Node 24.15+; use Node 24 LTS. From this repository:

```sh
npm ci
npm run dev -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/**. Loopback binding only. Ctrl+C stops the server.

The preview was launched during this session at that address. Node was missing from the Mac shell, so a temporary Node 24.21.0 runtime was downloaded under `/private/tmp`. For this session only:

```sh
export PATH="/private/tmp/node-v24.21.0-darwin-arm64/bin:$PATH"
npm run dev -- --port 5173 --strictPort
```

See README for build preview and portable Playwright startup instructions. Install Node normally for ongoing use; temporary files may be cleaned by macOS.

## Validation

- `npm run build`: TypeScript validation and Vite production build passed.
- `npm test`: 11 tests across state, QSO logic and Vue component suites passed. Covers interleaved ordering/deduplication, independent rig identities, stable browsing order/provenance, frequency/date/report/text sorting, band-status states (including incomplete and unknown), passive decodes, delayed independent results, stale same-call requests, invalid events, QSO details and distinct pending/empty/error states.
- `npm run test:e2e` with installed macOS Google Chrome: three browser workflows passed. Added immediate selection-driven dialog closure, returned keyboard focus, visible slow-loading states, and preserved radio provenance/order through subsequent browsing. Added fresh collapsed defaults, remembered expanded/collapsed preferences across reloads, keyboard expansion, dialog focus wrapping/Escape/close/focus return, theme persistence and independent list overflow checks at 1920 × 1080. Covers three rig selections, browsing older entries, unchanged list order/rig selections/radio timestamps and active highlight after browsing, band sort toggling/direction, worked-on-band count, selection ordering/deduplication, quiet decodes, out-of-order results, contact details, empty/error fixtures, and 600px window width without page overflow. No browser runtime errors observed.
- Visually reviewed the station-first console at 1920 × 1080, with both optional sections closed, in dark and light themes; also reviewed the separate Demo tools dialog. Station/photo/details and two independently scrolling lists use the available desktop space. Screenshots are under ignored `test-results/`.
- Prior dependency installation/audit reported zero vulnerabilities; audit was not rerun for this refinement.

## Assumptions and untested behavior

- All identities, profile text and contacts are illustrative; portrait art is a local SVG placeholder, not a fetched photo. Station callsigns may coincide with actual callsigns, but data makes no claim about their operators.
- History is tab-local in-memory state. Reload resets it; only Station Desk visibility and theme persist locally; cross-browser synchronization is deferred to Milestone 2.
- Every demo selection button action is deliberate, including repeated same-call actions. Actual Status baseline/unchanged/clear semantics require a future receiver and are not implemented here.
- Incomplete-history and unknown-band states are exercised through injected test providers/selection options; current normal demo providers return complete data or a simulated error.
- Navigation refetches mock data; caching/TTL behavior is deferred. Fixture catalog supplies small history contact hints; no background external enrichment exists.
- Tested Chrome on this Mac, not Firefox/Safari/Edge, Windows or Ubuntu. No real WSJT-X/Wavelog/QRZ integration has been tested or claimed.
- Build succeeded; packaged production deployment, Docker and authentication are outside this milestone.
- Accepted Milestone 1 is being committed and pushed as the baseline for Milestone 2.

## Next action

Proceed with the authorized Milestone 2 receiver, central state and SSE/snapshot synchronization. Keep enrichment as clearly labeled sample data and WaveLogGate as sole production submitter.
