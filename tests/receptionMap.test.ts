import { describe, expect, it } from 'vitest'
import { localReceptionSpots, mapReceptions, mapReceptionLabel, receptionSummary } from '../src/receptionMap'
import { calculateQsoOutlook } from '../src/qsoOutlook'
import { receptionSpots } from '../src/pskreporter'
import { gridLocation } from '../src/stationMap'
import type { LocalReceptionSpot, ReceptionSpot, PskReporterState } from '../src/types'

const now = Date.UTC(2026, 10, 8, 12)
const sent: ReceptionSpot = { sender: 'N0CALL', receiver: 'K1FOCUS', band: '20m', grid: 'FN31', mode: 'FT8', heardAt: now - 60000, frequency: 14074000, snr: -12 }
const recv: LocalReceptionSpot = { call: 'K1FOCUS', rigId: 'A', stationCall: 'N0CALL', band: '20m', grid: 'FN32', mode: 'FT8', heardAt: now - 120000, snr: -14 }
const local = (spots: LocalReceptionSpot[], minutes = 15) => localReceptionSpots({ spots, evicted: 0 }, 'N0CALL', 'A', '20m', minutes, now)

describe('directional map evidence', () => {
 it('keeps local receiver context, identity and band exact while rejecting stale/unknown locations', () => {
  expect(local([recv, { ...recv, stationCall: 'N0CALL/P' }, { ...recv, rigId: 'B' }, { ...recv, band: '17m' }, { ...recv, grid: 'ZZ99' }, { ...recv, heardAt: now-16*60000 }, { ...recv, heardAt: now+31000 }])).toEqual([recv])
  expect(localReceptionSpots({ spots: [recv], evicted: 0 }, '', 'A', '20m', 15, now)).toEqual([])
  expect(localReceptionSpots({ spots: [recv], evicted: 0 }, 'N0CALL', undefined, '20m', 15, now)).toEqual([])
  expect(localReceptionSpots({ spots: [recv], evicted: 0 }, 'N0CALL', 'A', null, 15, now)).toEqual([])
  expect(local([recv], 1)).toEqual([])
 })
 it('deduplicates latest local reports, preserving exact portable calls', () => {
  const newer = { ...recv, heardAt: now-30000 }
  expect(local([recv, newer, { ...recv, call: 'K1FOCUS/P' }])).toEqual([newer, { ...recv, call: 'K1FOCUS/P' }])
 })
 it('combines mutual evidence into one marker with both directional details', () => {
  const stations = mapReceptions([sent], [recv], 'both')
  expect(stations).toHaveLength(1)
  expect(stations[0]).toMatchObject({ call: 'K1FOCUS', direction: 'both', sent, recv, location: gridLocation('FN32') })
  const label = mapReceptionLabel(stations[0]!, now)
  expect(label).toContain('Mutual reception')
  expect(label).toContain('K1FOCUS heard N0CALL')
  expect(label).toContain('N0CALL heard K1FOCUS')
  expect(label).toContain('-14 dB')
  expect(label).toContain('2026-11-08T11:58:00.000Z')
 })
 it('filters immediately without losing the direction facts on mutual stations', () => {
  const sources = [sent, { ...sent, receiver: 'K2SENT' }], locals = [recv, { ...recv, call: 'K3RECV' }]
  expect(mapReceptions(sources, locals, 'sent').map(s => s.call)).toEqual(['K1FOCUS', 'K2SENT'])
  expect(mapReceptions(sources, locals, 'recv').map(s => s.call)).toEqual(['K1FOCUS', 'K3RECV'])
  expect(mapReceptions(sources, locals, 'both')).toHaveLength(3)
 })
 it('does not infer mutual reception from a grid, suffixed receiver, band or identity mismatch', () => {
  expect(mapReceptions([sent], [{ ...recv, call: 'K2OTHER', grid: sent.grid }], 'both').map(s => s.direction)).toEqual(['sent', 'recv'])
  expect(mapReceptions([{ ...sent, receiver: 'K1FOCUS-888' }], [recv], 'both')).toHaveLength(2)
  for (const report of [{ ...recv, band: '17m' }, { ...recv, stationCall: 'N0CALL/P' }]) {
   expect(mapReceptions([sent], [report], 'both').some(s => s.direction === 'both')).toBe(false)
  }
  expect(mapReceptions([sent], local([{ ...recv, heardAt: now-20*60000 }]), 'both')[0]!.direction).toBe('sent')
 })
 it('keeps a long map window separate from outlook and never scores local decodes', () => {
  const feed: PskReporterState = { config: { enabled: true, callsign: '', window_minutes: 15 }, status: 'connected', error: '', callsigns: ['N0CALL'], connectedAt: now, evicted: 0, spots: [{ ...sent, heardAt: now-32*60000 }] }
  const reports = receptionSpots(feed, 'N0CALL', '20m', 60, now)
  const score = () => calculateQsoOutlook({ feed, sender: 'N0CALL', call: sent.receiver, band: sent.band, mode: 'FT8', location: gridLocation('FN31'), minutes: 60, now })
  for (const view of ['sent', 'recv', 'both'] as const) {
   mapReceptions(reports, [recv], view)
   expect(score().score).toBeNull()
  }
  expect(reports).toHaveLength(1)
  expect(receptionSummary(reports[0], recv)).toBe('Mutual reception')
  expect(receptionSummary(undefined, recv)).toBe('I heard')
  expect(receptionSummary(reports[0])).toBe('Heard me')
  expect(receptionSummary()).toBe('No recent evidence')
 })
})
