<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Dashboard } from '../focus'
import type { ForwardDestination } from '../types'
const props = defineProps<{ dashboard: Dashboard }>()
const rows = ref<(ForwardDestination & { rigText: string })[]>([]), busy = ref(false), message = ref('')
const types = [[0,'Heartbeat'],[1,'Status'],[2,'Decode'],[3,'Clear'],[5,'QSO Logged'],[6,'Close'],[10,'WSPR Decode'],[12,'Logged ADIF']] as const
watch(() => JSON.stringify(props.dashboard.state.forwarding?.config), value => {
 if (value) rows.value = JSON.parse(value).destinations.map((row: ForwardDestination) => ({ ...row, rigText: row.rigs.join('\n') }))
}, { immediate: true })
function add() { rows.value.push({ id: `udp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`, name: 'UDP destination', enabled: false, host: '127.0.0.1', port: 2239, format: 'raw', rigs: [], rigText: '', packets: [0,1,2,3,5,12] }) }
async function save() {
 busy.value = true; message.value = ''
 try {
  const destinations = rows.value.map(({ rigText, ...row }) => ({ ...row, rigs: rigText.split('\n').filter(r=>r.trim().length>0) }))
  const response = await fetch('/api/forwarding', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ destinations }) })
  if (!response.ok) throw new Error('Save failed. Check addresses, packet selection and receiving-port loops.')
  props.dashboard.applySnapshot(await response.json(), false); message.value = 'UDP forwarding settings saved.'
 } catch { message.value = 'Forwarding settings could not be saved. Check host/port, packet selection, and ensure the destination does not feed the Dashboard receiving socket.' }
 finally { busy.value = false }
}
const status = (id: string) => props.dashboard.state.forwarding?.destinations.find(d=>d.id===id)
</script>
<template>
 <form class="settings-form forwarding-form" aria-label="UDP forwarding settings" @submit.prevent="save">
  <h3>UDP forwarding</h3><p>Optional one-way distribution. Each destination operates independently of history and logging. Dispatched UDP packets are not delivery acknowledgements.</p>
  <fieldset v-for="(row,index) in rows" :key="row.id" class="forwarding-destination"><legend>{{ row.name || 'Destination' }}</legend>
   <label>Name<input class="form-control" v-model="row.name" maxlength="80" required></label>
   <label class="check-setting"><input type="checkbox" v-model="row.enabled"> Enable destination</label>
   <label>Host / IPv4 address<input class="form-control" v-model="row.host" required></label><label>UDP port<input class="form-control" type="number" min="1024" max="65535" v-model.number="row.port" required></label>
   <label>Output format<select class="form-select" v-model="row.format"><option value="raw">Original WSJT-X datagrams</option><option value="enriched-adif">WSJT-X with enriched Logged ADIF</option></select></label>
   <label>Rig filters (one exact network ID per line; blank means all)<textarea class="form-control" v-model="row.rigText" rows="2" placeholder="WSJT-X - IC7300"></textarea></label>
   <fieldset class="packet-selection"><legend>Packet types</legend><label v-for="[kind,label] in types" :key="kind" class="check-setting"><input type="checkbox" :value="kind" v-model="row.packets">{{ label }}</label></fieldset>
   <p v-if="row.format === 'enriched-adif'">Select Logged ADIF for completed contacts. Paired QSO Logged notifications are suppressed. Ordinary selected packets pass through unchanged; enriched contacts wait separately for lookup data.</p>
   <p v-if="status(row.id)" class="forwarding-status">{{ status(row.id)?.status }} · {{ status(row.id)?.dispatched }} dispatched · {{ status(row.id)?.filtered }} filtered · {{ status(row.id)?.dropped }} dropped<span v-if="status(row.id)?.lastSentAt"> · Last dispatch {{ new Date(status(row.id)!.lastSentAt!).toISOString().slice(11,19) }} UTC</span><span v-if="status(row.id)?.lastError" class="error-text"> · {{ status(row.id)?.lastError }}</span></p>
   <button type="button" class="btn console-button" @click="rows.splice(index,1)">Remove destination</button>
  </fieldset>
  <button type="button" class="btn console-button" @click="add" :disabled="rows.length>=16">Add UDP destination</button>
  <button class="btn btn-success" :disabled="busy || dashboard.state.connection !== 'connected'">{{ busy ? 'Saving…' : 'Save UDP forwarding settings' }}</button><p role="status">{{ message }}</p>
  <p v-if="dashboard.state.forwarding?.error" role="alert" class="error-text">{{ dashboard.state.forwarding.error }}</p>
  <p v-if="dashboard.state.forwarding?.loopDrops">Reflected packets blocked: {{ dashboard.state.forwarding.loopDrops }}</p>
 </form>
</template>
