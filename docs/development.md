# Development and checks

The installed production path is [native macOS](install-macos.md) / [Ubuntu](install-ubuntu.md). For development, first run `./install.sh`. The backend still owns workspace state:

```sh
.venv/bin/python -m backend.server
```

For hot reload, in another terminal:

```sh
npm run dev -- --port 5173 --strictPort
```

Vite proxies `/api` to loopback **8787**. Open http://127.0.0.1:5173/. The installed server at http://127.0.0.1:8787/ always serves `dist`. An explicitly isolated historical tab-local demo is still available at `/?mode=demo` for regression checks; it is not the shared installed workspace. Legacy radio/parser tests remain offline and do not authorize Step 1.

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest backend/tests -q
npm test
npm run build
npx playwright install chromium
npm run test:e2e
npm run test:e2e:foundation
```

Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` when using installed macOS Chrome. The foundation browser suite runs the real installed server against a temporary config/database and production build. See the checkpoint for actual results. The old `test:e2e:live` command tests synthetic receiver packets against the dormant predecessor transport, not Step 0 or real radio reception.
