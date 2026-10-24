import { describe, expect, it } from 'vitest'
import { gridLocation, stationMapLocation } from '../src/stationMap'
import type { EnrichmentState, Entry } from '../src/types'

const entry: Entry = { call: 'K1ACT', dxGrid: 'PM85', rigId: 'Fixture', selectedAt: 0, recency: 1, band: '20m' }
const enrichment: EnrichmentState = { config: { enabled: true, allow_country_estimate: false } as EnrichmentState['config'], health: {}, result: {
 call: 'K1ACT', status: 'loaded', callbookGrid: 'FN31', fields: { latitude: 41.2, longitude: -73.1 }, fieldSources: { latitude: 'QRZ XML', longitude: 'QRZ XML' },
} }
describe('station map location', () => {
 it('converts 4, 6 and 8 character grids to cell centers and bounds, including equator and dateline', () => {
  expect(gridLocation('pm85')).toMatchObject({ lat: 35.5, lng: 137, bounds: [[35, 136], [36, 138]] })
  expect(gridLocation('FN31pr')?.lat).toBeCloseTo(41.7291667)
  expect(gridLocation('FN31pr')?.lng).toBeCloseTo(-72.7083333)
  expect(gridLocation('FN31pr12')?.lat).toBeCloseTo(41.71875)
  expect(gridLocation('FN31pr12')?.lng).toBeCloseTo(-72.7375)
  expect(gridLocation('JJ00')?.bounds).toEqual([[0, 0], [1, 2]])
  expect(gridLocation('RR99')?.lng).toBe(179)
  for (const raw of ['', 'ZZ99', 'AA', 'AA000', 'AA00ZZ', 0, null, '<img>']) expect(gridLocation(raw)).toBeUndefined()
 })
 it('shows a selected operating grid immediately, ahead of conflicting callbook coordinates', () => {
  expect(stationMapLocation('K1ACT', entry, enrichment)).toMatchObject({ lat: 35.5, lng: 137, detail: 'WSJT-X operating grid · approximate center' })
  expect(stationMapLocation('K1ACT', entry)).toMatchObject({ label: 'PM85' })
  expect(stationMapLocation('K2NEW', entry, enrichment)).toBeUndefined()
 })
 it('uses only valid QRZ coordinate pairs for a home marker and preserves explicit zero', () => {
  expect(stationMapLocation('K1ACT', undefined, enrichment)).toMatchObject({ lat: 41.2, lng: -73.1, detail: 'QRZ callbook coordinates · home location' })
  const withCoordinates = (latitude: unknown, longitude: unknown) => ({ ...enrichment, result: { ...enrichment.result, callbookGrid: '', fields: { latitude, longitude } } })
  expect(stationMapLocation('K1ACT', undefined, withCoordinates('0', 0))).toMatchObject({ lat: 0, lng: 0 })
  for (const [lat, lng] of [[null, null], ['', ''], [false, false], [91, 0], [0, 181], ['NaN', 3]]) expect(stationMapLocation('K1ACT', undefined, withCoordinates(lat, lng))).toBeUndefined()
  expect(stationMapLocation('K1ACT', undefined, { ...enrichment, result: { ...enrichment.result, fieldSources: { latitude: 'Country-files.com', longitude: 'Country-files.com' } } })).toMatchObject({ label: 'FN31', detail: 'Callbook home grid · approximate center' })
 })
 it('requires the existing estimate opt-in and labels entity centers, without treating missing data as a location', () => {
  const estimate = { ...enrichment, result: { call: 'K1ACT', status: 'loaded', locationGrid: 'JJ00', locationSource: 'Approximate provider coordinates; not a reported station grid' } }
  expect(stationMapLocation('K1ACT', undefined, estimate)).toBeUndefined()
  expect(stationMapLocation('K1ACT', undefined, { ...estimate, config: { ...estimate.config, allow_country_estimate: true } })).toMatchObject({ detail: 'Approximate entity location · not a station position' })
  expect(stationMapLocation('K1ACT', undefined, { ...enrichment, result: { call: 'K1ACT', status: 'pending' } })).toBeUndefined()
 })
})
