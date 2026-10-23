<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import type { Dashboard } from '../focus'
import type { DiagnosticDetail, DiagnosticPage } from '../types'
const props = defineProps<{ dashboard: Dashboard }>()
const state = props.dashboard.state
const data = ref<DiagnosticPage>({ generation: 0, latest: 0, limit: 200, rows: [] })
const paused = ref(false), filter = ref('all'), instance = ref(''), offset = ref(0), error = ref(''), detail = ref<DiagnosticDetail | null>(null)
let stopped = false, requesting = false, requestGeneration = 0
const rows = computed(() => data.value.rows.filter(row => (filter.value === 'all' || (filter.value === 'errors' ? row.error : filter.value === 'unknown' ? row.name === 'Unknown' : row.kind === Number(filter.value))) && (!instance.value || row.instance?.toLowerCase().includes(instance.value.toLowerCase()))))
const page = computed(() => rows.value.slice(offset.value, offset.value + 100))
watch([filter, instance], () => { offset.value = 0 })
async function refresh() {
 if (paused.value || requesting || stopped) return
 requesting = true
 const generation = requestGeneration
 try {
  const response = await fetch('/api/diagnostics', { cache: 'no-store' })
  if (!response.ok) throw new Error('Diagnostics unavailable. Check the server connection.')
  const value = await response.json() as DiagnosticPage
  if (!stopped && !paused.value && generation === requestGeneration) { data.value = value; error.value = ''; if (offset.value >= rows.value.length) offset.value = 0 }
 } catch (failure) { if (!stopped) error.value = failure instanceof Error ? failure.message : 'Diagnostics unavailable' }
 finally { requesting = false }
}
async function clear() {
 ++requestGeneration
 try {
  const response = await fetch('/api/diagnostics', { method: 'DELETE' })
  if (!response.ok) throw new Error('Clear failed; check connection.')
  data.value = await response.json(); detail.value = null; offset.value = 0; error.value = ''
 } catch (failure) { error.value = failure instanceof Error ? failure.message : 'Clear failed' }
}
async function inspect(id: number) {
 try {
  const response = await fetch(`/api/diagnostics/${id}`, { cache: 'no-store' })
  if (!response.ok) throw new Error('Packet has expired from retention. Select a newer packet.')
  detail.value = await response.json(); error.value = ''
 } catch (failure) { detail.value = null; error.value = failure instanceof Error ? failure.message : 'Packet unavailable' }
}
function togglePause() { paused.value = !paused.value; ++requestGeneration; if (!paused.value) void refresh() }
const utc = (at: number) => new Date(at).toISOString().slice(11, 23)
void refresh()
const timer = window.setInterval(refresh, 1000)
onUnmounted(() => { stopped = true; ++requestGeneration; window.clearInterval(timer) })
</script>
<template>
 <section class="utility-panel" aria-label="Diagnostics"><div class="diagnostics-heading"><div><span class="section-eyebrow">PRIMARY UDP / RECEIVE ONLY</span><h2>Diagnostics</h2></div><span class="receiver-badge" :data-status="state.receiver.status">{{ state.receiver.status }}</span></div><p>Receiver {{ state.receiver.listen || '0.0.0.0' }}:{{ state.receiver.port || 2238 }} · {{ state.receiver.group || 'Unicast' }} · interface {{ state.receiver.interface || 'not set' }}. Browser stream: {{ state.connection }}.</p><p v-if="state.receiver.error" class="connection-note" role="alert">{{ state.receiver.error }}</p>
 <div class="packet-stats"><article><span>DATAGRAMS</span><strong>{{ state.counters.packets ?? 0 }}</strong></article><article><span>DECODES</span><strong>{{ state.counters.decodes }}</strong></article><article><span>PARSE FAILURES</span><strong>{{ state.counters.malformed }}</strong></article><article><span>IGNORED / PASSIVE</span><strong>{{ state.counters.ignored ?? 0 }}</strong></article><article><span>RECEIVER ERRORS</span><strong>{{ state.counters.receiverErrors ?? 0 }}</strong></article><article><span>INSTANCE CAPACITY</span><strong>{{ state.counters.capacity ?? 0 }}</strong></article><article><span>LAST PACKET · UTC</span><strong class="last-packet">{{ state.receiver.lastPacketAt ? utc(state.receiver.lastPacketAt) : 'None yet' }}</strong></article></div>
 <h3>WSJT-X instances <small>{{ state.sample ? 'No live instances · sample workspace' : 'identified by network ID' }}</small></h3><div class="instances-scroll"><table class="table qso-table instance-table"><thead><tr><th>Network ID / source</th><th>State</th><th>Last seen · UTC</th><th>DX Call</th><th>Band / mode</th></tr></thead><tbody><tr v-for="rig in (state.sample ? [] : state.liveRigs)" :key="rig.id"><td><strong>{{ rig.id }}</strong><small>{{ rig.source || 'Source unavailable' }}</small></td><td>{{ rig.online ? 'Seen recently' : 'Closed / inactive' }}</td><td>{{ rig.lastSeen ? utc(rig.lastSeen) : '—' }}</td><td>{{ rig.call || '—' }}</td><td>{{ rig.band || '—' }} / {{ rig.mode || '—' }}</td></tr><tr v-if="state.sample || !state.liveRigs.length"><td colspan="5">No received instances yet. Enable/configure the receiver in Settings.</td></tr></tbody></table></div>
 <div class="diagnostic-toolbar"><label>Packet filter<select class="form-select" v-model="filter"><option value="all">All packets</option><option value="1">Status</option><option value="2">Decode</option><option value="0">Heartbeat</option><option value="6">Close</option><option value="errors">Parse failures</option><option value="unknown">Unknown types</option></select></label><label>Instance filter<input class="form-control" v-model="instance" placeholder="Network ID contains…"></label><button class="btn console-button" @click="togglePause" :aria-pressed="paused">{{ paused ? 'Resume display' : 'Pause display' }}</button><button class="btn console-button" @click="clear">Clear diagnostics</button></div>
 <p class="diagnostic-note">{{ paused ? 'Display paused · reception and counters continue.' : 'Newest first · refreshes every second.' }} {{ data.rows.length }} / {{ data.limit }} retained in server memory. Clear affects diagnostics only; selection history and counters continue.</p><p v-if="error" class="connection-note" role="alert">{{ error }}</p>
 <div class="packet-scroll" tabindex="0" aria-label="Packet diagnostics"><table class="table qso-table packet-table"><thead><tr><th>Received · UTC</th><th>Source</th><th>Instance</th><th>Packet</th><th>Result</th><th>Details</th></tr></thead><tbody><tr v-for="row in page" :key="row.id" :class="{ 'packet-error': row.error }"><td>{{ utc(row.at) }}</td><td>{{ row.source }}</td><td>{{ row.instance || '—' }}</td><td>{{ row.name }}<small>{{ row.kind === null ? 'Invalid header/payload' : `Type ${row.kind} · schema ${row.schema}` }}</small></td><td>{{ row.error || `${row.size} bytes` }}</td><td><button class="text-button" @click="inspect(row.id)" :aria-label="`Inspect packet ${row.id}`">Expand ↗</button></td></tr><tr v-if="!page.length"><td colspan="6">No matching packets. {{ state.receiver.status === 'listening' ? 'Listening does not confirm traffic has arrived.' : 'Configure and enable the receiver in Settings.' }}</td></tr></tbody></table></div>
 <div class="packet-pagination"><button class="btn console-button" :disabled="offset === 0" @click="offset -= 100">Newer</button><span>Showing {{ rows.length ? offset + 1 : 0 }}–{{ Math.min(offset + 100, rows.length) }} of {{ rows.length }} matching packets</span><button class="btn console-button" :disabled="offset + 100 >= rows.length" @click="offset += 100">Older</button></div>
 <section v-if="detail" class="packet-detail" aria-label="Packet details"><div class="diagnostics-heading"><h3>{{ detail.name }} · #{{ detail.id }}</h3><button class="btn console-button" @click="detail = null">Close packet details</button></div><p>{{ detail.source }} → {{ detail.instance || 'unparsed instance' }} · {{ utc(detail.at) }} UTC · {{ detail.size }} bytes</p><p v-if="detail.error" class="error-text">{{ detail.error }}</p><pre>{{ JSON.stringify(detail.fields, null, 2) }}</pre><p v-if="!Object.keys(detail.fields).length">Payload is not interpreted for this packet type. Original bytes are retained below; no QSO is submitted.</p><details><summary>Original datagram · Base64</summary><pre>{{ detail.rawBase64 }}</pre></details></section>
 <p class="diagnostic-note">Instances inactive for 90 seconds establish a new baseline on their next Status. Close and receiver restarts also reset baselines. QRZ/Wavelog: not connected. Logging/forwarding: not implemented.</p>
 </section>
</template>
