import type { Lookup, Qso } from './types'

export type SortColumn = 'date' | 'band' | 'mode' | 'sent' | 'received' | 'station' | 'confirmed'
export type SortDirection = 'ascending' | 'descending'
// Nominal MHz order, including bands beyond the current fixtures.
const bandMHz: Record<string, number> = { '2190m': .136, '630m': .472, '160m': 1.8, '80m': 3.5, '60m': 5, '40m': 7, '30m': 10, '20m': 14, '17m': 18, '15m': 21, '12m': 24, '10m': 28, '6m': 50, '4m': 70, '2m': 144, '1.25m': 222, '70cm': 420, '33cm': 902, '23cm': 1240 }
export const normalizeBand = (band: string) => band.toLowerCase().replace(/\s/g, '')
export const bandLabel = (band: string) => normalizeBand(band).replace(/(cm|m)$/, ' $1')
export function sortQsos(qsos: Qso[], column: SortColumn, direction: SortDirection): Qso[] {
 const value = (q: Qso): string | number => {
  if (column === 'date') return Date.parse(q.date)
  if (column === 'band') return bandMHz[normalizeBand(q.band)] ?? Infinity
  if (column === 'sent' || column === 'received') return Number(q[column])
  if (column === 'confirmed') return Number(q.confirmed)
  return q[column]
 }
 return [...qsos].sort((a, b) => {
  const x = value(a), y = value(b)
  const comparison = typeof x === 'number' && typeof y === 'number' ? (x === y ? 0 : x < y ? -1 : 1) : String(x).localeCompare(String(y))
  return comparison * (direction === 'ascending' ? 1 : -1)
 })
}
export function currentBandStatus(history: Lookup<Qso[]>, band: string | null | undefined, source = 'sample') {
 if (!band?.trim()) return { kind: 'unknown', title: 'Current band unknown', detail: 'Latest selection has no known band.' }
 const label = bandLabel(band)
 if (history.status === 'pending') return { kind: 'checking', title: `Checking ${label}…`, detail: `Waiting for complete ${source} history.` }
 if (history.status === 'error' || (history.status === 'loaded' && history.complete !== true)) return { kind: 'unavailable', title: `Status unavailable on ${label}`, detail: 'History failed or is incomplete · worked status unknown.' }
 const records = history.status === 'loaded' ? history.data : []
 const count = records.filter(q => normalizeBand(q.band) === normalizeBand(band)).length
 return count ? { kind: 'worked', title: `Worked on ${label}`, detail: `${count} matching ${count === 1 ? 'QSO' : 'QSOs'} · all modes` } : { kind: 'new', title: `New on ${label}`, detail: records.length ? `Complete ${source} history · no QSOs on this band` : `New callsign · complete ${source} history · 0 QSOs` }
}
