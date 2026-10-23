<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Dashboard } from '../focus'
import type { EnrichmentConfig, EnrichmentResult, Snapshot } from '../types'
const props = defineProps<{ dashboard: Dashboard }>()
const defaults: EnrichmentConfig = { enabled: false, source: 'countryfile', filename: '', station_grid: '', refresh_hours: 24, cache_minutes: 1440, cache_limit: 200, qrz_enabled: false, qrz_version: 'current', field_priority: 'qrz_first', allow_country_estimate: false }
const configuration = computed(() => props.dashboard.state.enrichment?.config ?? defaults)
const draft = ref({ ...configuration.value })
const dirty = ref(false)
watch(() => JSON.stringify(configuration.value), () => { if (!dirty.value) draft.value = { ...configuration.value } })
const secrets = ref({ clublog_key: '', qrz_username: '', qrz_password: '' })
const clear = ref({ clublog_key: false, qrz_username: false, qrz_password: false })
const busy = ref(false), message = ref(''), testCall = ref('KF6UFO'), tested = ref<EnrichmentResult | null>(null)
async function action(path: string, method: string, payload?: unknown) {
 busy.value = true; message.value = ''
 try {
  const response = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, ...(payload === undefined ? {} : { body: JSON.stringify(payload) }) })
  const body = await response.json()
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Enrichment operation failed')
  if (path.endsWith('/test')) { tested.value = body as EnrichmentResult; message.value = 'Provider test finished. Results are below; radio selection and history are unchanged.' }
  else { props.dashboard.applySnapshot(body as Snapshot, false); message.value = 'Enrichment settings applied. UDP reception and selection history are unchanged.' }
  return true
 } catch (error) { message.value = error instanceof Error ? error.message : 'Server connection failed'; return false }
 finally { busy.value = false }
}
async function save() {
 const submittedDraft = JSON.stringify(draft.value), submittedSecrets = JSON.stringify(secrets.value), submittedClear = JSON.stringify(clear.value)
 const { clublog_key_configured: _key, qrz_username_configured: _user, qrz_password_configured: _pwd, ...config } = draft.value
 const payload = { ...config, ...secrets.value, clear_clublog_key: clear.value.clublog_key, clear_qrz_username: clear.value.qrz_username, clear_qrz_password: clear.value.qrz_password }
 if (await action('/api/enrichment', 'PUT', payload)) {
  if (JSON.stringify(draft.value) === submittedDraft) { dirty.value = false; draft.value = { ...configuration.value } }
  if (JSON.stringify(secrets.value) === submittedSecrets) secrets.value = { clublog_key: '', qrz_username: '', qrz_password: '' }
  if (JSON.stringify(clear.value) === submittedClear) clear.value = { clublog_key: false, qrz_username: false, qrz_password: false }
  tested.value = null
 }
}
const disabled = computed(() => busy.value || props.dashboard.state.connection !== 'connected')
</script>
<template>
 <section class="receiver-settings" aria-labelledby="enrichment-settings-title">
  <span class="section-eyebrow">RADIO DATA &amp; CALLBOOK</span><h3 id="enrichment-settings-title">pyhamtools enrichment</h3>
  <p>Country, DXCC, zones and all available callbook fields load in the background. Settings apply without restarting the radio receiver.</p>
  <form class="settings-form receiver-form" aria-label="Enrichment settings" @submit.prevent="save" @input="dirty = true" @change="dirty = true">
   <label class="check-setting"><input type="checkbox" v-model="draft.enabled"> Enable enrichment for radio selections</label>
   <label>Primary data source<select class="form-select" v-model="draft.source"><option value="countryfile">Country-files.com</option><option value="clublogxml">Club Log XML</option><option value="clublogapi">Club Log API</option><option value="qrz">QRZ XML</option></select></label>
   <label v-if="draft.source === 'countryfile' || draft.source === 'clublogxml'">Local provider file (optional)<input class="form-control" v-model.trim="draft.filename" placeholder="Blank downloads the official data"><small>Country files use cty.plist; Club Log uses its XML file. Relative paths start at the installation folder.</small></label>
   <label>Station grid override (optional)<input class="form-control" v-model.trim="draft.station_grid" placeholder="Use the selecting radio’s DE grid" maxlength="8"><small>A 4, 6 or 8 character Maidenhead grid. Each selection otherwise uses its radio’s reported grid.</small></label>
   <label>Provider refresh interval (hours)<input class="form-control" type="number" min="1" max="720" v-model.number="draft.refresh_hours" required></label>
   <label>Callsign cache lifetime (minutes)<input class="form-control" type="number" min="1" max="10080" v-model.number="draft.cache_minutes" required></label>
   <label>Maximum cached provider results<input class="form-control" type="number" min="20" max="1000" v-model.number="draft.cache_limit" required></label>
   <label class="check-setting"><input type="checkbox" v-model="draft.qrz_enabled"> Add QRZ XML callbook details</label>
   <label>Field preference<select class="form-select" v-model="draft.field_priority"><option value="qrz_first">QRZ first; fill gaps from primary source</option><option value="source_first">Primary source first; fill gaps from QRZ</option></select><small>The reported operating grid always takes priority for distance and bearing.</small></label>
   <label class="check-setting"><input type="checkbox" v-model="draft.allow_country_estimate"> Allow approximate provider coordinates when no grid is available</label>
   <label v-if="draft.source === 'clublogxml' || draft.source === 'clublogapi'">Club Log API key<input class="form-control" type="password" aria-label="Club Log API key" v-model="secrets.clublog_key" autocomplete="new-password" :placeholder="configuration.clublog_key_configured ? 'Saved on server; blank keeps it' : 'API key'"><small>{{ configuration.clublog_key_configured ? 'A key is saved on this server.' : 'No key saved.' }}</small></label><label class="check-setting"><input type="checkbox" v-model="clear.clublog_key"> Remove saved Club Log key</label>
   <template v-if="draft.qrz_enabled || draft.source === 'qrz'">
    <label>QRZ XML username<input class="form-control" aria-label="QRZ XML username" v-model.trim="secrets.qrz_username" autocomplete="off" :placeholder="configuration.qrz_username_configured ? 'Saved on server; blank keeps it' : 'Your QRZ username / callsign'"><small>{{ configuration.qrz_username_configured ? 'Username saved on server.' : 'No username saved.' }}</small></label><label class="check-setting"><input type="checkbox" v-model="clear.qrz_username"> Remove saved QRZ username</label>
    <label>QRZ XML password<input class="form-control" type="password" aria-label="QRZ XML password" v-model="secrets.qrz_password" autocomplete="new-password" :placeholder="configuration.qrz_password_configured ? 'Saved on server; blank keeps it' : 'Your QRZ account password'"><small>{{ configuration.qrz_password_configured ? 'Password saved on server.' : 'No password saved.' }}</small></label><label class="check-setting"><input type="checkbox" v-model="clear.qrz_password"> Remove saved QRZ password</label>
    <label>QRZ XML version<input class="form-control" v-model.trim="draft.qrz_version" placeholder="current"></label>
    <p>QRZ XML uses your QRZ username and password; an active XML data subscription unlocks the full fields. A QRZ Logbook API key is a different credential. Saved credentials are never returned to browsers.</p>
   </template>
   <div class="receiver-actions"><button class="btn btn-success" :disabled="disabled">{{ busy ? 'Working…' : 'Save enrichment settings' }}</button><button class="btn console-button" type="button" :disabled="disabled" @click="action('/api/enrichment/refresh', 'POST')">Refresh provider data</button></div>
  </form>
  <form class="settings-form" aria-label="Test enrichment providers" @submit.prevent="action('/api/enrichment/test', 'POST', { call: testCall })"><label>Test callsign<input class="form-control" v-model.trim="testCall" required maxlength="15"></label><button class="btn console-button" :disabled="disabled">Test saved provider settings</button></form>
  <p role="status">{{ message }}</p>
  <div v-if="tested" class="provider-test-results"><h4>Test results · {{ tested.call }}</h4><p v-for="(provider, name) in tested.providers" :key="name">{{ name }}: {{ provider.status }}<span v-if="provider.message"> · {{ provider.message }}</span><span v-if="provider.subscription"> · Subscription: {{ provider.subscription }}</span><span v-if="provider.fields.country"> · {{ provider.fields.country }}</span></p></div>
 </section>
</template>
