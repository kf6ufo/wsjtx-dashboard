<script setup lang="ts">
import { computed } from 'vue'
import type { EnrichmentState } from '../types'
import { stationKeyFacts } from '../stationDetails'
const props = defineProps<{ enrichment?: EnrichmentState; call: string }>()
const data = computed(() => props.enrichment?.result.call === props.call ? props.enrichment.result : undefined)
const facts = computed(() => data.value ? stationKeyFacts(data.value) : [])
const icons: Record<string, string> = { distance: '◎', heading: '➤', grid: '▦', lotw: '◇', eqsl: '✉' }
</script>
<template>
 <section v-if="facts.length" class="station-key-information" aria-labelledby="key-information-title">
  <h3 id="key-information-title">Key information</h3>
  <dl class="station-key-facts"><div v-for="fact in facts" :key="fact.key" :data-field="fact.key" :class="{ 'key-fact-positive': ['lotw', 'eqsl'].includes(fact.key) && fact.value === 'Yes' }" :title="fact.source"><span class="key-fact-icon" aria-hidden="true">{{ icons[fact.key] }}</span><div><dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd></div></div></dl>
  <p v-if="data?.locationSource" class="key-location-note">{{ data.locationSource }}<span v-if="data.stationGrid"> · From {{ data.stationGrid }}</span></p>
 </section>
</template>
