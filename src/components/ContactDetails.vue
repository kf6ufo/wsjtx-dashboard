<script setup lang="ts">
import { computed } from 'vue'
import type { Qso } from '../types'
import { hasValue } from '../stationDetails'
const props = defineProps<{ qso: Qso; radio: boolean }>()
const labels: Record<string, string> = { name: 'Operator', qth: 'QTH', comment: 'Comment', notes: 'Notes', freq: 'Frequency (Hz)', freq_rx: 'Receive frequency (Hz)', tx_pwr: 'Power (W)', prop_mode: 'Propagation', sat_name: 'Satellite', sat_mode: 'Satellite mode', operator: 'Logging operator', state: 'State / province', cnty: 'County', qsl_via: 'QSL via', sota_ref: 'SOTA', pota_ref: 'POTA', wwff_ref: 'WWFF', iota: 'IOTA' }
const extras = computed(() => Object.entries(props.qso.details ?? {}).filter(([, value]) => hasValue(value)))
const utcDate = (date: string) => new Date(date).toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
</script>
<template>
 <div class="contact-detail-scroll" role="region" tabindex="0" aria-label="Scrollable contact details"><dl class="contact-details-grid">
  <dt>Date / time</dt><dd>{{ utcDate(qso.date) }}</dd>
  <dt>Band / mode</dt><dd>{{ qso.band }} / {{ qso.mode }}</dd>
  <template v-if="qso.sent || qso.received"><dt>Sent / received</dt><dd>{{ qso.sent || 'Not recorded' }} / {{ qso.received || 'Not recorded' }}</dd></template>
  <dt>Station callsign</dt><dd>{{ qso.station }}</dd>
  <template v-if="qso.grid"><dt>Reported contact grid</dt><dd>{{ qso.grid }}</dd></template>
  <dt>{{ radio ? 'Confirmation' : 'Sample confirmation' }}</dt><dd>{{ qso.confirmed === null ? 'Unavailable' : qso.confirmed ? 'Confirmed' : radio ? 'Unconfirmed' : 'Pending' }}</dd>
  <template v-if="radio"><dt>QSO ID</dt><dd>{{ qso.id }}</dd><template v-if="qso.stationName"><dt>Station location</dt><dd>{{ qso.stationName }}</dd></template><template v-for="confirmation in qso.confirmations" :key="confirmation.type"><dt>{{ confirmation.type }}</dt><dd>{{ confirmation.date || 'Received' }}</dd></template><template v-for="[key, value] in extras" :key="key"><dt>{{ labels[key] || key.replaceAll('_', ' ') }}</dt><dd>{{ value }}</dd></template></template>
 </dl></div>
</template>
