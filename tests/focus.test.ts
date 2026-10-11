import { describe, it, expect, vi } from 'vitest'
import { createDashboard } from '../src/focus'
import { rigs, profiles, sampleQsos } from '../src/fixtures'
import type { Providers } from '../src/types'
const instant: Providers = { profile: async call => profiles[call] ?? null, qsos: async call => ({ records: sampleQsos(call), complete: true }) }
describe('focus contract', () => {
 it('orders and deduplicates interleaved selections while tracking rigs independently', () => {
  const d = createDashboard(instant)
  d.select('JA2HDE', rigs[0]!.id); d.select('DL1DEMO', rigs[1]!.id); d.select('W7DEMO', rigs[2]!.id); d.select('ja2hde', rigs[1]!.id)
  expect(d.state.history.map(e => e.call)).toEqual(['JA2HDE','W7DEMO','DL1DEMO'])
  expect(d.state.history[0]!.rigId).toBe(rigs[1]!.id)
  expect(d.state.rigSelections).toEqual({ [rigs[0]!.id]: 'JA2HDE', [rigs[1]!.id]: 'JA2HDE', [rigs[2]!.id]: 'W7DEMO' })
 })
 it('browses older entries without changing radio provenance or selections; decodes are passive', () => {
  const d = createDashboard(instant)
  d.select('JA2HDE', rigs[0]!.id, { at: 100 }); d.select('DL1DEMO', rigs[1]!.id, { at: 200 })
  const selections = { ...d.state.rigSelections }
  const before = d.state.history.map(e => ({ ...e }))
  d.browse('JA2HDE'); d.decode()
  expect(d.state.call).toBe('JA2HDE'); expect(d.state.history[1]).toMatchObject({ selectedAt: 100, rigId: rigs[0]!.id })
  expect(d.state.history[1]!.browsedAt).toBeTypeOf('number'); expect(d.state.rigSelections).toEqual(selections)
  expect(d.state.history.map(({ browsedAt, ...e }) => e)).toEqual(before)
  d.select('JA2HDE', rigs[2]!.id, { at: 300, band: '6m' })
  expect(d.state.history.map(e => e.call)).toEqual(['JA2HDE', 'DL1DEMO'])
  expect(d.state.history[0]).toMatchObject({ selectedAt: 300, rigId: rigs[2]!.id, band: '6m' })
  expect(d.state.history).toHaveLength(2)
 })
 it('guards independent delayed results', async () => {
  vi.useFakeTimers()
  const deferred: Providers = { profile: (call, delay = 0) => new Promise(resolve => setTimeout(() => resolve(profiles[call]!), delay)), qsos: (call, delay = 0) => new Promise(resolve => setTimeout(() => resolve({ records: sampleQsos(call), complete: true }), delay)) }
  const d = createDashboard(deferred)
  d.select('DL1DEMO', rigs[0]!.id, { profileDelay: 2000, qsoDelay: 3000 })
  d.select('JA2HDE', rigs[1]!.id, { profileDelay: 100, qsoDelay: 500 })
  expect(d.state.call).toBe('JA2HDE'); expect(d.state.profile.status).toBe('pending')
  await vi.advanceTimersByTimeAsync(100)
  expect(d.state.profile.status).toBe('loaded'); expect(d.state.qsos.status).toBe('pending')
  await vi.runAllTimersAsync()
  expect(d.state.profile).toMatchObject({ status: 'loaded', data: profiles.JA2HDE }); expect(d.state.qsos).toMatchObject({ status: 'loaded', data: sampleQsos('JA2HDE') })
  vi.useRealTimers()
 })
 it('discards an earlier request even when returning to the same callsign', async () => {
  let resolveOld!: (value: typeof profiles.JA2HDE | null) => void
  let requests = 0
  const d = createDashboard({ profile: call => ++requests === 1 ? new Promise(resolve => { resolveOld = resolve }) : Promise.resolve(profiles[call]!), qsos: async call => ({ records: sampleQsos(call), complete: true }) })
  d.select('JA2HDE', rigs[0]!.id); d.select('DL1DEMO', rigs[1]!.id); d.browse('JA2HDE')
  await Promise.resolve(); resolveOld({ ...profiles.JA2HDE!, name: 'Stale profile' }); await Promise.resolve()
  expect(d.state.profile).toMatchObject({ status: 'loaded', data: { name: 'Haruto Mori' } })
 })
 it('preserves incomplete empty histories as unknown rather than complete empty results', async () => {
  const d = createDashboard({ profile: async () => null, qsos: async () => ({ records: [], complete: false }) })
  d.select('JA2HDE', rigs[0]!.id)
  await Promise.resolve()
  expect(d.state.qsos).toEqual({ status: 'loaded', data: [], complete: false })
 })
 it('rejects invalid selections', () => { const d = createDashboard(instant); d.select('', rigs[0]!.id); d.select('JA2HDE', 'unknown'); expect(d.state.history).toEqual([]) })
})
