import { defineConfig } from '@playwright/test'
export default defineConfig({
 testDir:'./tests/pskreporter-browser', workers:1,
 use:{ baseURL:'http://127.0.0.1:8799', viewport:{width:1600,height:1100}, launchOptions:{ executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } },
 webServer:{ command:'.venv/bin/python scripts/preview-pskreporter.py --port 8799', url:'http://127.0.0.1:8799/api/snapshot', reuseExistingServer:false },
})
