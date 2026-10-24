<script setup lang="ts">
import { computed } from 'vue'
import type { EnrichmentState } from '../types'
import { fieldText, hasValue, stationTableRows } from '../stationDetails'
const props = defineProps<{ enrichment?: EnrichmentState; call: string; connected?: boolean }>()
const emit = defineEmits<{ refresh: [] }>()
const data = computed(() => props.enrichment?.result.call === props.call ? props.enrichment.result : undefined)
const fields = computed(() => data.value?.fields ?? {})
const rows = computed(() => data.value ? stationTableRows(data.value) : [])
const returned = computed(() => Object.entries(fields.value).filter(([, value]) => hasValue(value)))
const qrz = computed(() => data.value?.providers?.qrz?.status === 'loaded')
const biography = computed(() => qrz.value && Number(fields.value.bio) > 0)
function utc(raw?: number) { return raw ? new Date(raw).toISOString().replace('T', ' ').slice(0,19) + ' UTC' : '' }
</script>
<template>
 <section class="enrichment-card station-details" aria-labelledby="radio-enrichment-title">
  <div class="enrichment-heading"><h3 id="radio-enrichment-title">Details</h3><a v-if="qrz" class="details-source-link" :href="`https://www.qrz.com/db/${encodeURIComponent(call)}`" target="_blank" rel="noopener noreferrer">Data from QRZ.com ↗</a><span v-else class="enrichment-state" role="status">{{ data?.status ?? (enrichment?.config.enabled ? 'Waiting for selection' : 'Disabled') }}</span></div>
  <p v-if="!enrichment?.config.enabled" class="muted-state">Enable enrichment and configure providers in Settings.</p>
  <p v-else-if="data?.status === 'pending'" role="status">Looking up {{ call }}… Radio reception continues.</p>
  <template v-else-if="data && data.status !== 'disabled' && data.status !== 'idle'">
   <p v-if="data.message" class="error-text">{{ data.message }}</p>
   <p v-if="data.status === 'empty'" class="muted-state">No matching station details were returned by the configured providers.</p>
   <div v-if="rows.length || returned.length" class="station-details-scroll" tabindex="0" role="region" :aria-label="`Scrollable station details for ${call}`" :key="call">
    <table class="station-details-table"><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>
     <tr v-if="biography"><th scope="row">Biography</th><td><a :href="`https://www.qrz.com/db/${encodeURIComponent(call)}`" target="_blank" rel="noopener noreferrer">Biography on QRZ ↗</a></td></tr>
     <tr v-for="field in rows" :key="field.key" :data-field="field.key"><th scope="row">{{ field.label }}</th><td :title="field.source ? `Source: ${field.source}` : undefined" :class="{ 'detail-emphasis': ['reportedGrid','distance','heading'].includes(field.key) }"><a v-if="field.href" :href="field.href" :target="field.key === 'url' ? '_blank' : undefined" rel="noopener noreferrer">{{ field.value }} ↗</a><span v-else>{{ field.value }}</span><small v-if="field.source" class="visually-hidden">Source: {{ field.source }}</small></td></tr>
     <tr v-if="qrz"><th scope="row">QRZ page</th><td><a :href="`https://www.qrz.com/db/${encodeURIComponent(call)}`" target="_blank" rel="noopener noreferrer">{{ call }} on QRZ ↗</a></td></tr>
    </tbody></table>
    <details class="enrichment-details" v-if="returned.length" :key="`raw-${call}`"><summary>All returned fields · {{ returned.length }}</summary><div class="enrichment-table"><table class="table"><thead><tr><th>Field</th><th>Value</th><th>Source</th></tr></thead><tbody><tr v-for="[name, field] in returned" :key="name"><td>{{ name }}</td><td>{{ fieldText(field) }}</td><td>{{ data.fieldSources?.[name] }}</td></tr></tbody></table></div></details>
   </div>
   <p v-if="data.reportedGrid && data.callbookGrid && data.reportedGrid !== data.callbookGrid" class="enrichment-note">Reported grid {{ data.reportedGrid }} is used for this contact; callbook grid {{ data.callbookGrid }} is retained separately.</p>
   <div class="enrichment-providers station-provider-status"><p v-for="(provider, name) in data.providers" :key="name"><strong>{{ name }}</strong> · {{ provider.status }}<span v-if="provider.cached"> · cached</span><span v-if="provider.dataStatus === 'stale'"> · stale data</span><span v-if="provider.message"> · {{ provider.message }}</span><small v-if="provider.updatedAt">Retrieved {{ utc(provider.updatedAt) }}</small></p></div>
  </template>
  <button v-if="enrichment?.config.enabled" class="text-button details-refresh" :disabled="connected === false || data?.status === 'pending'" @click="emit('refresh')">Refresh details</button>
 </section>
</template>
