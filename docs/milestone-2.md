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

## Mac development (no radio traffic)

Requires Python **3.11+** and Node **24.15+**. Tested here with Python 3.13.1 and temporary Node 24.21.0. From the repository:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm ci
```

Terminal 1 (UDP disabled explicitly):

```sh
WSJTX_RECEIVER=off .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Terminal 2:

```sh
npm run dev -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/** for the separate demo, or **http://127.0.0.1:5173/?mode=live** for the synchronized UI waiting for radio selections. Vite proxies `/api` to loopback port 8000. “Receiver disabled” is expected; no station has been connected. If Node is still absent from this Mac's PATH, prepend the session runtime with `export PATH="/private/tmp/node-v24.21.0-darwin-arm64/bin:$PATH"`; install Node normally for ongoing use.

A static build can instead be served by FastAPI: run `npm run build`, start the same backend, and open **http://127.0.0.1:8000/?mode=live**. Rebuild after frontend edits. Do not start a second backend on the same port.

## GitHub installation and updates (Ubuntu runtime only)

For a fresh installation, follow **[Install on Ubuntu](install-ubuntu.md)**. It includes identifying/stopping an old dashboard, preserving an existing checkout, prerequisites, GitHub authentication, installation of both backend and prebuilt frontend, verification, and manual operation. The publication and update details below are for maintainers.

Development, builds, checks and Codex stay on **macOS**. GitHub transfers committed source and a matching **prebuilt frontend release asset**. Ubuntu runs Python only; it needs neither Node nor a ChatGPT/Codex app. Never copy the Mac virtual environment. The former temporary archive workflow is retired; retain its files for now.

### Mac: publish a checked version

Run the offline checks below, then commit and push source to `origin/main`. With a clean working tree and Node available, run:

```sh
python3 scripts/package-frontend.py
```

This builds `dist`, writes its exact source commit to `dist/frontend.json`, and prints the temporary `frontend.tar.gz` path and SHA-256. Publish those two asset files (`frontend.tar.gz` and `frontend.tar.gz.sha256`) on a GitHub release targeting that exact commit. Build outputs remain ignored and are never committed. Example (replace the asset directory, tag and full commit with the packaging result):

```sh
gh release create RELEASE_TAG /path/to/frontend.tar.gz /path/to/frontend.tar.gz.sha256 \
  --repo kf6ufo/wsjtx-dashboard --target FULL_COMMIT --prerelease \
  --title "Milestone 2 validation" --notes "Receive-only radio focus; sample profiles/QSOs. Station acceptance remains in progress."
