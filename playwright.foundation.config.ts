import { defineConfig } from '@playwright/test'
export default defineConfig({
 testDir: './tests/foundation-browser', workers: 1,
 use: { baseURL: process.env.FOUNDATION_URL || 'http://127.0.0.1:8791', viewport: { width: 1600, height: 1100 }, launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } },
 webServer: process.env.FOUNDATION_URL ? undefined : { command: '.venv/bin/python scripts/test-foundation-server.py', url: 'http://127.0.0.1:8791/api/snapshot', reuseExistingServer: false },
})
