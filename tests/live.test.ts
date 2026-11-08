import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDashboard } from '../src/focus'
import { connectLive } from '../src/live'
import { mockProviders } from '../src/providers'
import { profiles, sampleQsos } from '../src/fixtures'
import type { Snapshot } from '../src/types'
const snapshot = (revision: number, call = 'JA2HDE'): Snapshot => ({
 epoch: 'server-one', revision, call, source: 'radio',
 history: [{ call, rigId: 'new-radio', band: '20m', mode: 'FT4', selectedAt: 100, recency: revision }],
 rigs: [{ id: 'new-radio', name: 'New radio', band: '20m', mode: 'FT4', color: '#70c9bd', call, frequency: 14080000, lastSeen: 100, online: true }],
 counters: { decodes: 0, malformed: 0 }, receiver: { status: 'disabled', error: null },
})

class FakeEventSource {
 static CLOSED = 2
 static instances: FakeEventSource[] = []
 readyState = 0
 onopen: ((event: Event) => void) | null = null
 onerror: ((event: Event) => void) | null = null
 private listener?: (event: MessageEvent) => void
 close = vi.fn(() => { this.readyState = FakeEventSource.CLOSED })
 constructor(readonly url: string) { FakeEventSource.instances.push(this) }
 addEventListener(_name: string, listener: (event: MessageEvent) => void) { this.listener = listener }
 open() { this.readyState = 1; this.onopen?.(new Event('open')) }
 snapshot(value: Snapshot) { this.listener?.(new MessageEvent('snapshot', { data: JSON.stringify(value) })) }
 fail(closed = false) { this.readyState = closed ? FakeEventSource.CLOSED : 0; this.onerror?.(new Event('error')) }
}

const wireSnapshot = (revision: number, call = 'JA2HDE', epoch = 'server-one'): Snapshot => ({
 ...snapshot(revision, call), epoch, step: 1, sample: false,
})
const reply = (value: Snapshot) => new Response(JSON.stringify(value))

