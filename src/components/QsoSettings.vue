<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Dashboard } from '../focus'
import type { QsoConfig, Snapshot } from '../types'
import StationAssociations from './StationAssociations.vue'
const props = defineProps<{ dashboard: Dashboard }>()
const settings = computed(() => props.dashboard.state.qso?.config)
const copy = (): QsoConfig => structuredClone(settings.value ? JSON.parse(JSON.stringify(settings.value)) : { history_source: 'auto', adif_path: '', adif_complete: false, logging_enabled: false, log_to_wavelog: false, recovery_seconds: 30, rigs: [] })
const draft = ref(copy()), dirty = ref(false), busy = ref(false), message = ref('')
watch(() => JSON.stringify(settings.value), () => { if (!dirty.value) draft.value = copy() })
const queue = computed(() => props.dashboard.state.qso?.queue)
const locations = computed(() => props.dashboard.state.wavelog?.connection.stations ?? [])
const associations = computed(() => props.dashboard.state.qso?.associations ?? [])
const selectedLocations = ref<Record<string,number>>({}), resolving = ref(''), resolutionMessages = ref<Record<string,string>>({})
function contactUTC(contact: Record<string,string>) {
 return `${(contact.QSO_DATE || '').replace(/^(\d{4})(\d{2})(\d{2})$/, '$1-$2-$3')} ${(contact.TIME_ON || '').replace(/^(\d{2})(\d{2})(\d{2})$/, '$1:$2:$3')} UTC`
}
function overrideFor(id: string) { return draft.value.rigs.find(row => row.id === id)?.wavelog_station_id ?? 0 }
function setOverride(id: string, event: Event) {
 const value = Number((event.target as HTMLSelectElement).value)
 let row = draft.value.rigs.find(row => row.id === id)
 if (!row) { row = { id,station_callsign:'',operator:'',wavelog_station_id:0,tx_power:'' }; draft.value.rigs.push(row) }
 row.wavelog_station_id = value; dirty.value = true
}
async function resolveExternal(id: string) {
 const call = queue.value?.recent.find(job => job.id === id)?.contact?.CALL || 'Contact'
 resolving.value = id; resolutionMessages.value[id] = ''
 try {
  const response = await fetch(`/api/qso/delivery/${encodeURIComponent(id)}/resolve-external`, { method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({station_id:selectedLocations.value[id]}) })
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'Exact contact verification failed; nothing was submitted.')
  props.dashboard.applySnapshot(body as Snapshot,false); resolutionMessages.value[id] = `${call}: exact existing QSO verified. Wavelog delivery resolved externally; ADIF and receipts preserved.`
 } catch(error) { resolutionMessages.value[id] = error instanceof Error ? error.message : 'Verification unavailable; nothing was submitted.' }
 finally { resolving.value = '' }
}
function addRig() { draft.value.rigs.push({ id: '', station_callsign: '', operator: '', wavelog_station_id: 0, tx_power: '' }); dirty.value = true }
async function action(path: string, data?: QsoConfig) {
 busy.value = true; message.value = ''
 const submitted = data ? JSON.stringify(data) : ''
 try {
  const response = await fetch(path, { method: data ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, ...(data ? { body: JSON.stringify(data) } : {}) })
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'QSO operation failed')
  props.dashboard.applySnapshot(body as Snapshot, false)
  if (data && JSON.stringify(draft.value) === submitted) { dirty.value = false; draft.value = copy() }
  message.value = data ? 'History and logging settings saved.' : 'Pending deliveries scheduled. Unknown Wavelog outcomes will only be reconciled.'
 } catch (error) { message.value = error instanceof Error ? error.message : 'Dashboard connection failed' }
 finally { busy.value = false }
}
</script>
<template>
 <section class="receiver-settings" aria-labelledby="qso-settings-title">
  <h3 id="qso-settings-title">QSO history &amp; logging</h3>
  <p>Wavelog is optional. Select a local ADIF file for independent history, or use it as a fallback when Wavelog is unavailable. Logging is a separate opt-in.</p>
  <form class="settings-form receiver-form qso-settings-form" aria-label="QSO history and logging settings" @submit.prevent="action('/api/qso/settings', draft)" @input="dirty = true" @change="dirty = true">
   <label>Preferred history<select class="form-select" v-model="draft.history_source"><option value="auto">Automatic — prefer enabled Wavelog, then ADIF</option><option value="wavelog">Wavelog only</option><option value="adif">Local ADIF only</option></select></label>
   <label>Absolute ADIF path<input class="form-control" v-model.trim="draft.adif_path" placeholder="/path/to/dashboard-log.adi"><small>Leave blank to disable local history/logging. Use a file for which the Dashboard is the only writer, separate from WSJT-X’s own log.</small></label>
   <label class="check-setting"><input type="checkbox" v-model="draft.adif_complete"> This file contains complete history for my intended scope</label>
   <p>Leave coverage unchecked for a partial export or a new local log. Incomplete files never establish a new callsign or band. ADIF confirmations are file data only; Wavelog confirmation synchronization is separate.</p>
   <label>Recovery check interval (seconds)<input class="form-control" type="number" min="5" max="3600" v-model.number="draft.recovery_seconds"></label>
   <label class="check-setting"><input type="checkbox" v-model="draft.logging_enabled"> Enable completed-QSO logging</label>
   <p>Enable after testing with an isolated Wavelog instance and arranging one uploader per destination. Enabling logging writes future valid Logged ADIF events to the configured ADIF file and, if selected below, Wavelog. Ordinary decodes never log QSOs.</p>
   <label class="check-setting"><input type="checkbox" v-model="draft.log_to_wavelog"> Deliver completed QSOs to Wavelog</label>
   <p>Uses the URL/token saved in Wavelog connection, with <strong>qso:read, station:read and qso:write</strong>. No legacy fallback is enabled. An unknown submission outcome is held for reconciliation rather than blindly resubmitted.</p>
   <div class="qso-station-associations"><StationAssociations :associations="associations"/>
    <label v-for="row in associations" :key="row.rigId">{{ row.rigId }} · location override<select class="form-select" :aria-label="`${row.rigId} · location override`" :value="overrideFor(row.rigId)" @change="setOverride(row.rigId,$event)"><option :value="0">Automatic — match station callsign</option><option v-for="station in locations" :key="station.id" :value="station.id">{{ station.callsign }} · {{ station.name }} · ID {{ station.id }}</option></select></label>
   </div>
   <details class="qso-manual-overrides"><summary>Optional station identity, power and manual overrides</summary><p>Usually unnecessary: station identity comes from Logged ADIF or verified WSJT-X Status. Set an override only for ambiguous locations or an identity WSJT-X does not report.</p>
   <fieldset v-for="(rig, index) in draft.rigs" :key="index" class="qso-rig-mapping"><legend>Rig {{ index + 1 }}</legend>
    <label>WSJT-X network ID<input class="form-control" v-model.trim="rig.id" placeholder="WSJT-X - IC7300" required></label>
    <label>Station callsign<input class="form-control" v-model.trim="rig.station_callsign" @change="rig.station_callsign = rig.station_callsign.toUpperCase()"></label>
    <label>Operator callsign<input class="form-control" v-model.trim="rig.operator" @change="rig.operator = rig.operator.toUpperCase()"></label>
    <label>Wavelog station location ID<input class="form-control" type="number" min="0" v-model.number="rig.wavelog_station_id"></label>
    <label>Configured transmit power (W, optional)<input class="form-control" v-model.trim="rig.tx_power" inputmode="decimal"></label>
    <button class="btn console-button" type="button" @click="draft.rigs.splice(index, 1); dirty = true">Remove mapping</button>
   </fieldset>
   <button class="btn console-button" type="button" @click="addRig">Add manual override</button></details>
   <button class="btn btn-success" :disabled="busy || dashboard.state.connection !== 'connected'">Save history and logging settings</button>
  </form>
  <p role="status">{{ message }}</p>
  <h4>Delivery queue</h4><p v-if="dashboard.state.qso?.error" role="alert" class="error-text">{{ dashboard.state.qso.error }}</p>
  <p v-if="dashboard.state.qso?.warning" role="status">{{ dashboard.state.qso.warning }}</p>
  <p>Completed contacts remain queued across restarts until each destination is delivered. Retry checks outstanding work; it never clears an uncertain Wavelog receipt or redirects queued contacts to a different server/file.</p>
  <button type="button" class="btn console-button" :disabled="busy" @click="action('/api/qso/retry')">Retry pending deliveries / reconcile</button>
  <ul v-if="queue?.destinations.length"><li v-for="row in queue.destinations" :key="row.destination + row.status">{{ row.destination }} · {{ row.status }} · {{ row.count }}</li></ul>
  <div v-for="job in queue?.recent" :key="job.id" :data-job-id="job.id" class="qso-delivery-job"><strong>{{ job.contact?.CALL || job.rig }} · {{ job.status }}</strong><p v-if="job.contact?.CALL">{{ contactUTC(job.contact) }} · {{ job.contact.BAND }} {{ job.contact.SUBMODE || job.contact.MODE }} · {{ job.rig }}</p><p v-if="job.message">{{ job.message }}</p><ul><li v-for="destination in job.deliveries" :key="destination.destination">{{ destination.destination }} · {{ destination.status === 'resolved_external' ? 'Resolved externally' : destination.status }}<span v-if="destination.remoteId"> · receipt {{ destination.remoteId }}</span><p v-if="destination.message">{{ destination.message }}</p>
   <div v-if="destination.destination === 'wavelog' && ['pending','error','uncertain','held'].includes(destination.status)" class="external-resolution"><label>Location for exact verification<select class="form-select" v-model.number="selectedLocations[job.id]"><option :value="undefined" disabled>Select a location</option><option v-for="station in locations" :key="station.id" :value="station.id">{{ station.callsign }} · {{ station.name }} · ID {{ station.id }}</option></select></label><button class="btn console-button" :disabled="!!resolving || !selectedLocations[job.id]" @click="resolveExternal(job.id)">{{ resolving === job.id ? 'Verifying…' : 'Resolve as already logged' }}</button><small>Read-only: verify this exact QSO. Never submits or retries a Wavelog write. ADIF delivery is preserved.</small></div>
  </li></ul><p role="status">{{ resolutionMessages[job.id] }}</p></div>
 </section>
</template>
