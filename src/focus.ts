import { reactive } from 'vue'
import { rigs } from './fixtures'
import { mockProviders } from './providers'
import type { Entry, Lookup, Profile, Providers, Qso, LiveRig, Snapshot, Preferences } from './types'
export function createDashboard(providers: Providers = mockProviders, live = false) {
 const state = reactive({ qso: undefined as import('./types').QsoServiceState | undefined, qsoHistory: undefined as import('./types').HistorySelectionState | undefined, wavelog: undefined as import('./types').WavelogState | undefined, photoUrls: {} as Record<string, string>, enrichment: undefined as import('./types').EnrichmentState | undefined, radioWorkspace: false, storageError: '' as string | null, counters: { packets: 0, malformed: 0, decodes: 0 } as Snapshot['counters'], sample: false, preferences: { title: 'My station', appearance: 'dark', radioStrip: false } as Preferences, call: '', history: [] as Entry[], rigSelections: {} as Record<string, string>, profile: { status: 'pending' } as Lookup<Profile>, qsos: { status: 'pending' } as Lookup<Qso[]>, source: 'radio' as 'radio' | 'browse', decodes: 0, live, liveRigs: [] as LiveRig[], connection: 'connecting' as 'connecting' | 'connected' | 'disconnected', receiver: { status: 'disabled', error: null } as Snapshot['receiver'], navigationError: '' })
 let generation = 0, sequence = 0
 function load(call: string, profileDelay?: number, qsoDelay?: number) {
  const token = ++generation
  state.call = call; state.profile = { status: 'pending' }; state.qsos = { status: 'pending' }
  if (state.radioWorkspace) { state.profile = { status: 'empty' }; return }
  const profileLookup = providers.profile(call, profileDelay)
  const qsoLookup = providers.qsos(call, qsoDelay)
  profileLookup.then(data => { if (token === generation) state.profile = data ? { status: 'loaded', data } : { status: 'empty' } }).catch(() => { if (token === generation) state.profile = { status: 'error', message: 'Sample profile lookup unavailable.' } })
  qsoLookup.then(data => { if (token === generation) state.qsos = data.records.length || !data.complete ? { status: 'loaded', data: data.records, complete: data.complete } : { status: 'empty' } }).catch(error => { if (token === generation) state.qsos = { status: 'error', message: error instanceof Error ? error.message : 'Sample QSO lookup unavailable.' } })
 }
 function sort() { state.history.sort((a,b) => b.recency - a.recency) }
 function select(raw: string, rigId: string, options: { at?: number; profileDelay?: number; qsoDelay?: number; band?: string | null } = {}) {
  if (live) return
  const call = raw.trim().toUpperCase()
  if (!/^(?=.*[A-Z])(?=.*\d)[A-Z0-9/]{3,15}$/.test(call) || !rigs.some(r => r.id === rigId)) return
  state.rigSelections[rigId] = call
  const existing = state.history.find(e => e.call === call)
  const data = { call, rigId, mode: rigs.find(r => r.id === rigId)!.mode, band: options.band === undefined ? rigs.find(r => r.id === rigId)!.band : options.band, selectedAt: options.at ?? Date.now(), recency: ++sequence }
  if (existing) Object.assign(existing, data); else state.history.push(data)
  sort(); state.source = 'radio'; load(call, options.profileDelay, options.qsoDelay)
 }
 let browseRequest = 0
 async function browse(call: string) {
  if (live) {
   const request = ++browseRequest
   state.navigationError = ''
   try {
    const response = await fetch('/api/focus', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ call }) })
    if (!response.ok) throw new Error('Navigation unavailable. Reconnect and try again.')
    applySnapshot(await response.json(), false)
   } catch { if (request === browseRequest) state.navigationError = 'Navigation unavailable. Reconnect and try again.' }
   return
  }
  const entry = state.history.find(e => e.call === call); if (!entry) return
  entry.browsedAt = Date.now(); state.source = 'browse'; load(call)
 }
 function decode() { if (!live) state.decodes++ }
 async function retry() {
  if (!state.radioWorkspace) { load(state.call); return }
  try {
   const response = await fetch(state.qsoHistory ? '/api/qso/history/refresh' : '/api/wavelog/refresh', { method: 'POST' })
   if (!response.ok) throw new Error('Refresh failed')
   applySnapshot(await response.json(), false)
  } catch { state.navigationError = 'History refresh failed. Check the dashboard connection.' }
 }
 let historyKey = '', historyRequest = 0
 let historyAbort: AbortController | undefined
 function applyWavelog(snapshot: Snapshot) {
  if (!state.radioWorkspace) return
  const result = snapshot.qsoHistory?.result ?? snapshot.wavelog?.result
  const endpoint = snapshot.qsoHistory ? '/api/qso/history/' : '/api/wavelog/history/'
  const key = `${snapshot.epoch}:${endpoint}:${state.call}:${result?.lookupId ?? result?.status ?? 'disabled'}`
  if (historyKey === key) return
  historyKey = key
  const request = ++historyRequest, call = state.call
  historyAbort?.abort()
  if (!snapshot.qsoHistory && (snapshot.wavelog?.config.enabled === false || result?.status === 'disabled')) {
   state.qsos = { status: 'error', message: 'Wavelog history is disabled. Turn on Enable Wavelog history in Settings and save. A successful connection test does not enable history.' }; return
  }
  if (!result || result.status === 'idle') {
   state.qsos = { status: 'error', message: 'Wavelog is not connected. Configure read-only history in Settings.' }; return
  }
  if (result.call !== call || result.status === 'pending') { state.qsos = { status: 'pending' }; return }
  if (result.status === 'empty' && result.complete) { state.qsos = { status: 'empty' }; return }
  if (!result.lookupId || !result.recordCount) {
   state.qsos = { status: 'error', message: result.message || 'Wavelog history is unavailable; worked status is unknown.' }; return
  }
  state.qsos = { status: 'pending' }
  historyAbort = new AbortController()
  void fetch(`${endpoint}${encodeURIComponent(result.lookupId)}`, { signal: historyAbort.signal })
   .then(async response => {
    if (!response.ok) throw new Error('History response changed or failed')
    const body = await response.json()
    if (request !== historyRequest || call !== state.call) return
    if (body.call !== call || body.lookupId !== result.lookupId || !Array.isArray(body.records)) throw new Error('Unexpected history')
    state.qsos = { status: 'loaded', data: body.records, complete: body.complete === true, message: body.message }
   }).catch(() => {
    if (request === historyRequest && call === state.call) state.qsos = { status: 'error', message: 'QSO history could not be loaded. Retry to refresh; worked status is unknown.' }
   })
 }

 function race() { select('DL1DEMO', rigs[1]!.id, { profileDelay: 2200, qsoDelay: 2800 }); select('JA2HDE', rigs[0]!.id, { profileDelay: 200, qsoDelay: 400 }) }
 let epoch = '', revision = -1
 function applySnapshot(snapshot: Snapshot, allowEpochChange = true) {
  if (epoch && snapshot.epoch !== epoch && !allowEpochChange) return
  if (snapshot.epoch === epoch && snapshot.revision <= revision) return
  const changedEpoch = snapshot.epoch !== epoch
  epoch = snapshot.epoch; revision = snapshot.revision
  const wasRadio = state.radioWorkspace
  state.radioWorkspace = (snapshot.step ?? 0) >= 1 && !snapshot.sample
  state.sample = snapshot.sample ?? false
  if (snapshot.preferences) state.preferences = snapshot.preferences
  state.history = snapshot.history
  state.liveRigs = snapshot.rigs
  state.rigSelections = Object.fromEntries(snapshot.rigs.map(r => [r.id, r.call]))
  state.source = snapshot.source
  state.decodes = snapshot.counters.decodes
  state.receiver = snapshot.receiver
  state.counters = snapshot.counters
  state.storageError = snapshot.storageError ?? null
  state.wavelog = snapshot.wavelog
  state.qsoHistory = snapshot.qsoHistory
  state.qso = snapshot.qso
  state.enrichment = snapshot.enrichment
  state.photoUrls = snapshot.photoUrls ?? {}
  if (snapshot.call && (changedEpoch || wasRadio !== state.radioWorkspace || state.call !== snapshot.call)) load(snapshot.call)
  else if (!snapshot.call && (state.call || changedEpoch)) {
   ++generation; state.call = ''; state.profile = { status: 'pending' }; state.qsos = { status: 'pending' }
  }
  applyWavelog(snapshot)
  // Same-call radio selections update provenance through history, without
  // restarting independent lookups for every telemetry/Decode snapshot.
 }
 async function selectSample(call: string, rigId: string) {
  state.navigationError = ''
  try {
   const response = await fetch('/api/sample/select', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ call, rigId }) })
   if (!response.ok) throw new Error('Selection failed')
   applySnapshot(await response.json(), false)
  } catch { state.navigationError = 'Sample selection unavailable. Check the server connection and try again.' }
 }
 async function configureReceiver(settings: import('./types').ReceiverConfig) {
  const response = await fetch('/api/receiver', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) })
  if (!response.ok) {
   const body = await response.json().catch(() => ({}))
   throw new Error(typeof body.detail === 'string' ? body.detail : 'Receiver settings are invalid or could not be saved.')
  }
  applySnapshot(await response.json(), false)
 }
 async function restartReceiver() {
  const response = await fetch('/api/receiver/restart', { method: 'POST' })
  if (!response.ok) throw new Error('Receiver restart failed. Check server connection.')
  applySnapshot(await response.json(), false)
 }
 async function saveSettings(preferences: Preferences) {
  const response = await fetch('/api/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(preferences) })
  if (!response.ok) throw new Error('Settings could not be saved. Check values and connection.')
  applySnapshot(await response.json(), false)
 }
 return { state, configureReceiver, restartReceiver, selectSample, saveSettings, select, browse, decode, retry, race, applySnapshot }
}
export type Dashboard = ReturnType<typeof createDashboard>
