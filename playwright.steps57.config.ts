import { defineConfig } from '@playwright/test'
export default defineConfig({
 testDir: './tests/steps57-browser', workers: 1, timeout: 60000,
 use: { baseURL: 'http://127.0.0.1:8796', viewport: { width: 1600, height: 1100 }, launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } },
 webServer: { command: '.venv/bin/python scripts/test-steps57-server.py', url: 'http://127.0.0.1:8796/api/snapshot', reuseExistingServer: false },
})
