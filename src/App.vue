<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import { createDashboard, type Dashboard } from './focus'
import { calls, profiles, rigs, sampleQsos } from './fixtures'
import type { Qso, Preferences } from './types'
import { currentBandStatus, sortQsos, bandLabel, type SortColumn, type SortDirection } from './qso'
import OperatorPortrait from './components/OperatorPortrait.vue'
import ReceiverSettings from './components/ReceiverSettings.vue'
import DiagnosticsView from './components/DiagnosticsView.vue'
import EnrichmentSettings from './components/EnrichmentSettings.vue'
import EnrichmentCard from './components/EnrichmentCard.vue'
import StationPhoto from './components/StationPhoto.vue'
import WavelogSettings from './components/WavelogSettings.vue'
import { photoUrl } from './photos'
import { operatorName, fieldText, emailLink } from './stationDetails'
import StationKeyInformation from './components/StationKeyInformation.vue'
import StationMap from './components/StationMap.vue'
import ContactDetails from './components/ContactDetails.vue'
const props = defineProps<{ dashboard?: Dashboard }>()
const dashboard = props.dashboard ?? createDashboard()
const { state } = dashboard
if (!state.call && !state.live) {
 for (const [i, call] of [...calls].reverse().entries()) dashboard.select(call, rigs[i % 3]!.id, { at: Date.now() - (6-i)*94000 })
}
const entry = computed(() => state.history.find(e => e.call === state.call)!)
const displayRigs = computed(() => state.live ? state.liveRigs : rigs)
const rig = (id: string) => displayRigs.value.find(r => r.id === id) ?? { name: id, color: '#70c9bd', mode: '' }
const radioStatus = computed(() => state.connection !== 'connected' ? 'Radio server disconnected' : state.receiver.status === 'listening' ? 'Radio receiver listening' : state.receiver.status === 'error' ? 'Radio receiver unavailable' : 'Radio receiver disabled')
const profile = computed(() => state.profile.status === 'loaded' ? state.profile.data : null)
const radioFields = computed(() => state.enrichment?.result.call === state.call ? state.enrichment.result.fields ?? {} : {})
const radioPhoto = computed(() => photoUrl(radioFields.value.image) || photoUrl(state.photoUrls[state.call]))
const radioName = computed(() => operatorName(radioFields.value))
const radioLocation = computed(() => [radioFields.value.addr2, radioFields.value.state, radioFields.value.zipcode].map(fieldText).filter(Boolean).join(', '))
const radioCountry = computed(() => fieldText(radioFields.value.country))
const radioAddress = computed(() => [fieldText(radioFields.value.addr1), radioLocation.value, radioCountry.value].filter(Boolean).join(' · '))
const radioEmail = computed(() => emailLink(radioFields.value.email))
const callAssessment = computed(() => state.qsos.status === 'empty' ? { kind: 'new', title: 'New callsign', detail: 'No contacts in this Wavelog scope' } : state.qsos.status === 'loaded' && state.qsos.complete ? { kind: 'worked', title: 'Previously worked', detail: `${state.qsos.data.length} contacts in this Wavelog scope` } : state.qsos.status === 'pending' ? { kind: 'checking', title: 'Checking callsign…', detail: 'Waiting for complete history' } : { kind: 'unknown', title: 'Worked status unknown', detail: 'History is disabled, unavailable or incomplete' })
const radioLicense = computed(() => [radioFields.value.license_class ? `Class ${radioFields.value.license_class}` : '', radioFields.value.expdate ? `Expires ${radioFields.value.expdate}` : ''].filter(Boolean).join(' · '))

