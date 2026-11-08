import { describe, expect, it } from 'vitest'
import { calculateQsoOutlook } from '../src/qsoOutlook'
import { gridLocation } from '../src/stationMap'
import type { PskReporterState, ReceptionSpot } from '../src/types'

const now = Date.UTC(2026, 10, 8, 12)
const spot: ReceptionSpot = { sender: 'N0CALL', receiver: 'K1FOCUS', band: '20m', grid: 'FN31', heardAt: now - 60000, frequency: 14074000, mode: 'FT8', snr: -12 }
const feed = (spots: ReceptionSpot[]): PskReporterState => ({ config: { enabled: true, callsign: '', window_minutes: 15 }, status: 'connected', error: '', callsigns: ['N0CALL'], connectedAt: now, evicted: 0, spots })
const options = { sender: 'N0CALL', call: 'K1FOCUS', band: '20m', mode: 'FT8', location: gridLocation('FN31'), minutes: 15, now }
const outlook = (spots: ReceptionSpot[], overrides: Partial<Parameters<typeof calculateQsoOutlook>[0]> = {}) => calculateQsoOutlook({ ...options, feed: feed(spots), ...overrides })
const nearby = (count: number, grid = 'FN32') => Array.from({ length: count }, (_, index) => ({ ...spot, receiver: `K${index + 2}NEAR`, grid }))

