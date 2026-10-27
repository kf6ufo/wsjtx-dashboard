<script setup lang="ts">
import { computed } from 'vue'
import type { Lookup, Qso } from '../types'
import { normalizeBand } from '../qso'

const props = defineProps<{
 history: Lookup<Qso[]>; band?: string | null; source: string; disabled?: boolean
 callStatus: { kind: string }; bandStatus: { kind: string }
}>()
defineEmits<{ retry: []; settings: [] }>()
const records = computed(() => props.history.status === 'loaded' ? props.history.data : [])
const complete = computed(() => props.history.status === 'empty' || props.history.status === 'loaded' && props.history.complete === true)
const bandName = computed(() => props.band?.trim() ? normalizeBand(props.band) : '')
const bandRecords = computed(() => bandName.value ? records.value.filter(q => normalizeBand(q.band) === bandName.value) : [])
const observed = computed(() => records.value.filter(q => q.observed).length)
const callTitle = computed(() => (({ new: 'NEW CALLSIGN', worked: 'WORKED BEFORE', checking: 'CHECKING', unknown: 'UNKNOWN' } as Record<string, string>)[props.callStatus.kind] ?? 'UNKNOWN'))
const bandTitle = computed(() => {
 if (!bandName.value) return 'UNKNOWN'
 const prefix = ({ new: 'NEW ON', worked: 'WORKED ON', checking: 'CHECKING' } as Record<string, string>)[props.bandStatus.kind] ?? 'UNKNOWN ON'
 return `${prefix} ${bandName.value}`
})
const completeness = computed(() => props.disabled ? 'History disabled' : props.history.status === 'pending' ? 'Checking history' : complete.value ? 'Complete history' : props.history.status === 'loaded' ? 'History incomplete' : 'History unavailable')
const callCount = computed(() => records.value.length || complete.value ? records.value.length : null)
const bandCount = computed(() => !bandName.value ? null : bandRecords.value.length || complete.value ? bandRecords.value.length : null)
</script>
<template>
 <div class="worked-summary worked-status-summary" aria-live="polite" aria-atomic="true">
  <div class="worked-status-grid">
   <div class="worked-status-indicator" :data-state="callStatus.kind" data-testid="callsign-status" aria-label="Callsign worked status">
    <span class="worked-status-caption">Callsign</span><strong>{{ callTitle }}</strong>
    <span class="worked-status-count">{{ callCount ?? '—' }} <small>{{ callCount === 1 ? 'QSO' : 'QSOs' }}</small></span>
   </div>
   <div class="worked-status-indicator" :data-state="bandStatus.kind" data-testid="band-status" aria-label="Current band worked status">
    <span class="worked-status-caption">Current band</span><strong>{{ bandTitle }}</strong>
    <span class="worked-status-count">{{ bandCount ?? '—' }} <small>{{ bandCount === 1 ? 'QSO' : 'QSOs' }}</small></span>
   </div>
  </div>
  <p class="worked-status-context"><span>{{ source }} · {{ completeness }}</span><span v-if="observed" class="worked-status-observations"> · {{ records.length - observed }} historical · {{ observed }} observed locally · awaiting reconciliation</span><button v-if="disabled" class="text-button" @click="$emit('settings')">Open history settings</button><button v-else-if="history.status === 'error'" class="text-button" @click="$emit('retry')">Retry lookup</button></p>
 </div>
</template>
<style scoped>
.worked-status-summary.worked-summary{display:block;margin:0 28px;padding:0;min-height:0;border:0;background:transparent}
:global(.station-main-radio .lookup-status .worked-status-summary.worked-summary){margin:0}
.worked-status-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.worked-status-indicator{display:flex;flex-direction:column;gap:3px;min-width:0;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:#20302f;color:#a6d9c7}
.worked-status-caption{font-size:9px;line-height:1.2;color:var(--muted)}
.worked-status-indicator strong{font-size:clamp(11px,1.1vw,14px);line-height:1.25;font-weight:750;letter-spacing:.02em;color:inherit;overflow-wrap:anywhere}
.worked-status-count{margin-top:auto;font-size:19px;line-height:1.15;font-weight:650;color:inherit;font-variant-numeric:tabular-nums}.worked-status-count small{font-size:11px;font-weight:500}
.worked-status-indicator[data-state="new"]{background:#332e23;border-color:#847047;color:#e0c78f}
.worked-status-indicator[data-state="unknown"],.worked-status-indicator[data-state="unavailable"],.worked-status-indicator[data-state="checking"]{background:#202c36;color:#b6c5cf}
.worked-status-summary .worked-status-context{font-size:10px;line-height:1.4;color:var(--muted);margin:6px 0 0;overflow-wrap:anywhere}.worked-status-context .text-button{font-size:inherit;margin-left:8px}
:global(.theme-light .worked-status-indicator){background:#edf5f1;color:#285e4d}:global(.theme-light .worked-status-indicator[data-state="new"]){background:#fcf4e2;border-color:#cdb67e;color:#775b20}
:global(.theme-light .worked-status-indicator[data-state="unknown"]),:global(.theme-light .worked-status-indicator[data-state="unavailable"]),:global(.theme-light .worked-status-indicator[data-state="checking"]){background:#f0f4f6;color:#506675}
@media(max-width:400px){.worked-status-grid{gap:6px}.worked-status-indicator{padding:7px 8px}.worked-status-count{font-size:17px}}
@media(max-width:700px){.worked-status-summary.worked-summary{margin-left:16px;margin-right:16px}}
</style>