const qsos = computed(() => state.qsos.status === 'loaded' ? state.qsos.data : [])
const sortColumn = ref<SortColumn>('date'), sortDirection = ref<SortDirection>('descending')
const columns: { key: SortColumn; label: string }[] = [{ key: 'date', label: 'Date / time' }, { key: 'band', label: 'Band' }, { key: 'mode', label: 'Mode' }, { key: 'sent', label: 'Sent' }, { key: 'received', label: 'Rcvd' }, { key: 'station', label: 'Station' }, { key: 'confirmed', label: 'QSL' }]
function changeSort(column: SortColumn) {
 sortDirection.value = sortColumn.value === column && sortDirection.value === 'ascending' ? 'descending' : sortColumn.value === column ? 'ascending' : column === 'date' ? 'descending' : 'ascending'
 sortColumn.value = column
}
const sortedQsos = computed(() => sortQsos(qsos.value, sortColumn.value, sortDirection.value))
const visibleContacts = ref(100)
const renderedQsos = computed(() => state.radioWorkspace ? sortedQsos.value.slice(0, visibleContacts.value) : sortedQsos.value)
watch([() => state.call, () => state.wavelog?.result.lookupId], () => { visibleContacts.value = 100; detail.value = null })
const wavelogResult = computed(() => state.wavelog?.result)
const wavelogDisabled = computed(() => state.radioWorkspace && state.wavelog?.config.enabled === false)
const historySource = computed(() => state.radioWorkspace ? 'this Wavelog scope' : 'sample logbook')
const historyNote = computed(() => !state.radioWorkspace ? 'Complete demonstration logbook history · both station callsigns' : wavelogDisabled.value ? 'History is disabled · connection tests do not enable lookups.' : state.qsos.status === 'loaded' && !state.qsos.complete ? 'Incomplete Wavelog history · worked status unknown' : wavelogResult.value?.complete ? `${wavelogResult.value.scope || 'Authorized locations'} · ${wavelogResult.value.cached ? 'cached' : 'loaded from Wavelog'}` : wavelogResult.value?.message || 'Wavelog history loads independently of the station profile.')
const latestQso = computed(() => sortQsos(qsos.value, 'date', 'descending')[0])
const bandStatus = computed(() => currentBandStatus(state.qsos, entry.value?.band, state.radioWorkspace ? 'Wavelog' : 'sample'))
const bands = computed(() => [...new Set(sortQsos(qsos.value, 'band', 'ascending').map(q => q.band))])
const modes = computed(() => [...new Set(qsos.value.map(q => q.mode))].sort())
const confirmations = computed(() => ({ confirmed: qsos.value.filter(q => q.confirmed === true).length, unknown: qsos.value.filter(q => q.confirmed === null).length }))
const detailsError = ref(''), detailsBusy = ref(false)
watch(() => state.call, () => { detailsError.value = '' })
async function refreshDetails() {
 detailsError.value = ''; detailsBusy.value = true
 try {
  const response = await fetch('/api/enrichment/refresh', { method: 'POST' })
  if (!response.ok) throw new Error()
  dashboard.applySnapshot(await response.json(), false)
 } catch { detailsError.value = 'Station details could not be refreshed. Check the server connection and try again.' }
 finally { detailsBusy.value = false }
}
const detail = ref<Qso | null>(null)
let previousFocus: HTMLElement | null = null
watch(detail, async value => {
 if (value) { previousFocus = document.activeElement as HTMLElement; await nextTick(); document.querySelector<HTMLButtonElement>('.detail-dialog button')?.focus() }
 else previousFocus?.focus()
})
function trapDialog(event: KeyboardEvent) {
 if (event.key !== 'Tab') return
 const controls = document.querySelector('.detail-dialog')?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], [tabindex="0"]')
 if (!controls?.length) return
 const first = controls[0]!, last = controls[controls.length - 1]!
 if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
 else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}
const chosenCall = ref('JA2HDE'), chosenRig = ref(rigs[0]!.id), slow = ref(false), demoOpen = ref(false)
const deskPreferenceKey = 'wsjtx-dashboard.station-desk'
function readPreference(key: string) { try { return localStorage.getItem(key) } catch { return null } }
const deskOpen = ref(readPreference(deskPreferenceKey) === 'open')
const theme = ref(readPreference('wsjtx-dashboard.theme') === 'light' ? 'light' : 'dark')
watch(deskOpen, value => { try { localStorage.setItem(deskPreferenceKey, value ? 'open' : 'closed') } catch { /* Session preference still works without storage. */ } })
watch(theme, value => { try { localStorage.setItem('wsjtx-dashboard.theme', value) } catch { /* Session-only fallback. */ } })
const demoDialog = ref<HTMLDialogElement | null>(null)
watch(demoOpen, async open => {
 await nextTick()
 if (open) demoDialog.value?.showModal()
 else demoDialog.value?.close()
})
function trapDemoDialog(event: KeyboardEvent) {
 if (event.key !== 'Tab') return
 const controls = demoDialog.value?.querySelectorAll<HTMLElement>('button:not(:disabled), select:not(:disabled), input:not(:disabled)')
 if (!controls?.length) return
 const first = controls[0]!, last = controls[controls.length - 1]!
 if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
 else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}
