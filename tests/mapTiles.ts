import type { Page } from '@playwright/test'

/** Browser workflows use an offline vector style, never the public tile service. */
export async function mockMapTiles(page: Page) {
 await page.route('https://tiles.openfreemap.org/**', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ version: 8, sources: {}, layers: [{ id: 'fixture-background', type: 'background', paint: { 'background-color': '#dce8e4' } }] }) }))
}
