import type { Page } from '@playwright/test'

/** Browser workflows use clearly labeled fixture tiles, never the public tile service. */
export async function mockMapTiles(page: Page) {
 await page.route('https://tile.openstreetmap.org/**', route => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#dce8e4"/><path d="M0 128h256M128 0v256" stroke="#bccfca"/><text x="20" y="35" fill="#58776d" font-size="12">Offline map fixture</text></svg>' }))
}