const view = ref<'station' | 'diagnostics' | 'settings'>('station')
const draft = ref<Preferences>({ ...state.preferences })
const saved = ref(''), saving = ref(false)
watch(() => JSON.stringify([state.sample, state.preferences]), () => {
 if (!state.live) return
 theme.value = state.preferences.appearance; deskOpen.value = state.preferences.radioStrip
 draft.value = { ...state.preferences }
})
async function saveSettings() {
 saving.value = true; saved.value = ''
 try { await dashboard.saveSettings({ ...draft.value, title: state.preferences.title }); saved.value = 'Saved on this server. All connected browsers updated.' }
 catch (error) { saved.value = error instanceof Error ? error.message : 'Save failed' }
 finally { saving.value = false }
}
const notice = ref('Ready for your next selection.')
const utc = (time: number | string) => new Date(time).toISOString().slice(11,19)
function simulate() { if (state.sample) { void dashboard.selectSample(chosenCall.value, chosenRig.value); demoOpen.value = false; return } dashboard.select(chosenCall.value, chosenRig.value, slow.value ? { profileDelay: 2400, qsoDelay: 4000 } : {}); notice.value = `Simulated selection: ${chosenCall.value}`; demoOpen.value = false }
function interleave() { dashboard.select('DL1DEMO', rigs[0]!.id); dashboard.select('W7DEMO', rigs[1]!.id); dashboard.select('VK3DEMO', rigs[2]!.id); notice.value = 'Three interleaved selections received. Field station is latest.' }
</script>
<template>
 <div class="app-shell" :class="[{ 'station-desk-open': deskOpen }, `theme-${theme}`]">
  <header class="topbar">
   <div class="brand"><span class="brand-icon" aria-hidden="true">⌁</span><h1>WSJT-X <span>Dashboard</span></h1></div>
   <span class="demo-status">{{ state.sample ? `Step 4 preview · Sample workspace · ${state.connection}` : state.live ? radioStatus : 'Demo · No live connections' }}</span>
   <nav class="console-controls" aria-label="Workspace views">
    <button v-for="tab in (['station', 'diagnostics', 'settings'] as const)" :key="tab" class="btn console-button" :aria-current="view === tab ? 'page' : undefined" @click="view = tab">{{ tab[0]!.toUpperCase() + tab.slice(1) }}</button>
    <button class="btn console-button" :aria-pressed="theme === 'light'" @click="theme = theme === 'dark' ? 'light' : 'dark'">Theme: {{ theme === 'dark' ? 'Dark' : 'Light' }}</button>
    <button v-if="!state.live || state.sample" class="btn console-button" aria-haspopup="dialog" aria-controls="demo-tools" :aria-expanded="demoOpen" @click="demoOpen = true">Demo tools</button>
   </nav>
  </header>
  <section v-show="deskOpen" id="station-desk" class="rig-strip" :aria-label="state.sample ? 'Simulated rig identities' : state.live ? 'WSJT-X rig identities' : 'Simulated rig identities'"><div class="section-eyebrow">STATION DESK <span>{{ state.sample ? 'Simulated radios · no receiver' : state.live ? `${displayRigs.length} WSJT-X network IDs · latest Status` : '3 simulated rigs' }}</span></div><div class="rigs"><div v-for="r in displayRigs" :key="r.id" class="rig-chip" :title="r.id" :style="{ '--rig-color': r.color }"><i></i><strong>{{ r.name }}{{ !state.sample && 'online' in r && !r.online ? ' · Closed' : '' }}</strong><span>{{ r.band ? bandLabel(r.band) : 'Band unknown' }} · {{ r.mode }}</span><code>{{ state.rigSelections[r.id] || 'Idle' }}</code></div></div></section>
  <dialog v-if="!state.live || state.sample" ref="demoDialog" id="demo-tools" class="demo-dialog" @keydown="trapDemoDialog" aria-labelledby="demo-tools-title" aria-describedby="demo-tools-description" @close="demoOpen = false" @click="event => { if (event.target === demoDialog) demoOpen = false }">
   <div class="demo-dialog-heading"><h2 id="demo-tools-title">Demo tools</h2><button class="btn console-button" @click="demoOpen = false" autofocus>Close demo tools</button></div>
   <p id="demo-tools-description">These tools affect demonstration data only. No radios, live services or logbooks are connected.</p>
   <div class="demo-action"><h3>Choose a station and radio</h3><div class="control-fields"><label>Callsign<select aria-label="Callsign" v-model="chosenCall" class="form-select form-select-sm"><option v-for="call in calls" :key="call">{{ call }}</option></select></label><label>Simulated radio<select aria-label="Simulated radio" v-model="chosenRig" class="form-select form-select-sm"><option v-for="r in rigs" :value="r.id" :key="r.id">{{ r.name }}</option></select></label><label v-if="!state.sample" class="slow-control"><input type="checkbox" v-model="slow" class="form-check-input"> Slow lookups</label></div><p>Display the chosen station immediately, then load its sample profile and contacts. Slow lookups make the waiting states easier to review.</p><button class="btn btn-success btn-sm" @click="simulate">Simulate a station selection</button></div>
   <div v-if="!state.sample" class="demo-action"><button class="btn btn-outline-light btn-sm" @click="interleave">Simulate selections from three radios</button><p>Select DL1DEMO, W7DEMO, then VK3DEMO on separate radios. The last selection appears first.</p></div>
   <div v-if="!state.sample" class="demo-action"><button class="btn btn-outline-light btn-sm" @click="dashboard.decode(); notice = 'Ordinary decode ignored. Focus and history unchanged.'">Simulate an ordinary decode</button><p>A received signal should leave the displayed station and Focus History unchanged.</p></div>
   <div v-if="!state.sample" class="demo-action"><button class="btn btn-outline-light btn-sm" @click="dashboard.race(); notice = 'Slow DL1DEMO → fast JA2HDE. Latest selection must win.'">Test responses arriving out of order</button><p>Select slow DL1DEMO, then fast JA2HDE. Delayed results must never replace the newer station.</p></div>
   <p class="demo-notice" role="status">{{ notice }} · {{ state.decodes }} ordinary decodes ignored.</p><small>Sample cases: VK3DEMO has no contacts; PY2DEMO has a history error; ZS6DEMO has no profile.</small>
  </dialog>
  <p v-if="state.live && state.connection !== 'connected'" class="connection-note" role="status">Connecting/reconnecting to the server · displayed state may be stale. Changes require a connection.</p><p v-if="state.storageError" class="connection-note" role="alert">{{ state.storageError }}</p><p v-if="state.navigationError" class="connection-note" role="alert">{{ state.navigationError }}</p>
  <p v-if="state.sample" class="sample-data-note">Sample station &amp; contact data · fictional profiles and illustrative callsigns</p>
  <DiagnosticsView v-if="view === 'diagnostics'" :dashboard="dashboard"/>
  <section v-if="view === 'settings'" class="utility-panel" aria-label="Settings"><span class="section-eyebrow">YOUR WORKSPACE</span><h2>Settings</h2><p>These controls save real preferences on the server and synchronize all browsers.</p><form @submit.prevent="saveSettings" class="settings-form" aria-label="Workspace preferences"><label>Saved appearance<select class="form-select" v-model="draft.appearance"><option value="dark">Dark</option><option value="light">Light</option></select></label><label class="check-setting"><input type="checkbox" v-model="draft.radioStrip"> Show compact radio status strip</label><button class="btn console-button" type="button" :aria-expanded="deskOpen" aria-controls="station-desk" @click="deskOpen = !deskOpen">Station Desk <span aria-hidden="true">{{ deskOpen ? '▴' : '▾' }}</span></button><button class="btn btn-success" :disabled="saving || state.connection !== 'connected'">{{ saving ? 'Saving…' : 'Save workspace settings' }}</button><p role="status">{{ saved }}</p></form><ReceiverSettings :dashboard="dashboard"/><EnrichmentSettings :dashboard="dashboard"/><WavelogSettings :dashboard="dashboard"/><h3>Installation configuration</h3><p>HTTP address and port are read from <code>config.toml</code>; edit the file and restart the server. Theme and the Station Desk preview affect this browser; use Save above for shared defaults.</p><p>Enrichment and Wavelog settings apply immediately. QSO submission and forwarding remain future steps. Callbook credentials and the Wavelog token stay on this server.</p></section>
  <main v-show="view === 'station'" class="desk" :class="{ 'radio-desk': state.radioWorkspace }">
   <section v-if="!state.call && state.live" class="station-panel waiting-station" aria-label="Waiting for radio selection"><h2>Waiting for a WSJT-X selection</h2><p>{{ radioStatus }}. The first Status from each radio establishes a baseline; a later valid DX callsign change displays the station.</p><p>Select a different DX callsign in WSJT-X after its first Status has arrived. Enrichment and Wavelog history load after selection when enabled. No logging or radio commands.</p><p v-if="state.receiver.error" class="error-text">{{ state.receiver.error }}</p></section>
   <section v-else class="station-panel" aria-label="Focused station">
    <div class="station-main" :class="{ 'station-main-radio': state.radioWorkspace }"><div class="station-primary">
    <div class="station-overview" :class="{ 'has-radio-photo': state.radioWorkspace }"><StationPhoto v-if="state.radioWorkspace" :call="state.call" :src="radioPhoto"/><div v-if="!state.radioWorkspace" class="portrait-column"><OperatorPortrait :initials="profile?.initials || '··'" :color="profile?.color || '#7d909d'"/><div class="photo-caption">{{ state.radioWorkspace ? 'Callbook photo not connected' : 'Operator image placeholder' }} <span>{{ state.radioWorkspace ? 'UNAVAILABLE' : 'DEMO' }}</span></div></div><div class="station-identity"><div class="callsign-row"><h2 data-testid="focused-call">{{ state.call }}</h2><span class="small-label">{{ state.sample ? 'SAMPLE' : state.live ? 'RADIO' : 'SAMPLE' }}</span></div><div v-if="state.radioWorkspace && (radioName || radioAddress || radioLicense || radioEmail)" class="radio-callbook-identity"><h3 v-if="radioName">{{ radioName }}</h3><p v-if="radioAddress" class="location compact-address">{{ radioAddress }}</p><div class="identity-links"><span v-if="radioLicense" class="radio-license">{{ radioLicense }}</span><a v-if="state.enrichment?.result.providers?.qrz?.status === 'loaded'" :href="`https://www.qrz.com/db/${encodeURIComponent(state.call)}`" target="_blank" rel="noopener noreferrer">QRZ profile ↗</a><a v-if="radioEmail" :href="radioEmail">✉ {{ radioFields.email }}</a></div></div><template v-else-if="profile"><h3>{{ profile.name }}</h3><p class="location">{{ profile.location }}<br><strong>{{ profile.country }}</strong> <span class="grid-locator">{{ profile.grid }}</span></p><p class="operator-bio">{{ profile.bio }}</p></template><div v-else-if="state.profile.status === 'pending'" class="profile-pending" role="status"><div class="skeleton wide"></div><div class="skeleton"></div><p>Loading sample operator profile…</p></div><p v-else-if="state.profile.status === 'empty'" class="muted-state">{{ state.radioWorkspace ? 'Available operator and license information appears in Details.' : 'No sample operator profile available.' }}</p><p v-else class="error-text">Profile unavailable. <button class="text-button" @click="dashboard.retry">Retry</button></p><div class="origin-card" v-if="entry"><span class="rig-dot" :style="{ background: rig(entry.rigId).color }"></span><div><strong>{{ rig(entry.rigId).name }}</strong><span>{{ entry.band ? bandLabel(entry.band) : 'Band unknown' }} · {{ entry.mode || rig(entry.rigId).mode }} <span class="origin-separator">/</span> {{ state.sample ? 'Sample selection' : state.live ? 'Radio selection' : 'Last radio selection' }} {{ utc(entry.selectedAt) }} UTC</span><small>{{ entry.rigId }}</small></div></div><div v-if="state.source === 'browse'" class="browse-note">Dashboard browsing only · radio selections unchanged</div></div></div>
    <section class="lookup-status" :aria-label="state.radioWorkspace ? 'Lookup status' : undefined"><h3 v-if="state.radioWorkspace">Lookup status</h3>
    <div class="worked-summary" aria-live="polite"><template v-if="state.qsos.status === 'loaded' && state.qsos.complete"><div class="worked-title"><span class="worked-check">✓</span><div><strong>{{ state.live && !state.radioWorkspace ? 'Sample: worked before' : 'Worked before' }}</strong><span>{{ state.radioWorkspace ? `${qsos.length} contacts · ${bands.length} bands · latest ${latestQso!.date.slice(0,10)} UTC` : 'Complete sample history' }}</span></div></div><div class="summary-stat"><strong>{{ qsos.length }}</strong><span>CONTACTS</span></div><div class="summary-stat"><strong>{{ bands.length }}</strong><span>BANDS</span></div><div class="summary-last"><span>LATEST CONTACT</span><strong>{{ latestQso!.date.slice(0,10) }}</strong><small>{{ utc(latestQso!.date) }} UTC · {{ latestQso!.band }} {{ latestQso!.mode }}</small></div></template><template v-else-if="state.qsos.status === 'pending'"><span class="spinner-border spinner-border-sm"></span> Loading {{ state.radioWorkspace ? 'Wavelog' : 'sample' }} QSO history…</template><template v-else-if="state.qsos.status === 'empty'"><span class="worked-check">○</span><div><strong>Not worked in {{ historySource }}</strong><p class="mb-0">Lookup complete · 0 {{ state.radioWorkspace ? 'Wavelog' : 'sample' }} contacts</p></div></template><template v-else-if="wavelogDisabled"><span>Wavelog history is disabled · worked-before status unknown</span><button class="text-button" @click="view = 'settings'">Open Wavelog settings</button></template><template v-else><span class="error-text">QSO history unavailable · worked-before status unknown</span><button class="text-button" @click="dashboard.retry">Retry lookup</button></template></div>
    <div class="lookup-status-cards">
    <div class="band-status" :data-state="bandStatus.kind" data-testid="band-status" aria-live="polite"><strong>{{ state.live && !state.radioWorkspace ? 'Sample: ' : '' }}{{ bandStatus.title }}</strong><span>{{ bandStatus.detail }}</span><small v-if="state.radioWorkspace" class="call-status-label" :data-state="callAssessment.kind">{{ callAssessment.title }}</small><small v-if="!state.radioWorkspace">Sample QSO comparison · band from latest {{ state.sample ? 'simulated WSJT-X' : state.live ? 'radio' : 'simulated WSJT-X' }} selection for {{ state.call }}</small></div>

    </div>
    <div v-if="state.radioWorkspace && state.qsos.status === 'loaded' && state.qsos.complete" class="contact-overview" aria-label="Complete contact history overview"><div><span class="section-eyebrow">WORKED BANDS</span><div class="contact-tags"><span v-for="band in bands" :key="band">{{ bandLabel(band) }}</span></div></div><div><span class="section-eyebrow">MODES</span><div class="contact-tags"><span v-for="mode in modes" :key="mode">{{ mode }}</span></div></div><div class="confirmation-overview"><span class="section-eyebrow">QSL STATUS</span><strong v-if="confirmations.unknown !== qsos.length">{{ confirmations.confirmed }} confirmed</strong><strong v-else>Confirmation unavailable</strong><small v-if="confirmations.unknown">{{ confirmations.unknown }} unavailable</small></div></div>
    </section>
    <StationKeyInformation v-if="state.radioWorkspace" :enrichment="state.enrichment" :call="state.call"/>
    </div><div class="station-details-column">
    <p v-if="detailsError" class="station-refresh-error" role="alert">{{ detailsError }}</p>
    <EnrichmentCard v-if="state.radioWorkspace" :enrichment="state.enrichment" :call="state.call" :connected="state.connection === 'connected' && !detailsBusy" @refresh="refreshDetails"/>
    </div></div>
    <StationMap v-if="state.radioWorkspace" :call="state.call" :entry="entry" :enrichment="state.enrichment"/>
    <div class="qso-heading"><div><h3>Previous contacts <span>{{ state.qsos.status === 'loaded' ? qsos.length : '—' }}</span></h3><p>{{ historyNote }}</p></div><div class="qso-tools"><button v-if="state.radioWorkspace && !wavelogDisabled" class="text-button" @click="dashboard.retry">Refresh Wavelog history</button><span class="utc-label">ALL TIMES UTC</span></div></div>
    <div class="qso-scroll" tabindex="0" :aria-label="state.radioWorkspace ? 'Scrollable Wavelog QSO history' : 'Scrollable sample QSO history'"><template v-if="state.qsos.status === 'loaded'"><table class="table qso-table"><thead><tr><th v-for="column in columns" :key="column.key" :aria-sort="sortColumn === column.key ? sortDirection : 'none'"><button class="sort-button" @click="changeSort(column.key)">{{ column.label }} <span aria-hidden="true">{{ sortColumn === column.key ? (sortDirection === 'ascending' ? '↑' : '↓') : '↕' }}</span></button></th><th><span class="visually-hidden">Details</span></th></tr></thead><tbody><tr v-for="q in renderedQsos" :key="q.id"><td><button class="qso-link" @click="detail = q" :aria-label="`Contact details ${q.date}`">{{ q.date.slice(0,10) }}<small>{{ utc(q.date) }}</small></button></td><td><span class="band-tag">{{ q.band }}</span></td><td>{{ q.mode }}</td><td class="reports">{{ q.sent }}</td><td class="reports">{{ q.received }}</td><td>{{ q.station }}</td><td><span :class="q.confirmed ? 'confirmed' : 'unconfirmed'">{{ q.confirmed === null ? 'Unavailable' : q.confirmed ? '✓ Confirmed' : state.radioWorkspace ? 'Unconfirmed' : 'Pending' }}</span></td><td><button class="text-button detail-arrow" @click="detail = q" :aria-label="`Open QSO ${q.id}`">↗</button></td></tr></tbody></table><div v-if="state.radioWorkspace && state.qsos.status === 'loaded'" class="qso-load-more"><p v-if="state.qsos.message">{{ state.qsos.message }}</p><p>Showing {{ renderedQsos.length }} of {{ qsos.length }} loaded contacts<span v-if="!state.qsos.complete"> · Incomplete history</span></p><button v-if="renderedQsos.length < qsos.length" class="btn console-button" @click="visibleContacts += 100">Show next 100 contacts</button></div></template><div v-else-if="state.qsos.status === 'pending'" class="table-loading" role="status"><div class="skeleton" v-for="i in 5" :key="i"></div><p>Retrieving contacts independently of the profile…</p></div><div v-else-if="state.qsos.status === 'empty'" class="empty-state"><span>◎</span><h4>A new connection</h4><p>No contacts found in this station’s complete {{ state.radioWorkspace ? 'Wavelog' : 'sample' }} history.</p></div><div v-else class="empty-state error-state"><span>◇</span><h4>{{ wavelogDisabled ? 'Wavelog history is disabled' : 'History couldn’t be loaded' }}</h4><p>{{ state.qsos.message }}</p><p v-if="!wavelogDisabled">Failed lookups never count as zero contacts.</p><button v-if="!wavelogDisabled" class="btn btn-outline-light btn-sm" @click="dashboard.retry">{{ state.radioWorkspace ? 'Retry lookup' : 'Retry sample lookup' }}</button></div></div>
    <div class="panel-footer"><span>{{ state.radioWorkspace ? '◈ Wavelog is the source of record' : '◈ Fictional contact records' }}</span><span>{{ state.radioWorkspace ? 'Contacts cached in memory' : state.sample ? 'Shared workspace · saved on server' : state.live ? 'Shared history · saved on server' : 'In-memory session · resets on reload' }}</span></div>
   </section>
   <aside class="history-panel" aria-label="Focus History"><div class="history-scroll" tabindex="0" aria-label="Scrollable Focus History"><p v-if="!state.history.length" class="history-intro">{{ state.radioWorkspace ? 'Waiting for a changed DX Call. Initial Status and decodes do not add history entries.' : 'No selections yet. Use Demo tools to select a sample station.' }}</p><button v-for="item in state.history" :key="item.call" class="history-entry" :class="{ active: state.call === item.call }" @click="dashboard.browse(item.call)" :aria-pressed="state.call === item.call" :data-testid="`history-${item.call}`"><StationPhoto v-if="state.radioWorkspace" :call="item.call" :src="state.photoUrls[item.call]" compact/><OperatorPortrait v-else :initials="profiles[item.call]?.initials || '?'" :color="profiles[item.call]?.color || '#aaa'" compact/><div class="history-entry-main"><div class="history-call"><strong>{{ item.call }}</strong><span v-if="state.call === item.call">FOCUSED</span></div><div class="history-location">{{ state.radioWorkspace ? 'Select to view enrichment' : state.live ? (profiles[item.call] ? 'Sample: ' : 'Profile not connected') : '' }}{{ state.radioWorkspace ? '' : profiles[item.call]?.country || (state.live ? '' : 'Unknown') }} <span v-if="!state.radioWorkspace && profiles[item.call]?.grid">· {{ profiles[item.call]?.grid }}</span></div><div class="history-qso-hint" v-if="!state.radioWorkspace && (!state.live || profiles[item.call])">{{ item.call === 'PY2DEMO' ? 'Sample QSO history unavailable' : `${sampleQsos(item.call).length} sample contacts` }}</div><div v-else class="history-qso-hint">{{ wavelogResult?.call === item.call && wavelogResult.complete ? `${wavelogResult.total} Wavelog QSOs` : state.wavelog?.config.enabled ? 'Select to load Wavelog history' : wavelogDisabled ? 'Wavelog history disabled' : 'Wavelog history not connected' }}</div><div class="history-rig"><i :style="{ background: rig(item.rigId).color }"></i>{{ rig(item.rigId).name }}<time>{{ utc(item.selectedAt) }}</time></div><small v-if="item.browsedAt" class="browsed-label">Browsed {{ utc(item.browsedAt) }} · radio time preserved</small><small v-else class="browsed-label">{{ state.sample ? 'Simulated selection' : state.live ? 'Radio selection' : 'Simulated selection' }}</small></div></button></div><div class="history-footer"><span class="mint-dot">●</span> Deliberate focus only. Decodes stay quiet.<small>Ordered only by {{ state.sample ? 'simulated radio' : state.live ? 'radio' : 'simulated radio' }} selections. Browsing keeps order.</small></div></aside>
  </main><footer class="app-footer"><span>WSJT-X Dashboard <span class="footer-version">/ STEP 4 PREVIEW / STATION DETAILS</span></span><span>Built for the operator. Ready for your next contact.</span></footer>
 </div>
 <div v-if="detail" class="detail-backdrop" :class="`theme-${theme}`" @click.self="detail = null" @keydown.esc="detail = null" @keydown="trapDialog"><section role="dialog" aria-modal="true" aria-labelledby="detail-title" class="detail-dialog" tabindex="-1"><div class="d-flex justify-content-between align-items-start"><div><span class="section-eyebrow">{{ state.radioWorkspace ? 'WAVELOG CONTACT DETAILS' : 'SAMPLE CONTACT DETAILS' }}</span><h2 id="detail-title">{{ state.call }}</h2></div><button class="btn btn-outline-light btn-sm" @click="detail = null" autofocus>Close</button></div><ContactDetails :qso="detail" :radio="state.radioWorkspace"/><p class="mb-0 text-secondary">{{ state.radioWorkspace ? 'Read-only record from Wavelog. No logging or radio commands.' : 'Illustrative record only. No logging or radio commands.' }}</p></section></div>
</template>
