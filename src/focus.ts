import { reactive } from 'vue'
import { rigs } from './fixtures'
import { mockProviders } from './providers'
import type { Entry, Lookup, Profile, Providers, Qso } from './types'
export function createDashboard(providers: Providers = mockProviders) {
 const state = reactive({ call: '', history: [] as Entry[], rigSelections: {} as Record<string, string>, profile: { status: 'pending' } as Lookup<Profile>, qsos: { status: 'pending' } as Lookup<Qso[]>, source: 'radio' as 'radio' | 'browse', decodes: 0 })
 let generation = 0, sequence = 0
 function load(call: string, profileDelay?: number, qsoDelay?: number) {
  const token = ++generation
  state.call = call; state.profile = { status: 'pending' }; state.qsos = { status: 'pending' }
  providers.profile(call, profileDelay).then(data => { if (token === generation) state.profile = data ? { status: 'loaded', data } : { status: 'empty' } }).catch(() => { if (token === generation) state.profile = { status: 'error', message: 'Sample profile lookup unavailable.' } })
  providers.qsos(call, qsoDelay).then(data => { if (token === generation) state.qsos = data.records.length || !data.complete ? { status: 'loaded', data: data.records, complete: data.complete } : { status: 'empty' } }).catch(error => { if (token === generation) state.qsos = { status: 'error', message: error instanceof Error ? error.message : 'Sample QSO lookup unavailable.' } })
 }
 function sort() { state.history.sort((a,b) => b.recency - a.recency) }
 function select(raw: string, rigId: string, options: { at?: number; profileDelay?: number; qsoDelay?: number; band?: string | null } = {}) {
  const call = raw.trim().toUpperCase()
  if (!/^(?=.*[A-Z])(?=.*\d)[A-Z0-9/]{3,15}$/.test(call) || !rigs.some(r => r.id === rigId)) return
  state.rigSelections[rigId] = call
  const existing = state.history.find(e => e.call === call)
  const data = { call, rigId, band: options.band === undefined ? rigs.find(r => r.id === rigId)!.band : options.band, selectedAt: options.at ?? Date.now(), recency: ++sequence }
  if (existing) Object.assign(existing, data); else state.history.push(data)
  sort(); state.source = 'radio'; load(call, options.profileDelay, options.qsoDelay)
 }
 function browse(call: string) {
  const entry = state.history.find(e => e.call === call); if (!entry) return
  entry.browsedAt = Date.now(); state.source = 'browse'; load(call)
 }
 function decode() { state.decodes++ }
 function retry() { load(state.call) }
 function race() { select('DL1DEMO', rigs[1]!.id, { profileDelay: 2200, qsoDelay: 2800 }); select('JA2HDE', rigs[0]!.id, { profileDelay: 200, qsoDelay: 400 }) }
 return { state, select, browse, decode, retry, race }
}
export type Dashboard = ReturnType<typeof createDashboard>
