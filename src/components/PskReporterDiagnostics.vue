<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import type { Dashboard } from '../focus'
import type { PskReporterDiagnostics } from '../types'
const props = defineProps<{ dashboard: Dashboard; active: boolean }>()
const data = ref<PskReporterDiagnostics>(), error = ref(''), paused = ref(false), filter = ref('all'), clearing = ref(false)
const calls = ref(''), bandMode = ref('')
let stopped = false, requesting = false, generation = 0
type Report = PskReporterDiagnostics['reports'][number]
const reportBandMode = (row: Report) => `${row.band || (typeof row.preview.f === 'number' ? `${(row.preview.f / 1e6).toFixed(6)} MHz` : 'Unknown')} / ${row.preview.md || '—'}`
const matches = (value: string, query: string) => query.toUpperCase().trim().split(/\s+/).every(term => value.toUpperCase().includes(term))
const rows = computed(() => data.value?.reports.filter(row =>
 (filter.value === 'all' || row.outcome === filter.value) &&
 matches(`${row.preview.sc || '—'} → ${row.preview.rc || '—'}`, calls.value) && matches(reportBandMode(row), bandMode.value)) ?? [])
const filtered = computed(() => !!(calls.value.trim() || bandMode.value.trim() || filter.value !== 'all'))
function resetFilters() { calls.value = ''; bandMode.value = ''; filter.value = 'all' }
const reasons: Record<string,string> = { malformed_json:'Invalid JSON', invalid_payload:'Invalid payload', invalid_callsign:'Invalid callsign', wrong_sender:'Different transmitting callsign', invalid_grid:'Missing or invalid receiver grid', unsupported_frequency:'Unknown band / invalid frequency', invalid_timestamp:'Missing or invalid report time', too_old:'Report older than one hour', future_timestamp:'Report time is in the future', oversized:'Payload exceeds 4096 bytes', duplicate_or_older:'Duplicate or older report' }
const reason = (key:string) => reasons[key] || key
const utc = (at: number | null | undefined) => at ? `${new Date(at).toISOString().slice(0,10)} ${new Date(at).toISOString().slice(11,19)}` : 'None yet'
async function refresh() {
 if (!props.active || paused.value || requesting || stopped) return
 requesting = true; const token = generation
 try {
  const response = await fetch('/api/pskreporter/diagnostics', { cache:'no-store' })
  if (!response.ok) throw new Error(response.status === 404 ? 'MQTT diagnostics are unavailable on this server. Update the Dashboard server to this version.' : 'MQTT diagnostics could not be loaded. Check the Dashboard connection.')
  const value = await response.json() as PskReporterDiagnostics
  if (!stopped && !paused.value && token === generation) { data.value = value; error.value = '' }
 } catch (failure) { if (!stopped && token === generation) error.value = failure instanceof Error ? failure.message : 'MQTT diagnostics unavailable.' }
 finally { requesting = false }
}
function togglePause() { paused.value = !paused.value; ++generation; if (!paused.value) void refresh() }
async function clear() {
 clearing.value = true; ++generation
 try {
  const response = await fetch('/api/pskreporter/diagnostics', { method:'DELETE' })
  if (!response.ok) throw new Error()
  data.value = await response.json(); error.value = ''
 } catch { error.value = 'MQTT diagnostic rows could not be cleared. Check the Dashboard connection.' }
 finally { clearing.value = false }
}
watch(() => props.active, active => { ++generation; if (active) void refresh() })
void refresh()
const timer = window.setInterval(refresh,1000)
onUnmounted(() => { stopped = true; ++generation; window.clearInterval(timer) })
</script>
<template>
 <section class="psk-diagnostics" aria-label="PSKReporter MQTT diagnostics">
  <div class="diagnostics-heading"><div><span class="section-eyebrow">MQTT / RECEIVE ONLY</span><h3>PSKReporter interface</h3></div><span v-if="data" class="psk-feed-badge" :data-status="data.status">{{ data.status }}</span></div>
  <p>Browser stream: {{ dashboard.state.connection }}. Diagnostic polling reads this Dashboard’s local collector; it does not query PSKReporter.</p>
  <p v-if="error" class="connection-note" role="alert">{{ error }}<span v-if="data"> Last successful diagnostic response: {{ utc(data.generatedAt) }} UTC.</span></p>
  <p v-if="!data && !error" role="status">Loading MQTT diagnostics…</p>
  <template v-if="data">
   <p class="psk-diagnosis" :data-status="data.status" role="status">{{ data.explanation }}</p>
   <div class="psk-context"><div><span>Broker</span><strong>{{ data.broker }}:{{ data.port }}</strong><small>{{ data.tls ? 'TLS certificate verification enabled' : 'Unencrypted' }} · {{ data.workerRunning ? 'Collector running' : 'Collector stopped' }}</small></div><div><span>Map filters</span><strong>{{ data.focus.sender || 'Transmitting callsign unknown' }} → {{ data.focus.call || 'No focus' }}</strong><small>{{ data.focus.band || 'Band unknown' }} · saved window {{ data.focus.windowMinutes }} min<span v-if="data.focus.focusHeard"> · Focus station heard you</span></small></div></div>
   <div class="packet-stats psk-stats"><article><span>MQTT MESSAGES</span><strong>{{ data.counts.received }}</strong></article><article><span>ACCEPTED REPORTS</span><strong>{{ data.counts.accepted }}</strong></article><article><span>REJECTED REPORTS</span><strong>{{ data.counts.rejected + data.counts.oversized }}</strong></article><article><span>DUPLICATE / OLDER</span><strong>{{ data.counts.duplicates }}</strong></article><article><span>CACHED · ALL BANDS</span><strong>{{ data.counts.cached }}</strong></article><article><span>MATCH SAVED MAP WINDOW</span><strong>{{ data.counts.matchingWindow }}</strong></article></div>
   <div class="psk-timestamps"><p>Collector started: <strong>{{ utc(data.startedAt) }} UTC</strong></p><p>Connected: <strong>{{ utc(data.connectedAt) }}<span v-if="data.connectedAt"> UTC</span></strong></p><p>Last MQTT message: <strong>{{ utc(data.counts.lastMessageAt) }}<span v-if="data.counts.lastMessageAt"> UTC</span></strong></p><p>Last accepted report: <strong>{{ utc(data.lastAcceptedAt) }}<span v-if="data.lastAcceptedAt"> UTC</span></strong></p></div>
   <h3>Subscriptions <small>Broker acknowledgement confirms the subscription</small></h3>
   <div class="instances-scroll"><table class="table qso-table psk-subscriptions"><thead><tr><th>Transmitting callsign</th><th>Subscription</th><th>State</th></tr></thead><tbody><tr v-for="item in data.subscriptions" :key="item.callsign"><td>{{ item.callsign }}</td><td><code>{{ item.topic }}</code></td><td>{{ item.status }}</td></tr><tr v-if="!data.subscriptions.length"><td colspan="3">{{ data.config.enabled ? 'Waiting for a transmitting callsign.' : 'No subscriptions: PSKReporter is disabled.' }}</td></tr></tbody></table></div>
   <p class="diagnostic-note">{{ data.counts.connections }} successful connections · {{ data.counts.disconnects }} disconnects · {{ data.counts.connectionFailures }} connection failures · {{ data.counts.subscriptionRequests }} subscription requests · {{ data.counts.subscriptionAcks }} acknowledgements · {{ data.counts.subscriptionErrors }} subscription errors.</p>
   <h3>Cached receivers by band <small>Last hour · all monitored callsigns</small></h3>
   <div class="psk-band-list"><span v-for="band in data.bands" :key="`${band.sender}:${band.band}`" class="band-tag">{{ band.sender }} · {{ band.band }} · {{ band.count }}</span><p v-if="!data.bands.length">No usable reception reports cached.</p></div>
   <p class="diagnostic-note">{{ data.counts.focusBand }} receivers cached on the focus band for the transmitting callsign. The Station map’s local time-window selection can differ from the saved default shown here. No historical backfill; reports may arrive late.</p>
   <div class="diagnostic-toolbar psk-report-filters" role="group" aria-label="MQTT report filters">
    <label>Sender → receiver<input v-model="calls" type="search" class="form-control" placeholder="Either callsign" aria-describedby="psk-filter-help" maxlength="100" /></label>
    <label>Band / mode<input v-model="bandMode" type="search" class="form-control" placeholder="20m FT8" aria-describedby="psk-filter-help" maxlength="100" /></label>
    <label>Result<select v-model="filter" class="form-select"><option value="all">All recent messages</option><option value="accepted">Accepted reports</option><option value="rejected">Rejected reports</option><option value="duplicate">Duplicate / older reports</option></select></label>
    <button class="btn console-button" :disabled="!filtered" @click="resetFilters">Reset filters</button>
    <button class="btn console-button" :aria-pressed="paused" @click="togglePause">{{ paused ? 'Resume MQTT display' : 'Pause MQTT display' }}</button><button class="btn console-button" :disabled="clearing" @click="clear">Clear MQTT diagnostic rows</button>
   </div>
   <p id="psk-filter-help" class="diagnostic-note">Search partial callsigns, bands or modes, ignoring case. Space-separated terms and all three filters apply together to retained report rows only.</p>
   <p class="diagnostic-note psk-filter-count" aria-live="polite">Showing {{ rows.length }} of {{ data.reports.length }} retained messages.</p>
   <p class="diagnostic-note">{{ paused ? 'Display paused; collection continues.' : 'Newest first; refreshes every second while this tab is open.' }} Counters cover this server session. Clear removes recent rows only; counters, reception cache, focus and contact data are preserved.</p>
   <div v-if="Object.keys(data.rejectionReasons).length" class="psk-rejection-reasons"><span v-for="(count,key) in data.rejectionReasons" :key="key">{{ reason(key) }}: <strong>{{ count }}</strong></span></div>
   <div class="packet-scroll" tabindex="0" aria-label="MQTT reception reports"><table class="table qso-table psk-report-table"><thead><tr><th>Arrived · UTC</th><th>Sender → receiver</th><th>Band / mode</th><th>Grid / SNR</th><th>Result</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id"><td>{{ utc(row.at) }}<small>{{ row.size }} bytes</small></td><td>{{ row.preview.sc || '—' }} → {{ row.preview.rc || '—' }}<small class="psk-topic" :title="row.topic">{{ row.topic }}</small></td><td>{{ reportBandMode(row) }}</td><td>{{ row.preview.rl || '—' }}<small>{{ row.preview.rp !== undefined ? `${row.preview.rp} dB` : 'SNR unavailable' }}</small></td><td :class="{ 'error-text': row.outcome === 'rejected' }">{{ row.outcome }}<small v-if="row.reason">{{ reason(row.reason) }}</small></td></tr><tr v-if="!rows.length"><td colspan="5">No retained messages match these filters. Use the connection/subscription status above to check collection.</td></tr></tbody></table></div>
   <h3>Connection activity</h3><div class="packet-scroll psk-event-scroll" tabindex="0" aria-label="MQTT connection activity"><table class="table qso-table"><thead><tr><th>Time · UTC</th><th>Event</th><th>Details</th></tr></thead><tbody><tr v-for="event in data.events" :key="event.id"><td>{{ utc(event.at) }}</td><td>{{ event.kind }}</td><td>{{ event.message }}</td></tr><tr v-if="!data.events.length"><td colspan="3">No retained connection events.</td></tr></tbody></table></div>
   <p class="diagnostic-note">Queue {{ data.counts.queued }}/{{ data.limits.queue }} · {{ data.counts.queueDropped }} reports dropped by queue capacity · {{ data.counts.controlDropped }} connection events dropped · {{ data.counts.oversized }} oversized payloads · {{ data.counts.evicted }} cache evictions · {{ data.counts.expired }} expired/removed entries · {{ data.counts.bytes }} received bytes. Retains {{ data.limits.reports }} message summaries and {{ data.limits.events }} connection events in memory; no raw MQTT payloads are saved.</p>
  </template>
 </section>
</template>
<style scoped>
.psk-report-filters input::placeholder { color: var(--muted); opacity: 1 }
</style>
