# Development and checks

The installed production path is [native macOS](install-macos.md) / [Ubuntu](install-ubuntu.md). For development, first run `./install.sh`. The backend still owns workspace state:

```sh
.venv/bin/python -m backend.server
```

For hot reload, in another terminal:

```sh
npm run dev -- --port 5173 --strictPort
```

Vite proxies `/api` to loopback **8787**. Open http://127.0.0.1:5173/. The installed server at http://127.0.0.1:8787/ always serves `dist`. An isolated tab-local frontend fixture demo is still available at `/?mode=demo` for regression checks; it is not the shared installed workspace. Radio/parser fixtures remain offline; loopback UDP tests use isolated ports. No automated test transmits to station multicast.

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest backend/tests -q
npm test
npm run build
npx playwright install chromium
npm run test:e2e
npm run test:e2e:foundation
npm run test:e2e:receiver
npm run test:e2e:enrichment
npm run test:e2e:wavelog
```

Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` when using installed macOS Chrome. The foundation browser suite runs the real installed server against a temporary config/database and production build. See the checkpoint for actual results. The receiver browser suite starts the installed entry point with loopback UDP 18238 and HTTP 8792; it sends synthetic protocol fixtures through an actual UDP socket. This validates socket/parse/state/browser behavior, not real WSJT-X or multicast.

Optional read-only actual station check (requires the running receiver and real traffic):

```sh
STATION_URL=http://127.0.0.1:8787 npm run test:e2e:station
```

This check reads actual station diagnostics in two browser windows without changing configuration or focus. It does not substitute for an operator changing the DX Call in WSJT-X. Its current source assertion targets the observed 10.176.1.x station LAN; adapt it for another LAN.

The enrichment browser suite uses HTTP 8793, isolated loopback UDP 18239 and a temporary country-file fixture. It checks shared enrichment, settings, missing QRZ credentials, history provenance and layout. Provider unit tests use the actual pyhamtools parser with offline country/Club Log XML data and mocked QRZ/Club Log HTTP responses; they require no account and do not establish live subscription access. See [Step 2](step-2.md).

The Wavelog browser workflow uses HTTP 8794 and loopback UDP 18240 with a temporary config/database. All Wavelog responses are offline fixtures; it exercises pagination, two station callsigns, incomplete/empty/loaded results, read-only details, delayed focus changes, two browsers, settings, scope selection and mobile width. Unit tests cover API error handling, pagination inconsistencies, safety limits, credentials and independent worker behavior. These tests do not use production tokens or establish live authenticated Wavelog access.


## Optional history/delivery extension

Run `npm run test:e2e:qso` for the isolated ADIF-only browser workflow (HTTP 8797 / loopback UDP 18241). It creates a temporary synthetic file, never uses station multicast or an operator log, and checks incomplete coverage, opt-in writes, duplicate suppression and cross-browser updates. `backend/tests/test_qso_architecture.py` covers provider and delivery contracts, 10,000 indexed contacts, append interruption, destination independence, persistent uncertain outcomes and automatic history recovery. The Python ADIF dependency is pinned in `requirements.lock`. See [the extension guide](qso-services.md) for acceptance limits and the required isolated real-Wavelog test.
