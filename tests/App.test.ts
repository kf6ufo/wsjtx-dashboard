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
  expect(wrapper.get('[data-testid="band-status"]').text()).toContain('WORKED ON 20m')
  const bandHeader = wrapper.findAll('th').find(th => th.text().startsWith('Band'))!
  await bandHeader.get('button').trigger('click')
  expect(bandHeader.attributes('aria-sort')).toBe('ascending')
  expect(wrapper.findAll('.band-tag')[0]!.text()).toBe('40m')
  await bandHeader.get('button').trigger('click')
  expect(bandHeader.attributes('aria-sort')).toBe('descending')
  expect(wrapper.findAll('.band-tag')[0]!.text()).toBe('10m')
  expect(wrapper.get('[data-testid="callsign-status"]').text()).toContain('24 QSOs')
  await wrapper.get('.qso-link').trigger('click'); expect(wrapper.get('[role="dialog"]').text()).toContain('KF6UFO')
  await wrapper.get('[role="dialog"] button').trigger('click'); expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
 })
 it('shows profile and QSO pending independently and distinguishes failed from empty', async () => {
  const d = createDashboard({ profile: async () => null, qsos: async () => { throw new Error('Fixture offline') } })
  d.select('PY2DEMO', rigs[0]!.id)
  const wrapper = mount(App, { props: { dashboard: d } })
  expect(wrapper.get('[data-testid="band-status"]').text()).toContain('CHECKING 20m'); expect(wrapper.text()).toContain('Loading sample operator profile'); expect(wrapper.get('.worked-status-context').text()).toContain('Checking history')
  await flushPromises(); expect(wrapper.text()).toContain('No sample operator profile'); expect(wrapper.get('[data-testid="callsign-status"]').text()).toContain('UNKNOWN'); expect(wrapper.text()).not.toContain('0 sample contacts')
  const empty = createDashboard({ profile: async () => profiles.VK3DEMO!, qsos: async () => ({ records: [], complete: true }) }); empty.select('VK3DEMO', rigs[0]!.id)
  const w = mount(App, { props: { dashboard: empty } }); await flushPromises(); expect(w.get('[data-testid="callsign-status"]').text()).toContain('NEW CALLSIGN'); expect(w.get('[data-testid="callsign-status"]').text()).toContain('0 QSOs')
 })
})

it('renders new-band, incomplete and unknown states from the latest selection snapshot', async () => {
 const d = createDashboard({ profile: async () => null, qsos: async () => ({ records: sampleQsos('JA2HDE'), complete: true }) })
 d.select('JA2HDE', rigs[0]!.id, { band: '6m' })
 const w = mount(App, { props: { dashboard: d } }); await flushPromises()
 expect(w.get('[data-testid="band-status"]').text()).toContain('NEW ON 6m')
 d.state.qsos = { status: 'loaded', data: [], complete: false }; await w.vm.$nextTick()
 expect(w.get('[data-testid="band-status"]').text()).toContain('UNKNOWN ON 6m')
 expect(w.get('[data-testid="band-status"]').text()).not.toContain('NEW')
 d.select('JA2HDE', rigs[1]!.id, { band: null }); await flushPromises()
 expect(w.get('[data-testid="band-status"]').text()).toContain('UNKNOWN')
})

it('keeps compact indicators honest through incomplete, observed and reconciled history', async () => {
 const d = createDashboard({ profile: async () => null, qsos: async () => ({ records: [], complete: true }) })
 d.select('K1TEST', rigs[0]!.id, { band: '15 m' })
 const w = mount(App, { props: { dashboard: d } }); await flushPromises()
 const call = () => w.get('[data-testid="callsign-status"]'), band = () => w.get('[data-testid="band-status"]')
 expect(call().text()).toContain('NEW CALLSIGN'); expect(band().text()).toContain('NEW ON 15m')
 expect(call().text()).toContain('0 QSOs'); expect(band().text()).toContain('0 QSOs')
 for (const history of [{ status: 'pending' }, { status: 'error', message: 'offline' }, { status: 'loaded', data: [], complete: false }] as const) {
  d.state.qsos = { ...history, ...('data' in history ? { data: [] } : {}) }; await w.vm.$nextTick()
  expect(call().text()).not.toContain('NEW'); expect(band().text()).not.toContain('NEW')
  expect(call().text()).not.toContain('0 QSOs'); expect(band().text()).not.toContain('0 QSOs')
  expect(call().text()).toContain(history.status === 'pending' ? 'CHECKING' : 'UNKNOWN')
 }
 const known = { ...sampleQsos('JA2HDE')[0]!, band: '15m', verifiedHistory: true }
 const observed = { ...known, id: 'observed', observed: true, verifiedHistory: false }
 d.state.qsos = { status: 'loaded', data: [known, observed], complete: false }; await w.vm.$nextTick()
 expect(call().text()).toContain('WORKED BEFORE'); expect(call().text()).toContain('2 QSOs')
 expect(band().text()).toContain('WORKED ON 15m'); expect(band().text()).toContain('2 QSOs')
 expect(w.get('.worked-status-context').text()).toContain('1 historical · 1 observed locally · awaiting reconciliation')
 d.state.history[0]!.band = '17m'; await w.vm.$nextTick()
 expect(band().text()).toContain('UNKNOWN ON 17m'); expect(band().text()).not.toContain('0 QSOs')
 d.state.history[0]!.band = '15m'
 d.state.qsos = { status: 'loaded', data: [known, { ...observed, observed: false }], complete: true }; await w.vm.$nextTick()
 expect(call().text()).toContain('2 QSOs'); expect(band().text()).toContain('2 QSOs')
 expect(w.get('.worked-status-context').text()).toContain('Complete history')
 expect(w.get('.worked-status-context').text()).not.toContain('awaiting')
 w.unmount()
})
