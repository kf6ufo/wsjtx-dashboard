import { test, expect, type Request } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mockMapTiles } from '../mapTiles'

// All radio events go to the isolated fixture socket; never station multicast.
function status(call: string) {
 execFileSync('.venv/bin/python', ['-c', `import socket\nfrom backend.tests.fixtures import status\ns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\ns.sendto(status(call='${call}',rig='Recovery fixture'),('127.0.0.1',18238))\ns.close()`])
}

test('recovers a silently stalled open stream, page resume and a stalled diagnostics request without a reload', async ({ browser, request, baseURL }) => {
 const context = await browser.newContext(), page = await context.newPage()
 await mockMapTiles(page)
 const errors: string[] = []
 page.on('pageerror', error => errors.push(error.message))
 let snapshotRequests = 0
 const pendingSnapshots = new Set<Request>()
 page.on('request', request => {
  if (new URL(request.url()).pathname === '/api/snapshot') { snapshotRequests++; pendingSnapshots.add(request) }
 })
 page.on('requestfinished', request => pendingSnapshots.delete(request))
 page.on('requestfailed', request => pendingSnapshots.delete(request))
 await page.addInitScript(() => {
  const Native = window.EventSource
  const control = { pauseSnapshots: false, connections: 0, opened: 0 }
  Object.assign(window, { recoveryFixture: control })
  // Keep the real connection OPEN but suppress application snapshot callbacks.
  window.EventSource = class extends Native {
   constructor(url: string | URL, options?: EventSourceInit) {
    super(url, options); control.connections++
    this.addEventListener('open', () => { control.opened++ })
   }
   override addEventListener(type: string, callback: EventListenerOrEventListenerObject | null, options?: boolean | AddEventListenerOptions) {
    if (type !== 'snapshot' || !callback) { super.addEventListener(type, callback, options); return }
    super.addEventListener(type, event => {
     if (control.pauseSnapshots) return
     if (typeof callback === 'function') callback.call(this, event)
     else callback.handleEvent(event)
    }, options)
   }
  }
 })
 try {
  await page.goto(baseURL!)
  status('N0BASE')
  await expect.poll(async () => (await (await request.get('/api/snapshot')).json()).rigs.length).toBe(1)
  status('K1REC')
  await expect(page.getByTestId('focused-call')).toHaveText('K1REC')
  const original = await (await request.get('/api/snapshot')).json()
  const connections = await page.evaluate(() => (window as unknown as { recoveryFixture: { connections: number } }).recoveryFixture.connections)
  await page.evaluate(() => { (window as unknown as { recoveryFixture: { pauseSnapshots: boolean } }).recoveryFixture.pauseSnapshots = true })
  status('K2REC')
  await expect.poll(async () => (await (await request.get('/api/snapshot')).json()).call).toBe('K2REC')
  expect(await page.getByTestId('focused-call').textContent()).toBe('K1REC')
  // No online/offline/error/visibility event occurs. The freshness timer must act.
  await expect(page.getByTestId('focused-call')).toHaveText('K2REC', { timeout: 45000 })
  await expect.poll(() => page.evaluate(() => (window as unknown as { recoveryFixture: { connections: number } }).recoveryFixture.connections)).toBeGreaterThan(connections)
  await expect.poll(() => page.evaluate(() => (window as unknown as { recoveryFixture: { opened: number } }).recoveryFixture.opened)).toBeGreaterThan(connections)
  await expect.poll(() => pendingSnapshots.size).toBe(0)

  status('K3REC')
  await expect.poll(async () => (await (await request.get('/api/snapshot')).json()).call).toBe('K3REC')
  expect(await page.getByTestId('focused-call').textContent()).toBe('K2REC')
  const checksBeforeResume = snapshotRequests
  await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })))
  await expect.poll(() => snapshotRequests).toBeGreaterThan(checksBeforeResume)
  await expect(page.getByTestId('focused-call')).toHaveText('K3REC')
  await page.evaluate(() => { (window as unknown as { recoveryFixture: { pauseSnapshots: boolean } }).recoveryFixture.pauseSnapshots = false })
  status('K4REC')
  await expect(page.getByTestId('focused-call')).toHaveText('K4REC')

  let polls = 0, release!: () => void
  const stalled = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/diagnostics', async route => {
   if (route.request().method() === 'GET' && ++polls === 1) {
    await stalled
    try { await route.continue() } catch { /* The request should already be aborted. */ }
   } else await route.continue()
  })
  try {
   await page.getByRole('button', { name: 'Diagnostics', exact: true }).click()
   await expect(page.getByLabel('Browser update status')).toContainText('Last browser check:')
   await expect(page.getByLabel('Browser update status')).not.toContainText('Waiting for server data')
   status('K5REC')
   await expect.poll(() => polls, { timeout: 16000 }).toBeGreaterThan(1)
   await expect(page.locator('.packet-table')).toContainText('K5REC')
  } finally { release() }
  const final = await (await request.get('/api/snapshot')).json()
  expect(final.epoch).toBe(original.epoch)
  expect(final.counters.receiverErrors).toBe(0)
  await page.screenshot({ path: 'test-results/live-recovery-desktop.png', fullPage: true })
  for (const width of [390, 320]) {
   await page.setViewportSize({ width, height: 844 })
   expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
  await page.screenshot({ path: 'test-results/live-recovery-mobile.png', fullPage: true })
  expect(errors).toEqual([])
 } finally { await context.close() }
})
