import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import App from '../src/App.vue'
import { createDashboard } from '../src/focus'
import { rigs, profiles, sampleQsos } from '../src/fixtures'
describe('dashboard components', () => {
 it('browses an older station and opens complete QSO details', async () => {
  const d = createDashboard({ profile: async call => profiles[call]!, qsos: async call => ({ records: sampleQsos(call), complete: true }) })
  d.select('JA2HDE', rigs[0]!.id, { at: 100 }); d.select('DL1DEMO', rigs[1]!.id)
  const wrapper = mount(App, { props: { dashboard: d } }); await flushPromises()
  await wrapper.get('[data-testid="history-JA2HDE"]').trigger('click'); await flushPromises()
  expect(wrapper.get('[data-testid="focused-call"]').text()).toBe('JA2HDE')
  expect(wrapper.text()).toContain('radio selections unchanged'); expect(d.state.history[1]!.selectedAt).toBe(100)
  expect(wrapper.findAll('tbody tr')).toHaveLength(24)
  expect(wrapper.findAll('.history-entry')[1]!.attributes('aria-pressed')).toBe('true')
  expect(wrapper.get('[data-testid="band-status"]').text()).toContain('Worked on 20 m')
  const bandHeader = wrapper.findAll('th').find(th => th.text().startsWith('Band'))!
  await bandHeader.get('button').trigger('click')
  expect(bandHeader.attributes('aria-sort')).toBe('ascending')
  expect(wrapper.findAll('.band-tag')[0]!.text()).toBe('40m')
  await bandHeader.get('button').trigger('click')
  expect(bandHeader.attributes('aria-sort')).toBe('descending')
  expect(wrapper.findAll('.band-tag')[0]!.text()).toBe('10m')
  expect(wrapper.get('.summary-last').text()).toContain('2026-10-10')
  await wrapper.get('.qso-link').trigger('click'); expect(wrapper.get('[role="dialog"]').text()).toContain('KF6UFO')
  await wrapper.get('[role="dialog"] button').trigger('click'); expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
 })
 it('shows profile and QSO pending independently and distinguishes failed from empty', async () => {
  const d = createDashboard({ profile: async () => null, qsos: async () => { throw new Error('Fixture offline') } })
  d.select('PY2DEMO', rigs[0]!.id)
  const wrapper = mount(App, { props: { dashboard: d } })
  expect(wrapper.get('[data-testid="band-status"]').text()).toContain('Checking 20 m'); expect(wrapper.text()).toContain('Loading sample operator profile'); expect(wrapper.text()).toContain('Loading sample QSO history')
  await flushPromises(); expect(wrapper.text()).toContain('No sample operator profile'); expect(wrapper.text()).toContain('worked-before status unknown'); expect(wrapper.text()).not.toContain('0 sample contacts')
  const empty = createDashboard({ profile: async () => profiles.VK3DEMO!, qsos: async () => ({ records: [], complete: true }) }); empty.select('VK3DEMO', rigs[0]!.id)
  const w = mount(App, { props: { dashboard: empty } }); await flushPromises(); expect(w.text()).toContain('0 sample contacts')
 })
})

it('renders new-band, incomplete and unknown states from the latest selection snapshot', async () => {
 const d = createDashboard({ profile: async () => null, qsos: async () => ({ records: sampleQsos('JA2HDE'), complete: true }) })
 d.select('JA2HDE', rigs[0]!.id, { band: '6m' })
 const w = mount(App, { props: { dashboard: d } }); await flushPromises()
 expect(w.get('[data-testid="band-status"]').text()).toContain('New on 6 m')
 d.state.qsos = { status: 'loaded', data: [], complete: false }; await w.vm.$nextTick()
 expect(w.get('[data-testid="band-status"]').text()).toContain('Status unavailable on 6 m')
 expect(w.get('[data-testid="band-status"]').text()).not.toContain('New')
 d.select('JA2HDE', rigs[1]!.id, { band: null }); await flushPromises()
 expect(w.get('[data-testid="band-status"]').text()).toContain('Current band unknown')
})
