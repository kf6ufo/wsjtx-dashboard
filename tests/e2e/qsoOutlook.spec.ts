import { test, expect } from '@playwright/test'
import { mockMapTiles } from '../mapTiles'
import type { Snapshot, ReceptionSpot } from '../../src/types'

test('QSO Outlook ring and accessible popup follow local evidence without moving the map', async ({ page }) => {
 const now = Date.UTC(2026, 10, 8, 12)
 const spot: ReceptionSpot = { sender: 'N0CALL', receiver: 'K1FOCUS', grid: 'FN31', band: '20m', frequency: 14074000, mode: 'FT8', snr: -12, heardAt: now - 60000 }
 const snapshot: Snapshot = { epoch: 'outlook-fixture', revision: 1, step: 3, call: 'K1FOCUS', source: 'radio',
  history: [{ call: 'K1FOCUS', rigId: 'Fixture A', stationCall: 'N0CALL', dxGrid: 'FN31', band: '20m', mode: 'FT8', selectedAt: now, recency: 1 }],
  rigs: [], counters: { packets: 5, decodes: 3, malformed: 0 }, receiver: { status: 'disabled', error: null },
  preferences: { title: 'QSO Outlook · fictional reports', appearance: 'dark', radioStrip: false },
  pskreporter: { config: { enabled: true, callsign: '', window_minutes: 15 }, status: 'connected', error: '', callsigns: ['N0CALL'], connectedAt: now, evicted: 0, spots: [spot] } }
 const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
 await page.clock.install({ time: now })
 await mockMapTiles(page)
 await page.addInitScript(() => {
  window.EventSource = class {
   static CLOSED = 2
   readyState = 1
   onopen?: () => void
   constructor() { setTimeout(() => this.onopen?.(), 25) }
   addEventListener(_name: string, callback: (event: { data: string }) => void) {
    window.addEventListener('outlook-fixture', event => callback({ data: JSON.stringify((event as CustomEvent).detail) }))
   }
   close() { this.readyState = 2 }
  } as unknown as typeof EventSource
 })
 await page.route('**/api/**', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify(snapshot) }))
 await page.goto('/')
 const pin = page.locator('.station-map-pin'), popup = page.getByRole('dialog', { name: 'QSO Outlook details for K1FOCUS', exact: true })
 const push = async () => { snapshot.revision++; await page.evaluate(data => window.dispatchEvent(new CustomEvent('outlook-fixture', { detail: data })), snapshot) }
 await expect(pin).toHaveAttribute('data-outlook-score', '90')
 await expect(pin).toHaveAttribute('data-outlook', 'green')
 await expect(page.locator('.station-map-focus-heard')).toContainText('Heard you: Confirmed')
 await expect(page.locator('.station-map-reception')).toHaveCount(1)
 // The inner amber dot opens the same popup as the surrounding pin.
 const position = await pin.getAttribute('style'), zoom = await page.locator('.station-map-canvas').getAttribute('data-zoom')
 await page.locator('.station-map-reception').click()
 await expect(popup).toBeVisible()
 await expect(popup).toBeFocused()
 await expect(pin).toHaveAttribute('aria-expanded', 'true')
 await expect(popup).toContainText('K1FOCUS · 20m FT8')
 await expect(popup).toContainText('QSO Outlook: 90/100 — Favorable')
 await expect(popup).toContainText('Direct reception: Confirmed')
 await expect(popup).toContainText('Nearest receiver: <1 km')
 await expect(popup).toContainText('Latest reception: 1 minute ago')
 expect(await pin.getAttribute('style')).toBe(position)
 expect(await page.locator('.station-map-canvas').getAttribute('data-zoom')).toBe(zoom)
 await popup.press('Escape'); await expect(pin).toBeFocused()
 await pin.press('Enter'); await expect(popup).toBeVisible()
 await page.getByRole('button', { name: 'Close QSO Outlook' }).click()
 await pin.press('Space'); await expect(popup).toBeVisible()
 await page.clock.fastForward(5 * 60000)
 await expect(pin).toHaveAttribute('data-outlook-score', '80')
 await expect(popup).toContainText('Latest reception: 6 minutes ago')
 await page.getByLabel('Reception time window').selectOption('5')
 await expect(pin).toHaveAttribute('data-outlook', 'gray')
 await expect(popup).toContainText('QSO Outlook: Unknown')
 await page.getByLabel('Reception time window').selectOption('60')
 await page.clock.fastForward(10 * 60000)
 await expect(pin).toHaveAttribute('data-outlook-score', 'unknown')
 await expect(page.locator('.station-map-focus-heard')).toContainText('Heard you: Confirmed')
 await expect(popup).toContainText('outside Outlook evidence')
 // Fresh nearby evidence exercises every ring category and live popup updates.
 const fresh = now + 15 * 60000
 snapshot.pskreporter!.spots = [0, 1, 2].map(i => ({ ...spot, receiver: `K${i + 2}NEAR`, grid: 'FN32', heardAt: fresh }))
 await push()
 await expect(pin).toHaveAttribute('data-outlook-score', '75')
 await expect(popup).toContainText('Nearby receivers: 3 within 200 km')
 await expect(popup).toContainText('Nearest receiver: 111 km')
 await expect(popup).toContainText('Direct reception: Not confirmed')
 await expect(page.locator('.station-map-focus-heard')).toHaveCount(0)
 await page.locator('.station-map').screenshot({ path: 'test-results/qso-outlook-favorable-dark.png' })
 snapshot.pskreporter!.spots.pop(); await push()
 await expect(pin).toHaveAttribute('data-outlook-score', '60')
 await expect(pin).toHaveAttribute('data-outlook', 'yellow')
 snapshot.pskreporter!.spots = [{ ...spot, receiver: 'K2NEAR', grid: 'FN34', heardAt: fresh }]; await push()
 await expect(pin).toHaveAttribute('data-outlook-score', '35')
 await expect(pin).toHaveAttribute('data-outlook', 'red')
 expect(await pin.evaluate(node => getComputedStyle(node, '::after').borderTopColor)).toBe('rgb(223, 85, 85)')
 // Popup stays inside even a narrow map, with all explanatory text scrollable.
 snapshot.preferences!.appearance = 'light'; await push()
 await page.setViewportSize({ width: 320, height: 700 })
 await popup.locator('small').scrollIntoViewIfNeeded()
 const box = await popup.boundingBox(), surface = await page.locator('.station-map-surface').boundingBox()
 expect(box!.x).toBeGreaterThanOrEqual(surface!.x)
 expect(box!.x + box!.width).toBeLessThanOrEqual(surface!.x + surface!.width)
 expect(box!.height).toBeLessThan(surface!.height)
 expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
 await popup.screenshot({ path: 'test-results/qso-outlook-limited-light-mobile.png' })
 await page.setViewportSize({ width: 1600, height: 1100 })
 await page.getByRole('button', { name: 'Close QSO Outlook' }).click()
 const canvas = await page.locator('.station-map-canvas').boundingBox()
 await page.mouse.move(canvas!.x + canvas!.width / 2, canvas!.y + canvas!.height / 2)
 await page.mouse.down(); await page.mouse.move(canvas!.x + canvas!.width / 2 + 70, canvas!.y + canvas!.height / 2 + 30, { steps: 10 }); await page.mouse.up()
 await page.waitForTimeout(500)
 const panned = await pin.getAttribute('style')
 snapshot.pskreporter!.spots.push({ ...spot, receiver: 'K3NEAR', grid: 'FN32', heardAt: fresh }); await push()
 await expect(pin).toHaveAttribute('data-outlook-score', '60')
 expect(await pin.getAttribute('style')).toBe(panned)
 snapshot.pskreporter!.status = 'reconnecting'; snapshot.pskreporter!.error = 'Fictional outage'; await push()
 await expect(pin).toHaveAttribute('data-outlook-score', '60')
 snapshot.pskreporter!.spots = []; await push()
 await expect(pin).toHaveAttribute('data-outlook-score', 'unknown')
 snapshot.pskreporter!.spots = [{ ...spot, heardAt: fresh }]; snapshot.pskreporter!.config.enabled = false; await push()
 await expect(pin).toHaveAttribute('data-outlook-score', 'unknown')
 snapshot.pskreporter!.config.enabled = true; snapshot.pskreporter!.status = 'connected'; snapshot.pskreporter!.error = ''; await push()
 await expect(pin).toHaveAttribute('data-outlook-score', '90')
 snapshot.history[0]!.band = '17m'; await push()
 await expect(pin).toHaveAttribute('data-outlook-score', 'unknown')
 snapshot.history[0]!.band = '20m'; snapshot.history[0]!.stationCall = 'N0CALL/P'; await push()
 await expect(pin).toHaveAttribute('data-outlook-score', 'unknown')
 snapshot.history[0]!.stationCall = 'N0CALL'; await push()
 await pin.focus(); await pin.press('Enter'); await expect(popup).toBeVisible()
 snapshot.call = 'K2FOCUS'; snapshot.history[0]!.call = 'K2FOCUS'; snapshot.history[0]!.dxGrid = 'FN32'; await push()
 await expect(popup).toHaveCount(0)
 await expect(pin).toHaveAttribute('data-outlook-score', '60')
 await expect(pin).toHaveAttribute('aria-label', /Station location for K2FOCUS/)
 snapshot.history[0]!.dxGrid = ''; await push()
 await expect(pin).toHaveCount(0)
 await expect(page.locator('.station-map-empty')).toContainText('QSO Outlook: Unknown')
 expect(errors).toEqual([])
})
