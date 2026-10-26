<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Dashboard } from '../focus'
import type { Snapshot, WavelogConfig, WavelogConnection } from '../types'
const props = defineProps<{ dashboard: Dashboard }>()
const defaults: WavelogConfig = { enabled: false, url: '', scope_mode: 'all', station_ids: [], logbook_id: 0, cache_minutes: 5, cache_limit: 20, page_size: 100, max_pages: 100, max_records: 10000, timeout_seconds: 8 }
const configuration = computed(() => props.dashboard.state.wavelog?.config ?? defaults)
const connection = computed<WavelogConnection>(() => props.dashboard.state.wavelog?.connection ?? { status: 'idle', stations: [], logbooks: [], scopes: [] })
const copy = () => ({ ...configuration.value, station_ids: [...configuration.value.station_ids] })
const draft = ref(copy()), dirty = ref(false), token = ref(''), clearToken = ref(false), additionalIds = ref('')
watch(() => JSON.stringify(configuration.value), () => { if (!dirty.value) draft.value = copy() })
const busy = ref(false), message = ref('')
const disabled = computed(() => busy.value || props.dashboard.state.connection !== 'connected')
async function action(path: string, method: string, payload?: unknown) {
 busy.value = true; message.value = ''
 try {
  const response = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, ...(payload === undefined ? {} : { body: JSON.stringify(payload) }) })
  const body = await response.json()
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Wavelog operation failed')
  if (path.endsWith('/test')) message.value = body.status === 'ready' && !configuration.value.enabled
   ? 'Connection test passed. History is still disabled; turn on Enable Wavelog history and save to load contacts.'
   : body.message || 'Connection test finished.'
  else { props.dashboard.applySnapshot(body as Snapshot, false); message.value = `Wavelog settings saved. History lookups are ${configuration.value.enabled ? 'enabled' : 'disabled'}. Radio reception and selection history are unchanged.` }
  return true
 } catch (error) { message.value = error instanceof Error ? error.message : 'Dashboard connection failed'; return false }
 finally { busy.value = false }
}
async function save() {
 const submitted = JSON.stringify(draft.value), submittedToken = token.value, submittedClear = clearToken.value, submittedIds = additionalIds.value
 const { token_configured: _configured, ...config } = draft.value
 const ids = additionalIds.value.split(',').map(value => value.trim()).filter(Boolean)
 if (ids.some(value => !/^\d+$/.test(value))) { message.value = 'Additional station IDs must be numbers separated by commas.'; return }
 const station_ids = [...new Set([...config.station_ids, ...ids.map(Number)])]
 if (await action('/api/wavelog', 'PUT', { ...config, station_ids, token: token.value, clear_token: clearToken.value })) {
  if (JSON.stringify(draft.value) === submitted && additionalIds.value === submittedIds) { dirty.value = false; draft.value = copy(); additionalIds.value = '' }
  if (token.value === submittedToken) token.value = ''
  if (clearToken.value === submittedClear) clearToken.value = false
 }
}
</script>
<template>
 <section class="receiver-settings" aria-labelledby="wavelog-settings-title">
  <span class="section-eyebrow">YOUR SOURCE OF RECORD</span><h3 id="wavelog-settings-title">Wavelog QSO history</h3>
  <p>Read previous contacts for the focused station. These controls only read contacts. Optional completed-QSO delivery has its own QSO history & logging section.</p>
  <p role="status" data-testid="wavelog-history-enablement"><strong>History lookups are {{ configuration.enabled ? 'enabled' : 'disabled' }}.</strong><template v-if="!configuration.enabled"> A connection test only verifies access. Turn on Enable Wavelog history and save to load contacts.</template></p>
  <form class="settings-form receiver-form" aria-label="Wavelog settings" @submit.prevent="save" @input="dirty = true" @change="dirty = true">
   <label class="check-setting"><input type="checkbox" v-model="draft.enabled"> Enable Wavelog history</label>
   <label>Wavelog application URL<input class="form-control" type="url" v-model.trim="draft.url" placeholder="https://log.example.com/index.php"><small>The application address; an ending /api or /api/v2 is removed automatically. Keep /index.php if your installation needs it.</small></label>
   <label>API v2 token<input class="form-control" type="password" aria-label="Wavelog API v2 token" v-model.trim="token" autocomplete="new-password" :placeholder="configuration.token_configured ? 'Saved on server; blank keeps it' : 'wl2_…'"><small>{{ configuration.token_configured ? 'A token is saved on this server.' : 'No token saved.' }}</small></label>
   <label class="check-setting"><input type="checkbox" v-model="clearToken"> Remove saved Wavelog token</label>
   <p>Wavelog 3.1.0+ uses a separate API v2 token. Grant <strong>qso:read</strong> and <strong>station:read</strong>. Optional <strong>logbook:read</strong> enables logbook selection (Wavelog 3.2+); <strong>confirmation:read</strong> supplies QSL details. Legacy API keys are different. Saved tokens never return to browsers.</p>
   <label>History scope<select class="form-select" v-model="draft.scope_mode"><option value="all">All authorized station locations</option><option value="stations">Selected station locations</option><option value="logbook">Selected logbook</option></select><small>All locations includes previous station callsigns, such as KF0TKE, as well as KF6UFO. Inactive locations are included when authorized.</small></label>
   <label v-if="draft.scope_mode === 'logbook'">Wavelog logbook<select class="form-select" v-model.number="draft.logbook_id"><option :value="0">Test the saved connection, then select a logbook</option><option v-for="book in connection.logbooks" :key="book.id" :value="book.id">{{ book.name }} · {{ book.stationIds.length }} locations</option></select></label>
   <template v-if="draft.scope_mode === 'stations'">
    <fieldset class="wavelog-location-options"><legend>Included station locations</legend><label class="check-setting" v-for="station in connection.stations" :key="station.id"><input type="checkbox" v-model="draft.station_ids" :value="station.id">{{ station.callsign }} · {{ station.name }} · ID {{ station.id }}{{ station.active ? '' : ' · inactive' }}</label></fieldset>
    <label>Additional station IDs (optional)<input class="form-control" v-model="additionalIds" placeholder="1, 2"><small>Use known location IDs if Wavelog hides them from its active-logbook listing. Access is verified with Wavelog.</small></label>
   </template>
   <label>History cache lifetime (minutes)<input class="form-control" type="number" min="1" max="60" v-model.number="draft.cache_minutes" required></label>
   <label>Maximum cached callsigns<input class="form-control" type="number" min="1" max="100" v-model.number="draft.cache_limit" required></label>
   <label>Contacts per API page<input class="form-control" type="number" min="10" max="500" v-model.number="draft.page_size" required></label>
   <label>Maximum API pages per lookup<input class="form-control" type="number" min="1" max="1000" v-model.number="draft.max_pages" required></label>
   <label>Maximum contacts per lookup<input class="form-control" type="number" min="1" max="50000" v-model.number="draft.max_records" required></label>
   <label>Request timeout (seconds)<input class="form-control" type="number" min="2" max="30" v-model.number="draft.timeout_seconds" required></label>
   <p>All pages load before history is called complete. A failed page or safety limit is shown as incomplete. Contacts are cached in memory; no permanent QSO copy is created here.</p>
   <div class="receiver-actions"><button class="btn btn-success" :disabled="disabled">{{ busy ? 'Working…' : 'Save Wavelog settings' }}</button><button class="btn console-button" type="button" :disabled="disabled" @click="action('/api/wavelog/test', 'POST')">Test saved connection &amp; load locations</button></div>
  </form>
  <p role="status">{{ message }}</p>
  <div class="provider-test-results"><h4>Wavelog connection · {{ connection.status }}</h4><p v-if="connection.message">{{ connection.message }}</p><p v-if="connection.owner">Token owner: {{ connection.owner }}<span v-if="connection.expiresAt"> · Expires {{ connection.expiresAt }} UTC</span></p><p v-if="connection.scopes.length">Granted scopes: {{ connection.scopes.join(', ') }}</p><p v-for="notice in connection.notices" :key="notice">{{ notice }}</p><ul v-if="connection.stations.length"><li v-for="station in connection.stations" :key="station.id">{{ station.callsign }} · {{ station.name }} · ID {{ station.id }}</li></ul></div>
 </section>
</template>
