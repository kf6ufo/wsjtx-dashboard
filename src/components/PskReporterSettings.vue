<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { Dashboard } from '../focus'
const props = defineProps<{ dashboard: Dashboard }>()
const draft = reactive({ enabled: false, callsign: '', window_minutes: 15 })
const busy = ref(false), message = ref('')
watch(() => JSON.stringify(props.dashboard.state.pskreporter?.config), value => { if (value) Object.assign(draft, JSON.parse(value)) }, { immediate: true })
async function save() {
 busy.value = true; message.value = ''
 try {
  const response = await fetch('/api/pskreporter', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...draft, callsign: draft.callsign.trim().toUpperCase() }) })
  if (!response.ok) throw new Error()
  props.dashboard.applySnapshot(await response.json(), false); message.value = 'PSKReporter settings saved.'
 } catch { message.value = 'PSKReporter settings could not be saved. Check the callsign, server connection and configuration permissions.' }
 finally { busy.value = false }
}
</script>
<template>
 <form class="settings-form" aria-label="PSKReporter settings" @submit.prevent="save">
  <h3>PSKReporter · stations hearing me</h3>
  <label class="check-setting"><input v-model="draft.enabled" type="checkbox"> Show recent reception reports on the Station map</label>
  <label>Transmitting callsign override<input v-model="draft.callsign" class="form-control" maxlength="15" placeholder="Automatic from WSJT-X"></label>
  <p>Leave blank to use the selected radio’s station callsign. Set an override if WSJT-X does not report it. Reception is filtered to that callsign and the focus band, across all modes.</p>
  <label>Default reception window<select v-model.number="draft.window_minutes" class="form-select"><option v-for="n in [5,15,30,60]" :key="n" :value="n">Last {{ n }} minutes</option></select></label>
  <p>One shared, receive-only MQTT connection collects reports while Dashboard runs. Amber dots are smaller than the focus marker; an inner dot means the focused callsign reported hearing you. Reports expire after one hour and are cleared on restart. No XML polling or QSO submission.</p>
  <p>Reports may arrive late. No dot means no recent report in this feed, rather than proof that a station cannot hear you.</p>
  <p v-if="dashboard.state.pskreporter" role="status">Feed: {{ dashboard.state.pskreporter.status }}<span v-if="dashboard.state.pskreporter.callsigns.length"> · {{ dashboard.state.pskreporter.callsigns.join(', ') }}</span><span v-if="dashboard.state.pskreporter.error"> · {{ dashboard.state.pskreporter.error }}</span></p>
  <button class="btn btn-success" :disabled="busy || !dashboard.state.pskreporter || dashboard.state.connection !== 'connected'">Save PSKReporter settings</button>
  <p role="status">{{ message }}</p>
 </form>
</template>
