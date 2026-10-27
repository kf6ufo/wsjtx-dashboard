import { defineConfig } from '@playwright/test'
export default defineConfig({
 testDir:'./tests/mapping-browser',workers:1,timeout:45000,
 use:{baseURL:'http://127.0.0.1:8798',viewport:{width:1600,height:1100},launchOptions:{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH}},
 webServer:{command:'.venv/bin/python scripts/test-station-mapping-server.py',url:'http://127.0.0.1:8798/api/snapshot',reuseExistingServer:false},
})
