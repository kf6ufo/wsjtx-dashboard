# Mac development

Development and Codex stay on macOS. Ubuntu source installation is documented separately in [Install on Ubuntu](install-ubuntu.md).

## Frontend development

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


## Python backend (UDP disabled)

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
WSJTX_RECEIVER=off .venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Vite proxies `/api` to this backend. Use `http://127.0.0.1:5173/?mode=live` for synchronized fixture-free live mode waiting for events, or `/` for the separate [offline demo](demo.md). The installed Ubuntu service uses `config.toml`; these developer commands keep UDP explicitly disabled.

## Checks

```sh
.venv/bin/python -m pytest backend/tests -q
npm test
npm run build
npx playwright install chromium
npm run test:e2e
npm run test:e2e:live
```

For existing macOS Chrome instead of downloading Chromium:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run test:e2e
```

Playwright starts a loopback Vite server if one is not already running. Tests use offline fixtures and never access radio services. Screenshots and build outputs are ignored by Git.
