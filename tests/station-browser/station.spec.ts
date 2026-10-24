import { test, expect } from '@playwright/test'

test('running station receiver reports actual traffic in both browser windows', async ({ browser, request, baseURL }) => {
 const response = await request.get('/api/snapshot')
 const snapshot = await response.json()
 expect(snapshot.step).toBeGreaterThanOrEqual(1)
 expect(snapshot.sample).toBe(false)
 expect(snapshot.receiver.status).toBe('listening')
 expect(snapshot.counters.packets).toBeGreaterThan(0)
 expect(snapshot.rigs.length).toBeGreaterThan(0)
 const a = await browser.newContext(), b = await browser.newContext()
 const first = await a.newPage(), second = await b.newPage()
 await first.goto(baseURL!); await second.goto(baseURL!)
 for (const page of [first, second]) {
  if (snapshot.call) await expect(page.getByTestId('focused-call')).toHaveText(snapshot.call)
  await expect(page.locator('.history-entry')).toHaveCount(snapshot.history.length)
  expect(await page.locator('.history-entry').evaluateAll(entries => entries.map(entry => entry.getAttribute('data-testid')))).toEqual(snapshot.history.map((entry: { call: string }) => `history-${entry.call}`))
 }
 await first.getByRole('button', { name: 'Diagnostics', exact: true }).click()
 await second.getByRole('button', { name: 'Diagnostics', exact: true }).click()
 for (const page of [first, second]) {
  await expect(page.locator('.receiver-badge')).toHaveText('listening')
  for (const rig of snapshot.rigs) await expect(page.locator('.instance-table')).toContainText(rig.id)
  await expect(page.locator('.packet-table')).toContainText('10.176.1.')
 }
 await first.screenshot({ path: 'test-results/step1-actual-station.png', fullPage: true })
 await first.getByRole('button', { name: 'Station', exact: true }).click()
  await expect(first.getByRole('button', { name: 'Station', exact: true })).toHaveAttribute('aria-current', 'page')
  if (snapshot.call) await expect(first.getByRole('region', { name: 'Focused station', exact: true })).toBeVisible()
 if (!snapshot.call) await expect(first.getByRole('heading', { name: 'Waiting for a WSJT-X selection' })).toBeVisible()
  if (snapshot.call) await first.getByTestId(`history-${snapshot.call}`).scrollIntoViewIfNeeded()
  if (snapshot.photoUrls?.[snapshot.call]) {
    const photos = first.getByRole('img', { name: `QRZ profile for ${snapshot.call}`, exact: true })
    await expect.poll(() => photos.evaluateAll(images => images.length >= 2 && images.every(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0)), { timeout: 15000 }).toBe(true)
  }
 if (snapshot.call) await first.screenshot({ path: 'test-results/step1-actual-focus.png', fullPage: true })
 if (snapshot.step >= 3) {
   await first.getByRole('button', { name: 'Settings', exact: true }).click()
   await first.getByRole('region', { name: 'Wavelog QSO history', exact: true }).screenshot({ path: 'test-results/step3-actual-wavelog-settings.png' })
 }
 // Read-only check: no settings, focus or radio commands are sent.
 await a.close(); await b.close()
})
