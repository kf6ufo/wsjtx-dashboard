import { describe, expect, it } from 'vitest'
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
 it('does not fabricate a sample logbook for a live callsign absent from the catalog', async () => {
  await expect(mockProviders.qsos('K1UNSEEN', 0)).rejects.toThrow('No sample QSO fixture')
 })
})
