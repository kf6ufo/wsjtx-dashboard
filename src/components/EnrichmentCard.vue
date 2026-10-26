<script setup lang="ts">
import { computed, ref } from 'vue'
import StationDetailsScroll from './StationDetailsScroll.vue'
import type { EnrichmentState } from '../types'
import { fieldText, hasValue, stationTableRows, sortStationFields, type StationField } from '../stationDetails'
const props = defineProps<{ enrichment?: EnrichmentState; call: string; connected?: boolean }>()
const emit = defineEmits<{ refresh: [] }>()
const data = computed(() => props.enrichment?.result.call === props.call ? props.enrichment.result : undefined)
const fields = computed(() => data.value?.fields ?? {})
const sortColumn = ref<'label' | 'value'>('label'), sortDirection = ref<'ascending' | 'descending'>('ascending')
function sortBy(column: 'label' | 'value') {
 sortDirection.value = sortColumn.value === column && sortDirection.value === 'ascending' ? 'descending' : 'ascending'
 sortColumn.value = column
}
const rows = computed(() => {
 const values: StationField[] = data.value ? stationTableRows(data.value) : []
 const href = `https://www.qrz.com/db/${encodeURIComponent(props.call)}`
 if (biography.value) values.push({ key: 'biography', label: 'Biography', value: 'Biography on QRZ', href })
 if (qrz.value) values.push({ key: 'qrzPage', label: 'QRZ page', value: `${props.call} on QRZ`, href })
 return sortStationFields(values, sortColumn.value, sortDirection.value)
})
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
   <StationDetailsScroll v-if="rows.length || returned.length" :label="`Scrollable station details for ${call}`" :key="call">
    <table class="station-details-table"><thead><tr><th scope="col" :aria-sort="sortColumn === 'label' ? sortDirection : 'none'"><button class="details-sort-button" aria-label="Sort details by Field" @click="sortBy('label')">Field <span aria-hidden="true">{{ sortColumn === 'label' ? sortDirection === 'ascending' ? '↑' : '↓' : '↕' }}</span></button></th><th scope="col" :aria-sort="sortColumn === 'value' ? sortDirection : 'none'"><button class="details-sort-button" aria-label="Sort details by Value" @click="sortBy('value')">Value <span aria-hidden="true">{{ sortColumn === 'value' ? sortDirection === 'ascending' ? '↑' : '↓' : '↕' }}</span></button></th></tr></thead><tbody>
     <tr v-for="field in rows" :key="field.key" :data-field="field.key"><th scope="row">{{ field.label }}</th><td :title="field.source ? `Source: ${field.source}` : undefined" :class="{ 'detail-emphasis': ['reportedGrid','distance','heading'].includes(field.key) }"><a v-if="field.href" :href="field.href" :target="field.href.startsWith('mailto:') ? undefined : '_blank'" rel="noopener noreferrer">{{ field.value }} ↗</a><span v-else>{{ field.value }}</span><small v-if="field.source" class="visually-hidden">Source: {{ field.source }}</small></td></tr>
    </tbody></table>
    <details class="enrichment-details" v-if="returned.length" :key="`raw-${call}`"><summary>All returned fields · {{ returned.length }}</summary><div class="enrichment-table"><table class="table"><thead><tr><th>Field</th><th>Value</th><th>Source</th></tr></thead><tbody><tr v-for="[name, field] in returned" :key="name"><td>{{ name }}</td><td>{{ fieldText(field) }}</td><td>{{ data.fieldSources?.[name] }}</td></tr></tbody></table></div></details>
   </StationDetailsScroll>
   <p v-if="data.reportedGrid && data.callbookGrid && data.reportedGrid !== data.callbookGrid" class="enrichment-note">Reported grid {{ data.reportedGrid }} is used for this contact; callbook grid {{ data.callbookGrid }} is retained separately.</p>
   <div class="enrichment-providers station-provider-status"><p v-for="(provider, name) in data.providers" :key="name"><strong>{{ name }}</strong> · {{ provider.status }}<span v-if="provider.cached"> · cached</span><span v-if="provider.dataStatus === 'stale'"> · stale data</span><span v-if="provider.message"> · {{ provider.message }}</span><small v-if="provider.updatedAt">Retrieved {{ utc(provider.updatedAt) }}</small></p></div>
  </template>
  <button v-if="enrichment?.config.enabled" class="text-button details-refresh" :disabled="connected === false || data?.status === 'pending'" @click="emit('refresh')">Refresh details</button>
 </section>
</template>
