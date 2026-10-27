<script setup lang="ts">
import type { StationAssociation } from '../types'
defineProps<{ associations: StationAssociation[] }>()
</script>
<template>
 <div class="station-associations">
  <h4>Detected station associations</h4><p>Locations match the completed QSO's station callsign. These previews use the latest verified WSJT-X identity; explicit overrides take priority. Loading locations does not enable submissions.</p>
  <div class="instances-scroll"><table class="table qso-table"><thead><tr><th>WSJT-X instance</th><th>Station callsign</th><th>Wavelog location</th></tr></thead><tbody>
   <tr v-for="row in associations" :key="row.rigId"><td>{{ row.rigId }}</td><td>{{ row.stationCall || 'Not reported' }}</td><td><template v-if="row.stationId">{{ row.location }} · ID {{ row.stationId }}<small>{{ row.status === 'automatic' ? 'Automatic match' : 'Explicit override' }}</small></template><span v-else>{{ row.message }}</span></td></tr>
   <tr v-if="!associations.length"><td colspan="3">No WSJT-X instances heard yet.</td></tr>
  </tbody></table></div>
 </div>
</template>