describe('browser live connection recovery', () => {
 let fetcher: ReturnType<typeof vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>>
 let online = true
 let visibility: DocumentVisibilityState = 'visible'
 let cleanups: (() => void)[]

 beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(0)
  online = true; visibility = 'visible'; cleanups = []
  FakeEventSource.instances = []
  fetcher = vi.fn(async () => reply(wireSnapshot(1)))
  vi.stubGlobal('fetch', fetcher)
  vi.stubGlobal('EventSource', FakeEventSource)
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online)
  vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visibility)
 })
 afterEach(async () => {
  cleanups.forEach(dispose => dispose())
  await vi.advanceTimersByTimeAsync(0)
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
 })

 function start(value = wireSnapshot(1)) {
  const dashboard = createDashboard(undefined, true)
  const dispose = connectLive(dashboard)
  cleanups.push(dispose)
  const source = FakeEventSource.instances.at(-1)!
  source.open(); source.snapshot(value)
  return { dashboard, source, dispose }
 }

 it('repairs a frozen OPEN stream from HTTP and replaces it without waiting for a socket error', async () => {
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(0)
  fetcher.mockResolvedValue(reply(wireSnapshot(5, 'DL1DEMO')))
  await vi.advanceTimersByTimeAsync(30_000)
  expect(dashboard.state.call).toBe('DL1DEMO')
  expect(dashboard.state.lastServerUpdateAt).toBe(30_000)
  expect(source.close).toHaveBeenCalledOnce()
  expect(FakeEventSource.instances).toHaveLength(2)
  source.snapshot(wireSnapshot(99, 'W7DEMO'))
  source.open()
  expect(dashboard.state.call).toBe('DL1DEMO')
  expect(fetcher).toHaveBeenCalledTimes(2)
 })

 it('checks an idle station without reconnecting or claiming a receiver failure', async () => {
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(120_000)
  expect(fetcher).toHaveBeenCalledTimes(5)
  expect(FakeEventSource.instances).toHaveLength(1)
  expect(source.close).not.toHaveBeenCalled()
  expect(dashboard.state.connection).toBe('connected')
  expect(dashboard.state.lastServerUpdateAt).toBe(120_000)
  expect(dashboard.state.counters.decodes).toBe(0)
 })

 it('does not repeatedly reconnect when only HTTP confirms an unchanged quiet snapshot', async () => {
  const dashboard = createDashboard(undefined, true)
  cleanups.push(connectLive(dashboard))
  const source = FakeEventSource.instances[0]!
  source.open()
  await vi.advanceTimersByTimeAsync(120_000)
  expect(fetcher).toHaveBeenCalledTimes(5)
  expect(source.close).not.toHaveBeenCalled()
  expect(FakeEventSource.instances).toHaveLength(1)
  expect(dashboard.state.lastServerUpdateAt).toBe(120_000)
  expect(dashboard.state.connection).toBe('connected')
 })

 it('uses fresh stream snapshots to defer checks and ignores an older HTTP revision', async () => {
  let finish!: (response: Response) => void
  fetcher.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(1_000)
  source.snapshot(wireSnapshot(2, 'DL1DEMO'))
  await vi.advanceTimersByTimeAsync(1_000)
  finish(reply(wireSnapshot(1)))
  await vi.advanceTimersByTimeAsync(0)
  expect(dashboard.state.call).toBe('DL1DEMO')
  expect(dashboard.state.lastServerUpdateAt).toBe(1_000)
  await vi.advanceTimersByTimeAsync(27_000)
  source.snapshot(wireSnapshot(3, 'W7DEMO'))
  await vi.advanceTimersByTimeAsync(1_000)
  expect(fetcher).toHaveBeenCalledOnce()
  expect(dashboard.state.lastServerUpdateAt).toBe(29_000)
 })

 it.each(['focus', 'pageshow', 'online', 'visibilitychange'])('revalidates immediately on %s', async event => {
  const { dashboard } = start()
  await vi.advanceTimersByTimeAsync(1_000)
  fetcher.mockResolvedValue(reply(wireSnapshot(2, 'DL1DEMO')))
  if (event === 'visibilitychange') document.dispatchEvent(new Event(event))
  else window.dispatchEvent(new Event(event))
  await vi.advanceTimersByTimeAsync(0)
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(dashboard.state.call).toBe('DL1DEMO')
  expect(dashboard.state.lastServerUpdateAt).toBe(1_000)
 })

 it('coalesces resume checks and bounds a stuck HTTP request, then recovers on the next check', async () => {
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(0)
  let finish!: (response: Response) => void
  fetcher.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  await vi.advanceTimersByTimeAsync(30_000)
  const signal = fetcher.mock.calls[1]![1]!.signal!
  window.dispatchEvent(new Event('focus'))
  window.dispatchEvent(new Event('pageshow'))
  document.dispatchEvent(new Event('visibilitychange'))
  await vi.advanceTimersByTimeAsync(5_000)
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(signal.aborted).toBe(false)
  await vi.advanceTimersByTimeAsync(3_000)
  expect(signal.aborted).toBe(true)
  expect(dashboard.state.connection).toBe('disconnected')
  expect(dashboard.state.lastServerUpdateAt).toBe(0)
  finish(reply(wireSnapshot(99, 'W7DEMO')))
  await vi.advanceTimersByTimeAsync(0)
  expect(dashboard.state.call).toBe('JA2HDE')
  fetcher.mockImplementation(async () => reply(wireSnapshot(3, 'DL1DEMO')))
  await vi.advanceTimersByTimeAsync(22_000)
  expect(dashboard.state.call).toBe('DL1DEMO')
  expect(source.close).toHaveBeenCalledOnce()
  const replacement = FakeEventSource.instances.at(-1)!
  replacement.open(); replacement.snapshot(wireSnapshot(3, 'DL1DEMO'))
  await vi.advanceTimersByTimeAsync(0)
  expect(dashboard.state.connection).toBe('connected')
 })

 it('recovers from a failed HTTP response and a closed stream', async () => {
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(0)
  fetcher.mockResolvedValueOnce(new Response('unavailable', { status: 503 }))
  await vi.advanceTimersByTimeAsync(30_000)
  expect(dashboard.state.connection).toBe('disconnected')
  expect(dashboard.state.lastServerUpdateAt).toBe(0)
  source.fail(true)
  await vi.advanceTimersByTimeAsync(30_000)
  expect(FakeEventSource.instances).toHaveLength(2)
  expect(dashboard.state.lastServerUpdateAt).toBe(60_000)
 })

 it('accepts a new backend epoch through HTTP and discards queued events from the replaced stream', async () => {
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(0)
  fetcher.mockImplementation(async () => reply(wireSnapshot(0, 'DL1DEMO', 'server-two')))
  await vi.advanceTimersByTimeAsync(30_000)
  expect(dashboard.state.call).toBe('DL1DEMO')
  expect(source.close).toHaveBeenCalledOnce()
  source.snapshot(wireSnapshot(99, 'W7DEMO'))
  expect(dashboard.state.call).toBe('DL1DEMO')
  const replacement = FakeEventSource.instances.at(-1)!
  replacement.open()
  await vi.advanceTimersByTimeAsync(0)
  expect(FakeEventSource.instances).toHaveLength(2)
  replacement.snapshot(wireSnapshot(1, 'W7DEMO', 'server-two'))
  expect(dashboard.state.call).toBe('W7DEMO')
 })

 it('rejects an old-epoch HTTP response after the stream has observed a backend restart', async () => {
  let finish!: (response: Response) => void
  fetcher.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(1_000)
  source.snapshot(wireSnapshot(0, 'DL1DEMO', 'server-two'))
  await vi.advanceTimersByTimeAsync(1_000)
  finish(reply(wireSnapshot(99, 'W7DEMO')))
  await vi.advanceTimersByTimeAsync(0)
  expect(dashboard.state.call).toBe('DL1DEMO')
  expect(dashboard.state.lastServerUpdateAt).toBe(1_000)
  expect(FakeEventSource.instances).toHaveLength(1)
 })

 it('aborts on offline, resumes online, and ignores hidden visibility events', async () => {
  const { dashboard, source } = start()
  await vi.advanceTimersByTimeAsync(0)
  visibility = 'hidden'
  document.dispatchEvent(new Event('visibilitychange'))
  expect(fetcher).toHaveBeenCalledOnce()
  let finish!: (response: Response) => void
  fetcher.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  window.dispatchEvent(new Event('focus'))
  const signal = fetcher.mock.calls[1]![1]!.signal!
  online = false
  window.dispatchEvent(new Event('offline'))
  expect(signal.aborted).toBe(true)
  expect(source.close).toHaveBeenCalledOnce()
  finish(reply(wireSnapshot(99, 'W7DEMO')))
  await vi.advanceTimersByTimeAsync(0)
  expect(dashboard.state.call).toBe('JA2HDE')
  online = true
  window.dispatchEvent(new Event('online'))
  await vi.advanceTimersByTimeAsync(0)
  expect(FakeEventSource.instances).toHaveLength(2)
  expect(dashboard.state.connection).toBe('connected')
 })

 it('disposes timers, listeners and pending requests without late updates', async () => {
  let finish!: (response: Response) => void
  fetcher.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  const { dashboard, source, dispose } = start()
  const signal = fetcher.mock.calls[0]![1]!.signal!
  dispose()
  expect(signal.aborted).toBe(true)
  expect(vi.getTimerCount()).toBe(0)
  finish(reply(wireSnapshot(99, 'W7DEMO')))
  source.snapshot(wireSnapshot(100, 'DL1DEMO'))
  for (const name of ['online', 'focus', 'pageshow']) window.dispatchEvent(new Event(name))
  document.dispatchEvent(new Event('visibilitychange'))
  await vi.advanceTimersByTimeAsync(60_000)
  expect(fetcher).toHaveBeenCalledOnce()
  expect(FakeEventSource.instances).toHaveLength(1)
  expect(dashboard.state.call).toBe('JA2HDE')
  expect(dashboard.state.connection).toBe('disconnected')
  expect(dashboard.state.lastServerUpdateAt).toBe(0)
 })
})
describe('centrally owned live snapshots', () => {
 it('accepts arbitrary network IDs and ordered revisions, preventing older responses and local simulations', async () => {
  const d = createDashboard({ profile: async c => profiles[c]!, qsos: async c => ({ records: sampleQsos(c), complete: true }) }, true)
  d.applySnapshot(snapshot(2)); d.applySnapshot(snapshot(1, 'DL1DEMO'))
  expect(d.state.call).toBe('JA2HDE')
  d.select('DL1DEMO', 'WSJT-X - IC7300'); d.decode(); d.race()
  expect(d.state.call).toBe('JA2HDE'); expect(d.state.decodes).toBe(0)
  await Promise.resolve()
  expect(d.state.qsos.status).toBe('loaded')
  d.applySnapshot({ ...snapshot(3), source: 'browse' })
  expect(d.state.source).toBe('browse')
  expect(d.state.history[0]).toMatchObject({ rigId: 'new-radio', selectedAt: 100 })
  d.applySnapshot({ ...snapshot(0), epoch: 'server-two', call: '', history: [], rigs: [] })
  expect(d.state.call).toBe('')
  d.applySnapshot(snapshot(99), false) // Old HTTP response after a service restart.
  expect(d.state.call).toBe('')
 })
 it('keeps independent generation guards when later snapshots focus a new station', async () => {
  let finish!: (value: typeof profiles.JA2HDE | null) => void
  const d = createDashboard({ profile: c => c === 'JA2HDE' ? new Promise(resolve => { finish = resolve }) : Promise.resolve(profiles[c]!), qsos: async c => ({ records: sampleQsos(c), complete: true }) }, true)
  d.applySnapshot(snapshot(1)); d.applySnapshot(snapshot(2, 'DL1DEMO'))
  await Promise.resolve(); finish(profiles.JA2HDE!); await Promise.resolve()
  expect(d.state.call).toBe('DL1DEMO')
  expect(d.state.profile).toMatchObject({ status: 'loaded', data: { name: 'Lena Fischer' } })
 })
 it('never displays fixture identities or QSOs for actual Step 1 radio calls, even a catalog match', async () => {
  const d = createDashboard(undefined, true)
  d.applySnapshot({ ...snapshot(1), step: 1, sample: false })
  await Promise.resolve(); await Promise.resolve()
  expect(d.state.profile.status).toBe('empty')
  expect(d.state.qsos).toMatchObject({ status: 'error', message: expect.stringContaining('not connected') })
 })
 it('does not fabricate a sample logbook for a live callsign absent from the catalog', async () => {
  await expect(mockProviders.qsos('K1UNSEEN', 0)).rejects.toThrow('No sample QSO fixture')
 })
 it('fetches each Wavelog result once and discards late HTTP data even after returning to the same call', async () => {
  const pending: ((response: Response) => void)[] = []
  const fetcher = vi.fn(() => new Promise<Response>(resolve => pending.push(resolve)))
  vi.stubGlobal('fetch', fetcher)
  try {
   const d = createDashboard(undefined, true)
   const real = (revision: number, call: string, lookupId: string): Snapshot => ({ ...snapshot(revision, call), step: 3, sample: false,
    wavelog: { config: { enabled: true, url: 'http://fixture.invalid', scope_mode: 'all', station_ids: [], logbook_id: 0, cache_minutes: 5, cache_limit: 20, page_size: 100, max_pages: 100, max_records: 10000, timeout_seconds: 8 },
     connection: { status: 'ready', scopes: [], stations: [], logbooks: [] }, result: { call, lookupId, status: 'loaded', complete: true, recordCount: 1 } } })
   d.applySnapshot(real(1, 'K1ABC', 'old'))
   d.applySnapshot(real(2, 'K1ABC', 'old'))
   expect(fetcher).toHaveBeenCalledTimes(1)
   d.applySnapshot(real(3, 'K2XYZ', 'other'))
   d.applySnapshot(real(4, 'K1ABC', 'new'))
   const response = (lookupId: string) => new Response(JSON.stringify({ call: 'K1ABC', lookupId, complete: true, records: [{ ...sampleQsos('JA2HDE')[0], id: lookupId }] }))
   pending[2]!(response('new'))
   await vi.waitFor(() => expect(d.state.qsos).toMatchObject({ status: 'loaded', data: [{ id: 'new' }] }))
   pending[0]!(response('old'))
   pending[1]!(new Response('error', { status: 500 }))
   await new Promise(resolve => setTimeout(resolve, 0))
   expect(d.state.qsos).toMatchObject({ status: 'loaded', data: [{ id: 'new' }] })
   const disabled = real(5, 'K1ABC', 'disabled')
   disabled.wavelog!.config.enabled = false
   disabled.wavelog!.result = { status: 'disabled', call: '', complete: false }
   d.applySnapshot(disabled)
   expect(d.state.qsos).toMatchObject({ status: 'error', message: expect.stringContaining('History is disabled') })
   expect(fetcher).toHaveBeenCalledTimes(3)
  } finally { vi.unstubAllGlobals() }
 })
 it('uses the generic ADIF result while Wavelog is disabled and rejects a stale provider response', async () => {
  const pending: ((response: Response) => void)[] = []
  const fetcher = vi.fn(() => new Promise<Response>(resolve => pending.push(resolve)))
  vi.stubGlobal('fetch', fetcher)
  try {
   const d = createDashboard(undefined, true)
   const local = (revision: number, call: string, id: string): Snapshot => ({ ...snapshot(revision, call), step: 3, sample: false,
    qsoHistory: { provider: 'adif', label: 'Local ADIF', notice: 'Local History Only', result: { call, lookupId: id, status: 'loaded', recordCount: 1, complete: false } } })
   d.applySnapshot(local(1,'K1ABC','old-local'))
   expect(fetcher.mock.calls[0]![0]).toBe('/api/qso/history/old-local')
   d.applySnapshot(local(2,'K2XYZ','new-local'))
   pending[0]!(new Response(JSON.stringify({ call:'K1ABC',lookupId:'old-local',complete:true,records:sampleQsos('JA2HDE') })))
   await new Promise(resolve => setTimeout(resolve,0))
   expect(d.state.call).toBe('K2XYZ'); expect(d.state.qsos.status).toBe('pending')
   pending[1]!(new Response(JSON.stringify({ call:'K2XYZ',lookupId:'new-local',complete:false,records:[{...sampleQsos('JA2HDE')[0],id:'local-current'}] })))
   await vi.waitFor(() => expect(d.state.qsos).toMatchObject({status:'loaded',complete:false,data:[{id:'local-current'}]}))
  } finally {vi.unstubAllGlobals()}
 })

})
