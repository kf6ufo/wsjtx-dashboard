import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { stationGroups, webLink, operatorName, stationKeyFacts, stationTableRows } from '../src/stationDetails'
import EnrichmentCard from '../src/components/EnrichmentCard.vue'
import ContactDetails from '../src/components/ContactDetails.vue'
import type { EnrichmentState } from '../src/types'
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
  expect(stationKeyFacts(enrichment.result).find(f => f.key === 'qrz')).toMatchObject({ label: 'QRZ', value: 'Profile ↗', href: 'https://www.qrz.com/db/K1ABC' })
  expect(stationKeyFacts(enrichment.result).some(f => f.key === 'eqsl')).toBe(false)
  expect(stationTableRows(enrichment.result).some(f => f.key === 'eqsl')).toBe(false)
  expect(fields.find(f => f.key === 'mqsl')?.value).toBe('No')
  expect(fields.some(f => ['email', 'state', 'nickname'].includes(f.key))).toBe(false)
  expect(groups[0]?.title).toBe('Contact & QSL')
  expect(groups.find(group => group.title === 'Operating location')?.fields.map(f => f.value)).toEqual(['JO62', 'FN31', 'CN87'])
  expect(fields.find(f => f.key === 'longitude')?.source).toBe('QRZ XML')
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
