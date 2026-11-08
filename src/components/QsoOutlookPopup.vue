<script setup lang="ts">
import { ref } from 'vue'
import type { QsoOutlook } from '../qsoOutlook'
import type { ReceptionSpot } from '../types'
defineProps<{ call: string; band?: string | null; mode?: string; outlook: QsoOutlook; confirmation?: ReceptionSpot; minutes: number; now: number }>()
defineEmits<{ close: [] }>()
const panel = ref<HTMLElement>()
defineExpose({ focus: () => panel.value?.focus({ preventScroll: true }) })
function age(at: number | null, now: number) {
 if (at === null) return 'No qualifying report'
 const minutes = Math.max(0, Math.floor((now - at) / 60000))
 return minutes < 1 ? 'Just now' : `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`
}
</script>
<template>
 <section ref="panel" class="qso-outlook-popup" role="dialog" :aria-label="`QSO Outlook details for ${call}`" tabindex="-1" @keydown.esc.stop.prevent="$emit('close')">
  <button type="button" class="qso-outlook-close" aria-label="Close QSO Outlook" @click="$emit('close')">×</button>
  <strong class="qso-outlook-title">{{ call }} · {{ band || 'Band unknown' }} {{ mode }}</strong>
  <p class="qso-outlook-score" :class="`outlook-${outlook.color}`">QSO Outlook: {{ outlook.score === null ? 'Unknown' : `${outlook.score}/100 — ${outlook.classification}` }}</p>
  <ul>
   <li>Direct reception: {{ confirmation ? `Confirmed · ${confirmation.mode || 'mode unknown'} · ${age(confirmation.heardAt, now)}${outlook.direct ? '' : ' (outside Outlook evidence)'}` : 'Not confirmed' }}</li>
   <li>Nearby receivers: {{ outlook.within200 }} within 200 km · {{ outlook.within500 }} within 500 km {{ outlook.nearbyMode ? `(${outlook.nearbyMode})` : '(all modes on band)' }}</li>
   <li>Nearest receiver: {{ outlook.nearestKm === null ? 'No qualifying nearby report' : `${outlook.nearestKm < 1 ? '<1' : Math.round(outlook.nearestKm)} km (approximate)` }}</li>
   <li>Latest reception: {{ age(outlook.latestAt, now) }}</li>
  </ul>
  <p class="qso-outlook-window">Outlook window: {{ Math.min(15, minutes) }} min · nearby: {{ Math.min(10, minutes) }} min.</p>
  <p>{{ outlook.explanation }}</p>
  <small>Experimental heuristic, not a calibrated probability. Does not account for antenna differences, interference, pileups or operator availability.</small>
 </section>
</template>
