import { describe, expect, it, vi } from 'vitest'
import { createDashboard } from '../src/focus'
import { mockProviders } from '../src/providers'
import { profiles, sampleQsos } from '../src/fixtures'
import type { Snapshot } from '../src/types'
const snapshot = (revision: number, call = 'JA2HDE'): Snapshot => ({
 epoch: 'server-one', revision, call, source: 'radio',
 history: [{ call, rigId: 'new-radio', band: '20m', mode: 'FT4', selectedAt: 100, recency: revision }],
 rigs: [{ id: 'new-radio', name: 'New radio', band: '20m', mode: 'FT4', color: '#70c9bd', call, frequency: 14080000, lastSeen: 100, online: true }],
 counters: { decodes: 0, malformed: 0 }, receiver: { status: 'disabled', error: null },
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
   expect(d.state.qsos).toMatchObject({ status: 'error', message: expect.stringContaining('history is disabled') })
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
