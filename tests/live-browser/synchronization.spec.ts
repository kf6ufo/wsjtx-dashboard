import { test, expect } from '@playwright/test'
const uint = (value: number) => { const b = Buffer.alloc(4); b.writeUInt32BE(value); return b }
const text = (value: string) => Buffer.concat([uint(Buffer.byteLength(value)), Buffer.from(value)])
const header = (rig: string, type = 1) => Buffer.concat([uint(0xadbccbda), uint(2), uint(type), text(rig)])
function status(call: string, rig: string, hz = 14074000) {
 const frequency = Buffer.alloc(8); frequency.writeBigUInt64BE(BigInt(hz))
 return Buffer.concat([header(rig), frequency, text('FT8'), text(call), text('-10'), text('FT8'), Buffer.from([0, 0, 1]), uint(1200), uint(1500), text('N0TEST'), text('AA00'), text('PM85')])
}

test('two browsers share radio history and browsing focus, recovering a full snapshot after disconnect', async ({ browser, request }) => {
 const a = await browser.newContext(), b = await browser.newContext()
 const first = await a.newPage(), second = await b.newPage()
 let reconnectSnapshots = 0
 second.on('request', r => { if (new URL(r.url()).pathname === '/api/snapshot') reconnectSnapshots++ })
 const errors: string[] = []
 first.on('pageerror', e => errors.push(e.message)); second.on('pageerror', e => errors.push(e.message))
 const send = async (packet: Buffer) => {
  const response = await request.post('/fixture/packet', { data: { hex: packet.toString('hex') } })
  expect(response.ok()).toBe(true)
 }
 const order = () => first.locator('.history-entry').evaluateAll(cards => cards.map(c => c.getAttribute('data-testid')))
 await first.goto('/?mode=live'); await second.goto('/?mode=live')
 for (const page of [first, second]) {
  await expect(page.getByRole('heading', { name: 'Waiting for a WSJT-X selection' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Demo tools', exact: true })).toHaveCount(0)
  await expect(page.locator('.demo-status')).toContainText('Sample profiles/QSOs')
 }
 await send(status('N0BASE', 'WSJT-X - Alpha'))
 await send(status('N0BASE', 'WSJT-X - Beta', 28074000))
 await expect(first.locator('.history-entry')).toHaveCount(0)
 await send(status(' ja2hde ', 'WSJT-X - Alpha'))
 for (const page of [first, second]) await expect(page.getByTestId('focused-call')).toHaveText('JA2HDE')
 await send(status('DL1DEMO', 'WSJT-X - Beta', 28074000))
 for (const page of [first, second]) await expect(page.getByTestId('focused-call')).toHaveText('DL1DEMO')
 const before = await order()
 const provenance = await first.getByTestId('history-JA2HDE').locator('.history-rig').textContent()
 await first.getByTestId('history-JA2HDE').click()
 await expect(second.getByTestId('focused-call')).toHaveText('JA2HDE')
 expect(await order()).toEqual(before)
 await expect(second.getByTestId('history-JA2HDE')).toHaveAttribute('aria-pressed', 'true')
 const decode = Buffer.concat([header('WSJT-X - Alpha', 2), Buffer.from([1]), uint(12345000), Buffer.from('fffffff40000000000000000000004b0', 'hex'), text('~'), text('CQ ZS6DEMO AA00')])
 await send(decode)
 await send(status('DL1DEMO', 'WSJT-X - Beta')) // Unchanged call, changed band: no selection.
 await send(status('', 'WSJT-X - Alpha'))
 await send(Buffer.from('broken'))
 expect(await order()).toEqual(before)
 for (const page of [first, second]) await expect(page.getByTestId('focused-call')).toHaveText('JA2HDE')
 await expect(second.locator('tbody tr')).toHaveCount(24)
 await second.screenshot({ path: 'test-results/live-fixture-desktop.png', fullPage: true })
 // Block/re-establish a real EventSource connection; missed updates are not replayed.
 const snapshotRequestsBefore = reconnectSnapshots
 await b.setOffline(true)
 await expect(second.locator('.connection-note')).toBeVisible({ timeout: 15000 })
 await send(status('W7DEMO', 'WSJT-X - Beta'))
 await expect(first.getByTestId('focused-call')).toHaveText('W7DEMO')
 await send(status('ZS6DEMO', 'WSJT-X - Alpha', 21074000))
 await expect(first.getByTestId('focused-call')).toHaveText('ZS6DEMO')
 await expect(second.getByTestId('focused-call')).toHaveText('JA2HDE')
 await b.setOffline(false)
 await expect(second.getByTestId('focused-call')).toHaveText('ZS6DEMO', { timeout: 15000 })
 await expect.poll(() => reconnectSnapshots).toBeGreaterThan(snapshotRequestsBefore)
 expect(await second.locator('.history-entry').evaluateAll(cards => cards.map(c => c.getAttribute('data-testid')))).toEqual(await order())
 await send(status('JA2HDE', 'WSJT-X - Beta', 28074000))
 for (const page of [first, second]) {
  await expect(page.locator('.history-entry').first()).toHaveAttribute('data-testid', 'history-JA2HDE')
  await expect(page.getByTestId('history-JA2HDE').locator('.history-rig')).toContainText('Beta')
  await expect(page.locator('.history-entry')).toHaveCount(4)
 }
 expect(await first.getByTestId('history-JA2HDE').locator('.history-rig').textContent()).not.toBe(provenance)
 // Unknown calls must never borrow invented complete sample QSO histories.
 await send(status('K1UNSEEN', 'WSJT-X - Alpha'))
 for (const page of [first, second]) {
  await expect(page.getByTestId('focused-call')).toHaveText('K1UNSEEN')
  await expect(page.getByText('QSO history unavailable · worked-before status unknown')).toBeVisible()
  await expect(page.getByTestId('band-status')).toContainText('Status unavailable')
 }
 await first.reload()
 await expect(first.getByTestId('focused-call')).toHaveText('K1UNSEEN')
 await expect(first.locator('.history-entry')).toHaveCount(5)
 expect(errors).toEqual([])
 await a.close(); await b.close()
})
