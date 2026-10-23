import { test, expect } from '@playwright/test'

test('running station receiver reports actual traffic in both browser windows', async ({ browser, request, baseURL }) => {
 const response = await request.get('/api/snapshot')
 const snapshot = await response.json()
 expect(snapshot.step).toBe(1)
 expect(snapshot.sample).toBe(false)
 expect(snapshot.receiver.status).toBe('listening')
 expect(snapshot.counters.packets).toBeGreaterThan(0)
 expect(snapshot.rigs.length).toBeGreaterThan(0)
 const a = await browser.newContext(), b = await browser.newContext()
 const first = await a.newPage(), second = await b.newPage()
 await first.goto(baseURL!); await second.goto(baseURL!)
 await first.getByRole('button', { name: 'Diagnostics', exact: true }).click()
 await second.getByRole('button', { name: 'Diagnostics', exact: true }).click()
 for (const page of [first, second]) {
  await expect(page.locator('.receiver-badge')).toHaveText('listening')
  for (const rig of snapshot.rigs) await expect(page.locator('.instance-table')).toContainText(rig.id)
  await expect(page.locator('.packet-table')).toContainText('10.176.1.')
 }
 await first.screenshot({ path: 'test-results/step1-actual-station.png', fullPage: true })
 await first.getByRole('button', { name: 'Station', exact: true }).click()
 if (!snapshot.call) await expect(first.getByRole('heading', { name: 'Waiting for a WSJT-X selection' })).toBeVisible()
 // Read-only check: no settings, focus or radio commands are sent.
 await a.close(); await b.close()
})
