# Milestone 2: receiver and synchronized focus

Milestone 1 was reviewed and accepted, then committed and pushed to `origin/main` as **8a8c0df** before this implementation began. This phase receives radio focus only. Operator identities, portraits, QSO records, worked-before and band comparisons remain **sample data**. No Wavelog/QRZ access, credentials, QSO storage/submissions, radio commands or production configuration changes exist here.

## Architecture and protocol verification

`backend/protocol.py` is an independent, bounded standard-library reader, rather than a dependency on the reference application or Qt. Before implementation, the local `wsjtx-station-utility/wsjtx_parser.py` at reference commit `0df3e5c` was inspected for Reader/header/Status/Decode and multicast socket behavior. Its parser functions were subsequently executed in isolation against synthetic fixtures (without importing/running the application or its integrations); schema 2/3 Status fields and Decode text agreed. The reference application's Decode-driven focus logic is deliberately not adopted.

The [WSJT-X NetworkMessage.hpp protocol definition](https://raw.githubusercontent.com/WSJTX/wsjtx/master/Network/NetworkMessage.hpp) independently confirms big-endian encoding, magic `0xADBCCBDA`, UTF-8 QByteArray length/null semantics, network IDs, Status fields and append-only extensions. We support schema 2 and 3 for the fields used here; schema 1 and unknown schemas are rejected. The parser requires the stable Status prefix through DX grid, ignoring subsequent extensions. Decode's mandatory payload is validated, then discarded. Other types are safely ignored after validating their header; Close (6) resets that ID's baseline. QSO Logged (5) and Logged ADIF (12) have no QSO processing.

- `backend/state.py`: single event-loop-owned central displayed focus, radio-only history, rig telemetry, counters and revision/instance IDs. Network ID is the key, never sender IP. History holds at most 200 distinct callsigns, and telemetry/baselines at most 32 IDs. Extra IDs are refused and counted until a restart. State is memory-only; server restart intentionally resets history and baselines.
- First Status per ID establishes a baseline without selection, including blank/invalid DX fields. Later valid normalized DX changes select. Normalization trims whitespace, uppercases ASCII, and conservatively requires 3–15 alphanumeric/slash characters with both a letter and digit and no empty slash segment. Nonblank invalid changes are ignored. A blank sets the rig's DX field to empty but preserves displayed focus/history; returning from blank to a valid call is a change.
- Unchanged callsigns never create selections, even when band/mode changes. Rig-strip telemetry reflects latest Status; history/summary provenance retains the band/mode/frequency/time captured at selection. Sequences resolve arrival ordering even when timestamps tie.
- **A Status change is a practical selection signal, not proof of a physical click. Reselecting an unchanged call can be undetectable.** A Close resets that rig's baseline; after unannounced rig restarts, the previous baseline persists until a meaningful change, Close, or service restart. No heuristic timeout creates extra selections.
- `backend/receiver.py`: receive-only `SO_REUSEADDR` socket, multicast membership on the explicitly configured local IPv4 interface. No `SO_REUSEPORT` load-balancing, outbound UDP packets, acknowledgements or radio control. Join/receive failures are visible through snapshots; “listening” means the socket joined, not that station traffic has been verified.
- `backend/app.py`: FastAPI lifespan owns one receiver task/socket. Run **one worker, without reload**, to avoid independent competing state owners. Shutdown cancels the task and closes its socket. No database is created.
- `src/live.ts` and `src/focus.ts`: complete snapshot applied immediately; independent sample lookups retain generation guards. Known fixture calls may display fictional sample profiles/contacts. Unknown real calls get no invented QSO dataset: profile unavailable, history unavailable, worked status unknown.

## Synchronization contract

`GET /api/snapshot` returns `{epoch, revision, call, source, history, rigs, counters, receiver}`. Times are UTC Unix milliseconds. History is most recent radio selection first, deduplicated by call; entries retain selecting network ID, timestamp, band, mode and frequency. The source is `radio` or `browse`. Receiver status is `disabled`, `listening` or `error`, with the configured group/port/interface.

`GET /api/events` sends SSE `snapshot` events containing complete state. Registration and the initial snapshot are atomic on the event loop. Each client has a one-snapshot queue; a slow client gets the newest complete state instead of unbounded queued events. Up to 32 streams are supported. A comment heartbeat is sent every 15 seconds, caching/proxy buffering is disabled, and disconnect removes the subscriber. The browser also fetches `/api/snapshot` on every EventSource open/reopen. Epoch/revision guards reject older HTTP responses; an authoritative new SSE epoch resets state after a backend restart. Last-Event-ID replay is intentionally unnecessary.

`POST /api/focus` with `{"call":"JA2HDE"}` browses an existing entry centrally. It changes displayed focus (shared across browsers) and separate browsing time only. It never reorders history, changes radio provenance, or sends WSJT-X commands. Missing calls return 404. Same-origin JSON requests are required when an Origin header is supplied; no cross-origin access is enabled. Navigation failures are shown without changing radio history.

The live UI is explicitly selected with **`?mode=live`**; it starts empty and never seeds demo events. Demo mode at `/` retains the accepted local simulation tools and never connects to the backend. Those actions are disabled in the live state layer as well as absent from its UI. In live mode the header identifies receiver/connectivity status plus **Sample profiles/QSOs**, callsigns are labeled **RADIO**, and sample worked/band indicators are explicitly marked. Disconnect keeps last known state with a stale-data/reconnecting notice until a fresh snapshot arrives.

## Installation and development

Use the source-based [Ubuntu installation](install-ubuntu.md): clone, copy/edit `config.toml`, run `./install.sh`, then manage `wsjtx-dashboard` with systemctl. The installer builds the frontend locally on Ubuntu; no release assets or Mac build are required. HTTP and multicast use the single TOML configuration. The service runs one worker as the installation user.

[Mac development](development.md), the [offline demo](demo.md), and [historical validation notes](validation-history.md) are separate from installation. No new feature milestone is included in these deployment changes.

## Offline checks

```sh
.venv/bin/python -m pytest backend/tests -q
npm test
npm run build
npx playwright install chromium
npm run test:e2e
npm run test:e2e:live
```

With this Mac's installed Chrome, prepend `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` to either browser test command.

`test:e2e:live` requires the fresh `dist` build and the repository `.venv`. It starts **`backend.tests.fixture_server`** on loopback port 8001, with UDP disabled, and injects synthetic protocol packets into the actual ingest/state path. Its `/fixture/packet` endpoint exists only in the separate test application, never the production app. Do not deploy that test server or use it on a station network. The browser test uses two isolated contexts, verifies genuinely disconnected state, sends missed updates while one is offline, and confirms a new snapshot request and full synchronization after reconnect. It also verifies central browsing, passive/invalid inputs, deduplication, rig provenance, reload recovery and unknown real-call sample-data limits. This is **offline validation, not observed live multicast reception**.

## Station validation status and remaining acceptance

Observed on the temporary Ubuntu runtime: real multicast reception from both IC7300 and QRPLabsQDX, 261 packets including 156 Decodes, zero malformed packets. An operator-confirmed click on W0PE produced the sole history entry with IC7300/12m/FT8 provenance. This confirms the receiver/state path for that selection, not browser latency, initial empty baselines, or passive-decode stability. The new source-based installer/systemd operation and direct Mac LAN browser access still require station validation.

1. On the new installation, inspect `/api/snapshot` before changing either DX call. First Status from both actual network IDs should appear in Station Desk with empty Focus History. Capture that evidence explicitly.
2. Select a different valid DX call on IC7300 and QRPLabsQDX, plus any additional rig. Confirm immediate focused call/history, correct ID/band/mode/time, deduplication and two-browser updates. Do not change radio configuration for this check.
3. Check ordinary decodes and unchanged/blank DX calls do not steal focus. Browse an old history entry in one client: both display it, order and radio provenance remain unchanged, and WSJT-X itself remains untouched.
4. Disconnect/reconnect one browser and confirm full snapshot recovery. Test observed sender schema, shutdown/restart baseline behavior, and any OS-specific multicast sharing issues.
5. Confirm production WaveLogGate continues its existing operation. This application must never receive authorization to log merely because the receiver works.

Stop after Milestone 2 review. Wavelog read-only access and QRZ enrichment require their own later authorization/verification.
