<script setup lang="ts">
import { computed } from 'vue'
import type { EnrichmentState } from '../types'
const props = defineProps<{ enrichment?: EnrichmentState; call: string }>()
const result = computed(() => props.enrichment?.result)
const fields = computed(() => result.value?.call === props.call ? result.value.fields ?? {} : {})
const data = computed(() => result.value?.call === props.call ? result.value : undefined)
const operator = computed(() => [fields.value.fname, fields.value.name].filter(Boolean).join(' '))
const location = computed(() => [fields.value.addr2, fields.value.state, fields.value.country].filter(Boolean).join(', '))
const license = computed(() => [fields.value.license_class ? `Class ${fields.value.license_class}` : '', fields.value.expdate ? `Expires ${fields.value.expdate}` : ''].filter(Boolean).join(' · '))
function value(raw: unknown) { return typeof raw === 'object' && raw !== null ? JSON.stringify(raw) : String(raw ?? '—') }
function utc(raw?: number) { return raw ? new Date(raw).toISOString().replace('T', ' ').slice(0,19) + ' UTC' : '' }
const image = computed(() => {
 try { const url = new URL(String(fields.value.image ?? '')); return url.protocol === 'https:' && !url.username && !url.password ? url.href : '' } catch { return '' }
})
</script>
<template>
 <section class="enrichment-card" aria-labelledby="radio-enrichment-title" aria-live="polite">
  <div class="enrichment-heading"><div><span class="section-eyebrow">PYHAMTOOLS &amp; CALLBOOK</span><h3 id="radio-enrichment-title">Station enrichment</h3></div><span class="enrichment-state">{{ data?.status ?? (enrichment?.config.enabled ? 'Waiting for selection' : 'Disabled') }}</span></div>
  <p v-if="!enrichment?.config.enabled" class="muted-state">Enable enrichment and configure providers in Settings.</p>
  <p v-else-if="data?.status === 'pending'" role="status">Looking up {{ call }}… Radio reception continues.</p>
  <template v-else-if="data && data.status !== 'disabled' && data.status !== 'idle'">
   <p v-if="data.message" class="error-text">{{ data.message }}</p>
   <div class="enrichment-profile" v-if="operator || image"><img v-if="image" :src="image" :alt="`QRZ profile for ${call}`" referrerpolicy="no-referrer" @error="($event.target as HTMLImageElement).hidden = true"><div><h3 v-if="operator">{{ operator }}</h3><p v-if="location">{{ location }}</p><p v-if="license">{{ license }}</p><a v-if="data.providers?.qrz" :href="`https://www.qrz.com/db/${encodeURIComponent(call)}`" target="_blank" rel="noopener noreferrer">View QRZ profile</a></div></div>
   <dl class="enrichment-summary"><div v-if="fields.country"><dt>Country / entity</dt><dd>{{ fields.country }}</dd></div><div v-if="fields.adif"><dt>DXCC</dt><dd>{{ fields.adif }}</dd></div><div v-if="fields.continent"><dt>Continent</dt><dd>{{ fields.continent }}</dd></div><div v-if="fields.cqz || fields.ituz"><dt>CQ / ITU zone</dt><dd>{{ fields.cqz ?? '—' }} / {{ fields.ituz ?? '—' }}</dd></div><div v-if="data.locationGrid"><dt>Location grid</dt><dd>{{ data.locationGrid }}</dd></div><div v-if="data.computed?.distanceKm !== undefined"><dt>Short path</dt><dd>{{ data.computed.distanceKm.toLocaleString() }} km · {{ data.computed.heading }}°</dd></div></dl>
   <p v-if="data.locationSource" class="enrichment-note">{{ data.locationSource }}<span v-if="data.stationGrid"> · From {{ data.stationGrid }} ({{ data.stationGridSource }})</span></p>
   <p v-else class="enrichment-note">No station grid available. Country coordinates are not treated as a reported operating location.</p>
   <p v-if="data.reportedGrid && data.callbookGrid && data.reportedGrid !== data.callbookGrid" class="enrichment-note">Reported grid {{ data.reportedGrid }} is used for this contact; callbook grid {{ data.callbookGrid }} is retained separately.</p>
   <div class="enrichment-providers"><p v-for="(provider, name) in data.providers" :key="name"><strong>{{ name }}</strong> · {{ provider.status }}<span v-if="provider.cached"> · cached</span><span v-if="provider.dataStatus === 'stale'"> · stale data</span><span v-if="provider.message"> · {{ provider.message }}</span><span v-if="provider.subscription"> · XML subscription: {{ provider.subscription }}</span><small v-if="provider.updatedAt">{{ utc(provider.updatedAt) }}</small></p></div>
   <details class="enrichment-details" v-if="Object.keys(fields).length"><summary>All returned fields · {{ Object.keys(fields).length }}</summary><div class="enrichment-table"><table class="table"><thead><tr><th>Field</th><th>Value</th><th>Source</th></tr></thead><tbody><tr v-for="(field, name) in fields" :key="name"><td>{{ name }}</td><td>{{ value(field) }}</td><td>{{ data.fieldSources?.[name] }}</td></tr></tbody></table></div></details>
   <details class="enrichment-details" v-if="data.computed && Object.keys(data.computed).length"><summary>Radio calculations</summary><dl><template v-for="(field, name) in data.computed" :key="name"><dt>{{ name }}</dt><dd>{{ value(field) }}</dd></template></dl></details>
  </template>
 </section>
</template>
