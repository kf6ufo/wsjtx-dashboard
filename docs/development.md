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
```

Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` when using installed macOS Chrome. The foundation browser suite runs the real installed server against a temporary config/database and production build. See the checkpoint for actual results. The receiver browser suite starts the installed entry point with loopback UDP 18238 and HTTP 8792; it sends synthetic protocol fixtures through an actual UDP socket. This validates socket/parse/state/browser behavior, not real WSJT-X or multicast.

Optional read-only actual station check (requires the running receiver and real traffic):

```sh
STATION_URL=http://127.0.0.1:8787 npm run test:e2e:station
```

This check reads actual station diagnostics in two browser windows without changing configuration or focus. It does not substitute for an operator changing the DX Call in WSJT-X. Its current source assertion targets the observed 10.176.1.x station LAN; adapt it for another LAN.

The enrichment browser suite uses HTTP 8793, isolated loopback UDP 18239 and a temporary country-file fixture. It checks shared enrichment, settings, missing QRZ credentials, history provenance and layout. Provider unit tests use the actual pyhamtools parser with offline country/Club Log XML data and mocked QRZ/Club Log HTTP responses; they require no account and do not establish live subscription access. See [Step 2](step-2.md).
