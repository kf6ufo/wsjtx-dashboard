<script setup lang="ts">
import { computed } from 'vue'
import type { EnrichmentState } from '../types'
import { fieldText, hasValue, stationGroups } from '../stationDetails'
const props = defineProps<{ enrichment?: EnrichmentState; call: string; connected?: boolean }>()
const emit = defineEmits<{ refresh: [] }>()
const data = computed(() => props.enrichment?.result.call === props.call ? props.enrichment.result : undefined)
const fields = computed(() => data.value?.fields ?? {})
const groups = computed(() => data.value ? stationGroups(data.value) : [])
const returned = computed(() => Object.entries(fields.value).filter(([, value]) => hasValue(value)))
const qrz = computed(() => data.value?.providers?.qrz?.status === 'loaded')
const biography = computed(() => qrz.value && Number(fields.value.bio) > 0)
function utc(raw?: number) { return raw ? new Date(raw).toISOString().replace('T', ' ').slice(0,19) + ' UTC' : '' }
</script>
<template>
 <section class="enrichment-card station-details" aria-labelledby="radio-enrichment-title">
  <div class="enrichment-heading"><div><span class="section-eyebrow">STATION PROFILE &amp; RADIO DATA</span><h3 id="radio-enrichment-title">Station details</h3></div><div class="station-details-actions"><span class="enrichment-state" role="status">{{ data?.status ?? (enrichment?.config.enabled ? 'Waiting for selection' : 'Disabled') }}</span><button v-if="enrichment?.config.enabled" class="text-button" :disabled="connected === false || data?.status === 'pending'" @click="emit('refresh')">Refresh details</button></div></div>
  <p v-if="!enrichment?.config.enabled" class="muted-state">Enable enrichment and configure providers in Settings.</p>
  <p v-else-if="data?.status === 'pending'" role="status">Looking up {{ call }}… Radio reception continues.</p>
  <template v-else-if="data && data.status !== 'disabled' && data.status !== 'idle'">
   <p v-if="data.message" class="error-text">{{ data.message }}</p>
   <p v-if="data.status === 'empty'" class="muted-state">No matching station details were returned by the configured providers.</p>
   <dl v-if="returned.length || data.locationGrid" class="enrichment-summary station-highlights">
    <div v-if="hasValue(fields.country)"><dt>Country / entity</dt><dd><span>{{ fields.country }}</span><small v-if="hasValue(fields.adif)">DXCC {{ fields.adif }}</small></dd></div>
    <div v-if="data.locationGrid"><dt>{{ data.reportedGrid ? 'Operating grid' : data.callbookGrid ? 'Callbook grid' : 'Estimated grid' }}</dt><dd>{{ data.locationGrid }}</dd></div>
    <div v-if="data.computed?.distanceKm !== undefined"><dt>Short path</dt><dd>{{ data.computed.distanceKm.toLocaleString() }} km<small v-if="data.computed.heading !== undefined">Bearing {{ data.computed.heading }}°</small></dd></div>
    <div v-if="hasValue(fields.cqz) || hasValue(fields.ituz)"><dt>Zones</dt><dd><span v-if="hasValue(fields.cqz)">CQ {{ fields.cqz }}</span><span v-if="hasValue(fields.ituz)">ITU {{ fields.ituz }}</span></dd></div>
   </dl>
   <p v-if="data.locationSource" class="enrichment-note">{{ data.locationSource }}<span v-if="data.stationGrid"> · From {{ data.stationGrid }} ({{ data.stationGridSource }})</span></p>
   <p v-if="data.reportedGrid && data.callbookGrid && data.reportedGrid !== data.callbookGrid" class="enrichment-note">Reported grid {{ data.reportedGrid }} is used for this contact; callbook grid {{ data.callbookGrid }} is retained separately.</p>
   <nav v-if="qrz" class="station-links" aria-label="Station sources"><a :href="`https://www.qrz.com/db/${encodeURIComponent(call)}`" target="_blank" rel="noopener noreferrer">QRZ profile ↗</a><a v-if="biography" :href="`https://www.qrz.com/db/${encodeURIComponent(call)}`" target="_blank" rel="noopener noreferrer">Biography on QRZ ↗</a></nav>
   <p v-if="groups.reduce((count, group) => count + group.fields.length, 0) > 5" class="station-details-hint">Available contact, license &amp; location information <span>Scroll for more ↓</span></p>
   <div v-if="groups.length || returned.length" class="station-details-scroll" tabindex="0" role="region" :aria-label="`Scrollable station details for ${call}`" :key="call">
    <section v-for="group in groups" :key="group.title" class="station-field-group"><h4>{{ group.title }}</h4><dl><div v-for="field in group.fields" :key="field.key"><dt>{{ field.label }}</dt><dd><a v-if="field.href" :href="field.href" :target="field.key === 'url' ? '_blank' : undefined" rel="noopener noreferrer">{{ field.value }} ↗</a><span v-else>{{ field.value }}</span><small v-if="field.source">{{ field.source }}</small></dd></div></dl></section>
    <details class="enrichment-details" v-if="returned.length" :key="`raw-${call}`"><summary>All returned fields · {{ returned.length }}</summary><div class="enrichment-table"><table class="table"><thead><tr><th>Field</th><th>Value</th><th>Source</th></tr></thead><tbody><tr v-for="[name, field] in returned" :key="name"><td>{{ name }}</td><td>{{ fieldText(field) }}</td><td>{{ data.fieldSources?.[name] }}</td></tr></tbody></table></div></details>
   </div>
   <div class="enrichment-providers station-provider-status"><p v-for="(provider, name) in data.providers" :key="name"><strong>{{ name }}</strong> · {{ provider.status }}<span v-if="provider.cached"> · cached</span><span v-if="provider.dataStatus === 'stale'"> · stale data</span><span v-if="provider.message"> · {{ provider.message }}</span><small v-if="provider.updatedAt">Retrieved {{ utc(provider.updatedAt) }}</small></p></div>
  </template>
 </section>
</template>
