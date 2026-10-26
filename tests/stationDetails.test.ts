import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { stationGroups, webLink, operatorName, stationKeyFacts, stationTableRows, stationConfirmationFact } from '../src/stationDetails'
import StationKeyInformation from '../src/components/StationKeyInformation.vue'
import EnrichmentCard from '../src/components/EnrichmentCard.vue'
import ContactDetails from '../src/components/ContactDetails.vue'
import type { EnrichmentState, Lookup, Qso } from '../src/types'
const enrichment: EnrichmentState = {
 config: { enabled: true } as EnrichmentState['config'], health: {},
 result: { status: 'loaded', call: 'K1ABC', reportedGrid: 'JO62', callbookGrid: 'FN31', stationGrid: 'CN87',
 fields: { country: 'United States', fname: 'Fixture', name: 'Operator', email: '', state: null, longitude: 0, gmtoffset: 0, lotw: '1', eqsl: '0', mqsl: false, bio: '1200', nickname: '  ', url: 'javascript:alert(1)' },
 fieldSources: { country: 'QRZ XML', longitude: 'QRZ XML' }, providers: { qrz: { status: 'loaded', fields: {}, updatedAt: 1700000000000 } } }
}
describe('station presentation', () => {
 it('omits missing rows while retaining zero coordinates, zero offsets and explicit QSL negatives', () => {
  const groups = stationGroups(enrichment.result)
  const fields = groups.flatMap(group => group.fields)
  expect(fields.find(f => f.key === 'longitude')?.value).toBe('0')
  expect(fields.find(f => f.key === 'gmtoffset')?.value).toBe('0')
  expect(fields.find(f => f.key === 'lotw')?.value).toBe('Yes')
  expect(fields.find(f => f.key === 'eqsl')?.value).toBe('No')
  expect(stationKeyFacts(enrichment.result).some(f => f.key === 'qrz')).toBe(false)
  expect(stationKeyFacts(enrichment.result).some(f => f.key === 'eqsl')).toBe(false)
  expect(stationTableRows(enrichment.result).some(f => f.key === 'eqsl')).toBe(false)
  expect(fields.find(f => f.key === 'mqsl')?.value).toBe('No')
  expect(fields.some(f => ['email', 'state', 'nickname'].includes(f.key))).toBe(false)
  expect(groups[0]?.title).toBe('Contact & QSL')
  expect(groups.find(group => group.title === 'Operating location')?.fields.map(f => f.value)).toEqual(['JO62', 'FN31', 'CN87'])
  expect(fields.find(f => f.key === 'longitude')?.source).toBe('QRZ XML')
 })
 it('lists advertised confirmation methods without inferring QRZ from a profile or account', () => {
  const data = { ...enrichment.result, fields: { lotw: 'Y', eqsl: 'N', mqsl: true, user: 'profile-owner', lotw_user: '1' } }
  expect(stationConfirmationFact(data, 'K1ABC')).toMatchObject({ label: 'Confirm via', value: 'LoTW, Paper QSL' })
  expect(stationGroups(data).flatMap(g => g.fields).find(f => f.key === 'eqsl')?.value).toBe('No')
  expect(stationConfirmationFact({ ...data, fields: { lotw: '0', eqsl: '', mqsl: false } }, 'K1ABC').value).toBe('Unknown')
 })
 it('uses positive contact evidence for QRZ, deduplicates methods, and respects current advertised negatives', () => {
  const qso: Qso = { id: '1', call: 'K1ABC', date: '2026-10-24T14:25:27Z', band: '17m', mode: 'FT8', sent: '-10', received: '-07', station: 'KF6UFO', grid: 'JO62', confirmed: true, confirmations: [{ type: 'QRZ.com', date: '' }, { type: 'LoTW', date: '' }, { type: 'eQSL', date: '' }, { type: 'unknown service', date: '' }] }
  const history: Lookup<Qso[]> = { status: 'loaded', complete: false, data: [qso, qso] }
  const fact = stationConfirmationFact(enrichment.result, 'K1ABC', history)
  expect(fact.value).toBe('LoTW, QRZ')
  expect(fact.source).toContain('QRZ: previously confirmed in contact history')
  expect(stationConfirmationFact(undefined, 'K1ABC', { ...history, data: [qso, { ...qso, call: 'K2OTHER' }] }).value).toBe('LoTW, QRZ, eQSL')
  expect(stationConfirmationFact(enrichment.result, 'K2NEW', history).value).toBe('Unknown')
  expect(stationConfirmationFact(undefined, 'K1ABC', { ...history, data: [{ ...qso, call: undefined }] }).value).toBe('Unknown')
  for (const unavailable of [{ status: 'pending' }, { status: 'empty' }, { status: 'error', message: 'Unavailable' }] as Lookup<Qso[]>[]) expect(stationConfirmationFact(undefined, 'K1ABC', unavailable).value).toBe('Unknown')
 })
 it('renders one compact confirmation indicator, with unknown state after a different callsign', async () => {
  const w = mount(StationKeyInformation, { props: { enrichment, call: 'K1ABC' } })
  expect(w.get('[data-field="confirmVia"] dd').text()).toBe('LoTW')
  expect(w.find('a').exists()).toBe(false)
  await w.setProps({ call: 'K2NEW' })
  expect(w.get('[data-field="confirmVia"] dd').text()).toBe('Unknown')
  expect(w.text()).not.toContain('LoTW')
 })
 it('keeps unsafe links as text, and formats the provider display name without HTML rendering', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,x', 'https://user:pass@example.com', '//example.com']) expect(webLink(value)).toBeUndefined()
  expect(webLink('https://example.com/profile')).toBe('https://example.com/profile')
  expect(operatorName({ name_fmt: 'DOE, Jane', fname: 'Jane', name: 'Doe' })).toBe('DOE, Jane')
  expect(operatorName({ fname: 'Jane', name: 'Doe' })).toBe('Jane Doe')
 })
 it('renders sparse details without empty labels, separates home and reported grids, and rejects stale calls', async () => {
  const w = mount(EnrichmentCard, { props: { enrichment, call: 'K1ABC' } })
  expect(w.find('.station-details-scroll').attributes('tabindex')).toBe('0')
  expect(w.text()).not.toContain('Email')
  expect(w.text()).not.toContain('State / province')
  expect(w.text()).toContain('Reported operating grid')
  expect(w.text()).toContain('Callbook home grid')
  expect(w.text()).toContain('Biography on QRZ')
  expect(w.find('a[href^="javascript:"]').exists()).toBe(false)
  expect(w.text()).toContain('QRZ XML')
  await w.setProps({ call: 'K2NEW' })
  expect(w.text()).not.toContain('United States')
  expect(w.find('.station-details-scroll').exists()).toBe(false)
 })
 it('distinguishes provider failure, empty response and pending state without losing usable partial results', async () => {
  const w = mount(EnrichmentCard, { props: { call: 'K1ABC', enrichment: { ...enrichment, result: { ...enrichment.result, providers: { qrz: { status: 'error', fields: {}, message: 'Provider unavailable' } } } } } })
  expect(w.text()).toContain('United States')
  expect(w.text()).toContain('Provider unavailable')
  await w.setProps({ enrichment: { ...enrichment, result: { call: 'K1ABC', status: 'empty' } } })
  expect(w.text()).toContain('No matching station details')
  await w.setProps({ enrichment: { ...enrichment, result: { call: 'K1ABC', status: 'pending' } } })
  expect(w.text()).toContain('Looking up K1ABC')
  expect(w.text()).not.toContain('No matching')
 })
 it('keeps actual contact fields and explicit confirmation state; hides absent optional fields', () => {
  const w = mount(ContactDetails, { props: { radio: true, qso: { id: '1', date: '2026-10-24T14:25:27Z', band: '17m', mode: 'FT8', sent: '-10', received: '-07', station: 'KF0TKE', grid: 'JO62', confirmed: null, details: { name: 'Fixture', notes: '', tx_pwr: '0' } } } })
  expect(w.text()).toContain('2026-10-24 14:25:27 UTC')
  expect(w.text()).toContain('JO62')
  expect(w.text()).toContain('Unavailable')
  expect(w.text()).not.toContain('Notes')
  expect(w.text()).toContain('Power (W)0')
 })
})