```

Every update gets a **new tag** and new matching frontend assets; do not replace published assets or move tags. The release target and `git rev-parse HEAD` identify the exact source revision; a commit cannot contain its own hash. The current validation release is **`m2-validation-20261012`**. Its exact commit and published asset checksum are recorded in GitHub release notes and the delivery message. Release publication must succeed before Ubuntu installation.

### Ubuntu: stop the temporary dashboard first

The temporary dashboard was started in the foreground as Uvicorn PID **60357**, from `/home/jerry/wsjtx-m2-validation.JrNjUo/wsjtx-dashboard`, bound to `127.0.0.1:8000`. In that original terminal press **Ctrl+C** and wait for shutdown. PID numbers can change/reuse: do not blindly kill 60357. If the terminal is unavailable, inspect `ss -ltnp '( sport = :8000 )'` and verify the current PID's working directory before using `kill -TERM` on that dashboard process only. Confirm port 8000 is free afterward.

The separate `/home/jerry/Downloads/wsjtx_focus_probe.py` (previously PID 17225) is **not** the dashboard and can stay running. Keep WaveLogGate and every existing radio/service configuration unchanged. Do not remove temporary validation files.

### Ubuntu: first installation

Use stable directory **`/home/jerry/wsjtx-dashboard`**. First check whether it already exists; if so inspect it before proceeding, never overwrite or delete it. Requirements: Python 3.12 (already observed), `python3-venv` (already worked), Git and GitHub CLI (`gh`). Check `git --version` and `gh --version`; if missing, install only these prerequisites using `sudo apt install git gh python3-venv`. The private repository requires GitHub access: run `gh auth login --hostname github.com --git-protocol https --web`, complete device authentication in a Mac browser, then `gh auth setup-git`. Never paste credentials into chat or put them in clone URLs. Existing authorized GitHub access can be reused.

Once the directory is confirmed absent and the temporary dashboard is stopped:

```sh
git clone https://github.com/kf6ufo/wsjtx-dashboard.git /home/jerry/wsjtx-dashboard
cd /home/jerry/wsjtx-dashboard
python3 scripts/install-ubuntu.py m2-validation-20261012
```

The installer refuses a dirty/unexpected checkout or occupied HTTP port. It fetches the explicit tag, downloads the matching frontend assets through authenticated GitHub CLI, checks the checksum and embedded commit, rejects unsafe archive paths/links, checks out the exact commit, creates a local `.venv`, installs Python requirements, and installs `dist`. It never starts/stops services, uses git reset/clean, changes radios/firewalls, or accesses Wavelog/QRZ. Failed installation must be resolved before starting; no backend-only installation is considered complete. All changes are confined to this dedicated checkout. `git rev-parse HEAD` records the installed revision. The installed frontend's embedded revision must match it.

### Ubuntu: manual start and stop

```sh
cd /home/jerry/wsjtx-dashboard
./scripts/start-station.sh
```

Leave that terminal running. **Ctrl+C in the same terminal stops only this dashboard.** No systemd service or automatic startup is installed. The launcher verifies frontend/source revisions and uses one Uvicorn worker, without reload, with explicit multicast configuration `WSJTX_RECEIVER=on WSJTX_GROUP=239.255.0.73 WSJTX_PORT=2238 WSJTX_INTERFACE=10.176.1.6`.

HTTP binds specifically to **10.176.1.6:8000**, not all interfaces. On the **Mac**, open **http://10.176.1.6:8000/?mode=live** directly over the trusted LAN; Ubuntu browsers can use that same URL. No SSH tunnel, router port forwarding or public exposure is required. This is unauthenticated plain HTTP intended only for the trusted station LAN. Existing firewall policy is not changed by these scripts; if Mac access fails, inspect it before proposing any narrow LAN-only rule. Do not disable the firewall or open a router port.

To inspect reception on **Ubuntu** while it runs, use a second terminal:

```sh
curl -fsS http://10.176.1.6:8000/api/snapshot | python3 -m json.tool
```

Configuration in the backend remains opt-in: `WSJTX_RECEIVER=off|on` (default off), group239.255.0.73, port2238, and an explicit local interface required when enabled. The station launcher intentionally supplies the known Ubuntu configuration. The Mac development commands above remain loopback-only with UDP disabled.

### Ubuntu: repeatable updates

After a new version is checked, committed, pushed and released **on the Mac**, stop the dashboard with Ctrl+C. In its dedicated Ubuntu checkout:

```sh
cd /home/jerry/wsjtx-dashboard
git status --short
git fetch origin main
git merge --ff-only origin/main
python3 scripts/install-ubuntu.py NEW_RELEASE_TAG
git rev-parse HEAD
./scripts/start-station.sh
```

Replace `NEW_RELEASE_TAG` with the newly published tag; do not type it literally. If Git reports local modifications or a non-fast-forward update, stop and inspect; never discard station files. The checkout is normally detached at the installed release; the fast-forward updates installer/source before pinning the next explicit release. Keep previous release tags for rollback using the same installer with the previous tag while stopped. No temporary validation folders are removed. Focus/history is memory-only and resets on every receiver restart, establishing fresh per-rig baselines.

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

Observed on the temporary Ubuntu runtime: real multicast reception from both IC7300 and QRPLabsQDX, 261 packets including 156 Decodes, zero malformed packets. An operator-confirmed click on W0PE produced the sole history entry with IC7300/12m/FT8 provenance. This confirms the receiver/state path for that selection, not browser latency, initial empty baselines, or passive-decode stability. The new GitHub installation and direct Mac LAN browser access still require station validation.

1. On the new installation, inspect `/api/snapshot` before changing either DX call. First Status from both actual network IDs should appear in Station Desk with empty Focus History. Capture that evidence explicitly.
2. Select a different valid DX call on IC7300 and QRPLabsQDX, plus any additional rig. Confirm immediate focused call/history, correct ID/band/mode/time, deduplication and two-browser updates. Do not change radio configuration for this check.
3. Check ordinary decodes and unchanged/blank DX calls do not steal focus. Browse an old history entry in one client: both display it, order and radio provenance remain unchanged, and WSJT-X itself remains untouched.
4. Disconnect/reconnect one browser and confirm full snapshot recovery. Test observed sender schema, shutdown/restart baseline behavior, and any OS-specific multicast sharing issues.
5. Confirm production WaveLogGate continues its existing operation. This application must never receive authorization to log merely because the receiver works.

Stop after Milestone 2 review. Wavelog read-only access and QRZ enrichment require their own later authorization/verification.
