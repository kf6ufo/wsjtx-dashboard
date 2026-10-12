# WSJT-X Dashboard

A desktop-first station companion with dark and light themes built with Vue 3, TypeScript and Bootstrap 5. **Milestone 2 radio focus with sample enrichment:** fictional profiles, illustrative portrait placeholders and sample QSOs. Live rig identities come from WSJT-X; the separate demo uses three simulated rigs. Demo mode remains fully offline; explicit live mode receives WSJT-X selection data and synchronizes browsers. Profiles and QSO history remain samples. No Wavelog/QRZ connections, credentials, radio commands or QSO submissions. WaveLogGate is untouched.

See [Milestone 2 startup, architecture and validation](docs/milestone-2.md) for Mac development, GitHub release installation/updates and manual Ubuntu start/stop commands. Development and Codex stay on the Mac; Ubuntu is the runtime host. The station browser URL is **http://10.176.1.6:8000/?mode=live** after the documented installation. Open `/?mode=live` only when using the central backend; `/` keeps the separate accepted demo.

## Start and review (separate demo)

Install Node.js **24.15 or newer** (Node 24 LTS recommended), then open a terminal:

```sh
cd /Users/jerryjoplin/Documents/GitHub/wsjtx-dashboard
npm ci
npm run dev -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/** in your browser. The server binds to loopback only. Stop with Ctrl+C. For a production-build preview, run `npm run build`, then `npm run preview -- --port 4173` and open http://127.0.0.1:4173/.

This work session used a temporary Node runtime because Node was absent from PATH. While that runtime remains available, use:

```sh
export PATH="/private/tmp/node-v24.21.0-darwin-arm64/bin:$PATH"
npm run dev -- --port 5173 --strictPort
```

The temporary runtime may disappear after system cleanup; install Node for ongoing development.

## Try the separate demo interface

- The compact header keeps **Demo · No live connections** visible. **Station Desk** starts collapsed and remembers your open/closed preference locally; expand it to inspect all three simulated radio summaries. **Theme** switches dark/light and remembers that preference too. Storage restrictions fall back to session-only preferences. Focus/history remain tab-local and reset on reload.
- Start with JA2HDE: a generous portrait placeholder and all 24 sample contacts in an independently scrolling table. Click a contact date or arrow for details; Escape closes the dialog.
- Click QSO column headers to sort date/time, band, mode, sent report, received report, station or QSL. The arrow and accessible sort state show direction; click again to reverse. Dates use UTC instants, reports use numeric values, and bands use increasing frequency (40 m → 20 m → 15 m → 10 m). Default: newest contact first. The latest-contact summary stays independent of table sorting.
- The band indicator evaluates the focused callsign’s last simulated selection band, across all modes. Complete history shows “Worked on 20 m” and matching count, or “New on 20 m”; empty complete history also says “New callsign.” Pending, failed or incomplete history cannot claim new, and absent selection band shows “Current band unknown.”
- Click an older Focus History card. It displays immediately and stays in its existing position, highlighted, retaining its last simulated radio-selection timestamp, band and rig. Only a subsequent simulated radio selection moves it to the top. Rig-strip selections remain unchanged. Browsing time is displayed separately.
- Open **Demo tools** from the header. The separate dialog starts closed, explains each action, and affects demonstration data only. Simulate a station selection, selections from three radios, or an ordinary decode; decodes only increment a diagnostic counter. “Simulate a station selection” dispatches immediately and closes the dialog, including with Slow lookups enabled; loading continues visibly on the dashboard. You can also close the dialog or press Escape to return to the console; focus returns to its header button.
- Enable **Slow lookups** to see profile and QSO sections resolve independently. Use **Test responses arriving out of order** to send slow DL1DEMO followed by fast JA2HDE; late results cannot overwrite JA2HDE.
- VK3DEMO has zero sample contacts. PY2DEMO simulates an unavailable logbook; its worked-before status is unknown, never zero. ZS6DEMO has no profile. Failure fixtures remain failures on retry by design.

History and radio selections are in-memory and specific to this browser tab. Reload resets the demonstration. The rig strip displays simulated selections, not radio telemetry. History summary hints come from the fixture catalog, not remote enrichment.

## Checks

```sh
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

For existing macOS Chrome instead of downloading Chromium:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run test:e2e
```

Playwright starts a loopback Vite server if one is not already running. Tests use offline fixtures and never access radio services. Screenshots and build outputs are ignored by Git.

## Structure and boundaries

- `src/focus.ts`: selection, deduplication, recency, independent per-network-ID rig selections, asynchronous generation guards.
- `src/qso.ts`: value-based sorting and completeness-aware current-band status.
- `src/providers.ts`: independent asynchronous mock profile/QSO providers; no network calls.
- `src/fixtures.ts`, `src/types.ts`: fictional data and typed contracts.
- `backend/protocol.py`, `backend/receiver.py`, `backend/state.py`, `backend/app.py`: opt-in receive-only WSJT-X parser/socket, central state and SSE/snapshot/navigation API.
- `src/live.ts`: live-mode connection/reconnection and complete snapshot recovery.
- `src/App.vue`, `src/components/`, `src/style.css`: presentation and demo controls.
- `tests/`: state/component tests and browser smoke test.

Every accepted deliberate simulated selection updates radio provenance; dashboard browsing updates the displayed station and separate browsing time only, preserving list order and radio provenance. History order uses a selection-only sequence. The selection snapshots its band; browsing does not borrow another rig’s band. QSO providers return records plus an explicit completeness flag; incomplete results stay unknown, even if empty. Monotonic sequence numbers order interactions even when wall-clock timestamps tie. Profiles/QSOs reset to pending on navigation and reload independently; caching and persistence are deferred. The fixture set bounds demo history to six stations. This paragraph describes demo mode only. The separate live mode uses the Python Status receiver and centrally synchronized snapshots; no logging gateway exists.

See [project handoff](docs/project-handoff.md) and [current checkpoint](docs/current-checkpoint.md). **Milestone 1 accepted and pushed as `8a8c0df`; Milestone 2 has offline coverage and observed live reception from both rigs plus an operator-confirmed IC7300 selection. Full station/browser acceptance remains pending.**
