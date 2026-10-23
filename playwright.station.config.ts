import { defineConfig } from '@playwright/test'
export default defineConfig({
 testDir: './tests/station-browser', workers: 1,
 use: { baseURL: process.env.STATION_URL || 'http://127.0.0.1:8789', viewport: { width: 1600, height: 1100 }, launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } },
})
