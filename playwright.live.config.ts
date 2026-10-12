import { defineConfig } from '@playwright/test'
export default defineConfig({
 testDir: './tests/live-browser',
 use: { baseURL: 'http://127.0.0.1:8001', viewport: { width: 1920, height: 1080 }, launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } },
 webServer: { command: '.venv/bin/python -m uvicorn backend.tests.fixture_server:app --host 127.0.0.1 --port 8001', url: 'http://127.0.0.1:8001/api/snapshot', reuseExistingServer: false },
})
