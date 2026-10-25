import { describe, it, expect } from 'vitest'
import { currentBandStatus, sortQsos } from '../src/qso'
import { sampleQsos } from '../src/fixtures'
const records = sampleQsos('JA2HDE')
describe('QSO sorting and band assessment', () => {
 it('sorts UTC instants, frequency order, numeric reports and displayed text without mutating history', () => {
  const original = [...records]
  expect(sortQsos([...records].reverse(), 'date', 'descending')).toEqual(records)
  expect([...new Set(sortQsos(records, 'band', 'ascending').map(q => q.band))]).toEqual(['40m','20m','15m','10m'])
  expect([...new Set(sortQsos(records, 'band', 'descending').map(q => q.band))]).toEqual(['10m','15m','20m','40m'])
  for (const column of ['sent', 'received'] as const) {
   const custom = records.slice(0,3).map((q, i) => ({ ...q, [column]: ['-2','-10','+3'][i]! }))
   expect(sortQsos(custom, column, 'ascending').map(q => q[column])).toEqual(['-10','-2','+3'])
  }
  for (const column of ['mode', 'station'] as const) {
   const values = sortQsos(records, column, 'ascending').map(q => q[column])
   expect(values).toEqual([...values].sort())
  }
  expect(sortQsos(records, 'confirmed', 'ascending')[0]!.confirmed).toBe(false)
  expect(records).toEqual(original)
 })
 it('uses band regardless of mode and only declares new from complete history', () => {
  const complete = { status: 'loaded' as const, data: records, complete: true }
  expect(currentBandStatus(complete, '20 m')).toMatchObject({ title: 'Worked on 20 m', detail: '6 matching QSOs · all modes' })
  expect(currentBandStatus({ ...complete, data: [records[0]!] }, '20m').kind).toBe('worked') // FT4 counts
  expect(currentBandStatus(complete, '6m')).toMatchObject({ title: 'New on 6 m' })
  expect(currentBandStatus({ status: 'empty' }, '20m').detail).toContain('New callsign')
  expect(currentBandStatus({ status: 'pending' }, '20m').kind).toBe('checking')
  expect(currentBandStatus({ status: 'error', message: 'offline' }, '20m').kind).toBe('unavailable')
  for (const data of [records, []]) expect(currentBandStatus({ status: 'loaded', data, complete: false }, '20m').kind).toBe('unavailable')
  expect(currentBandStatus(complete, null).kind).toBe('unknown')
 })
 it('shows positive observed band and mode immediately while keeping other incomplete bands unknown', () => {
  const observed = { ...records[0]!, band: '17m', mode: 'FT8', observed: true }
  const incomplete = { status: 'loaded' as const, data: [observed], complete: false }
  expect(currentBandStatus(incomplete, '17m')).toMatchObject({ kind: 'worked', title: 'Worked on 17 m', detail: expect.stringContaining('observed locally · FT8') })
  expect(currentBandStatus(incomplete, '20m').kind).toBe('unavailable')
  expect(currentBandStatus({ ...incomplete, data: [{ ...observed, observed: false }] }, '17m').kind).toBe('unavailable')
 })
})