describe('experimental QSO Outlook', () => {
 it.each([[0, 90], [5 * 60000, 90], [5 * 60000 + 1, 80], [15 * 60000, 80], [15 * 60000 + 1, null]])('scores direct evidence at age %i ms as %s', (age, score) => {
  expect(outlook([{ ...spot, heardAt: now - age }]).score).toBe(score)
 })
 it.each([[3, 'FN32', 75, 'Favorable', 'green'], [2, 'FN32', 60, 'Moderate', 'yellow'], [1, 'FN32', 60, 'Moderate', 'yellow'], [3, 'FN34', 55, 'Moderate', 'yellow'], [2, 'FN34', 35, 'Limited evidence', 'red'], [1, 'FN34', 35, 'Limited evidence', 'red']])('scores %i nearby receivers in %s', (count, grid, score, classification, color) => {
  const value = outlook(nearby(count as number, grid as string))
  expect(value).toMatchObject({ score, classification, color, within500: count, latestAt: spot.heardAt })
  expect(value.nearestKm).toBeCloseTo(grid === 'FN32' ? 111.1949 : 333.5848, 3)
 })
 it('preserves rule priority over larger regional counts and prefers direct evidence', () => {
  const reports = [...nearby(1), ...nearby(4, 'FN34').map(s => ({ ...s, receiver: `${s.receiver}-RX` }))]
  expect(outlook(reports)).toMatchObject({ score: 60, within200: 1, within500: 5 })
  expect(outlook([...reports, { ...spot, heardAt: now - 9 * 60000 }]).score).toBe(80)
 })
 it('counts complete unique receiver identities, retaining only each latest report', () => {
  const reports = [nearby(1)[0]!, { ...nearby(1)[0]!, heardAt: now - 30000 }, { ...nearby(1)[0]!, grid: 'FN34', heardAt: now - 45000 }]
  expect(outlook(reports)).toMatchObject({ score: 60, within200: 1, within500: 1, latestAt: now - 30000 })
  expect(outlook([...reports, { ...reports[0]!, receiver: 'K2NEAR-1' }, { ...reports[0]!, receiver: 'K2NEAR-RX' }]).score).toBe(75)
  expect(outlook([{ ...spot, receiver: 'K1FOCUS-888' }]).direct).toBeUndefined()
 })
 it('caps nearby evidence at ten minutes and direct evidence at fifteen, within the selected window', () => {
  const near = nearby(1)[0]!
  expect(outlook([{ ...near, heardAt: now - 10 * 60000 }]).score).toBe(60)
  expect(outlook([{ ...near, heardAt: now - 10 * 60000 - 1 }]).score).toBeNull()
  expect(outlook([{ ...spot, heardAt: now - 6 * 60000 }], { minutes: 5 }).score).toBeNull()
  expect(outlook([{ ...spot, heardAt: now - 16 * 60000 }], { minutes: 60 }).score).toBeNull()
  expect(outlook([spot], { now: now + 15 * 60000 }).score).toBeNull()
 })
 it('requires exact transmitting identity and band, including portable identity', () => {
  expect(outlook([{ ...spot, sender: 'N0CALL/P' }, { ...spot, band: '17m' }]).score).toBeNull()
  expect(outlook([{ ...spot, sender: 'N0CALL/P' }], { sender: 'N0CALL/P' }).score).toBe(90)
  expect(outlook([spot], { sender: '' }).score).toBeNull()
  expect(outlook([spot], { band: null }).score).toBeNull()
 })
 it('prefers matching-mode nearby reports and falls back to all modes on the band', () => {
  const reports = [{ ...nearby(1)[0]!, mode: ' ft8 ' }, ...nearby(3).map(s => ({ ...s, receiver: `${s.receiver}-RX`, mode: 'FT4' }))]
  expect(outlook(reports)).toMatchObject({ score: 60, within500: 1, nearbyMode: 'FT8' })
  expect(outlook(reports, { mode: 'JS8' })).toMatchObject({ score: 75, within500: 4, nearbyMode: null })
  expect(outlook(reports, { mode: undefined }).score).toBe(75)
  expect(outlook([...reports, { ...spot, mode: 'FT4' }])).toMatchObject({ score: 90, direct: { mode: 'FT4' } })
 })
 it('returns Unknown for disabled, absent, empty, distant or unusable reports, retaining cached evidence during outages', () => {
  for (const overrides of [{ feed: undefined }, { feed: { ...feed([spot]), config: { ...feed([]).config, enabled: false } } }]) {
   const value = outlook([spot], overrides)
   expect(value).toMatchObject({ score: null, color: 'gray' })
   expect(value.direct).toBeUndefined()
  }
  for (const reports of [[], nearby(2, 'FN36'), [{ ...spot, grid: 'ZZ99' }], [{ ...spot, heardAt: now + 60000 }]]) expect(outlook(reports).score).toBeNull()
  expect(outlook([], { feed: { ...feed([]), status: 'reconnecting' } }).score).toBeNull()
  expect(outlook([], { feed: { ...feed([spot]), status: 'reconnecting' } }).score).toBe(90)
 })
 it('requires a real station location, with confirmation independent of that requirement', () => {
  for (const location of [undefined, { ...options.location!, isEntityEstimate: true }, { ...options.location!, lat: NaN }]) {
   expect(outlook([spot], { location })).toMatchObject({ score: null, classification: 'Unknown', direct: spot })
  }
 })
 it('recalculates for a new focus and location without carrying over confirmation', () => {
  expect(outlook([spot]).score).toBe(90)
  expect(outlook([spot], { call: 'K2FOCUS', location: gridLocation('FN32') })).toMatchObject({ score: 60, direct: undefined })
  expect(outlook([spot], { call: 'K2FOCUS', location: gridLocation('PM85') })).toMatchObject({ score: null, direct: undefined })
 })
 it('uses great-circle distance across the date line and inclusive 200/500 km bounds', () => {
  const receiver = { ...nearby(1)[0]!, grid: 'AJ00' }
  expect(outlook([receiver], { location: gridLocation('RJ90') })).toMatchObject({ score: 35 })
  for (const distance of [199.99, 200.01, 499.99, 500.01]) {
   const location = { ...options.location!, lat: options.location!.lat + distance / 6371 * 180 / Math.PI }
   expect(outlook([{ ...nearby(1)[0]!, grid: 'FN31' }], { location }).score).toBe(distance < 200 ? 60 : distance < 500 ? 35 : null)
  }
 })
 it('does not use SNR or mutate the feed', () => {
  const data = feed([{ ...spot, snr: -40 }]), before = JSON.stringify(data)
  expect(calculateQsoOutlook({ ...options, feed: data }).score).toBe(90)
  expect(outlook([{ ...spot, snr: 30 }]).score).toBe(90)
  expect(JSON.stringify(data)).toBe(before)
 })
})
