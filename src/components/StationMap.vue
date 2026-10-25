<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Map as LeafletMap, LayerGroup } from 'leaflet'
import type { EnrichmentState, Entry } from '../types'
import { stationMapLocation } from '../stationMap'
import 'leaflet/dist/leaflet.css'

const props = defineProps<{ call: string; entry?: Entry; enrichment?: EnrichmentState }>()
const location = computed(() => stationMapLocation(props.call, props.entry, props.enrichment))
const host = ref<HTMLDivElement>(), tilesFailed = ref(false), mapFailed = ref(false), zoom = ref(6), ready = ref(false)
let map: LeafletMap | undefined, markers: LayerGroup | undefined, observer: ResizeObserver | undefined
let mounted = false, generation = 0
function destroy() { ready.value = false; observer?.disconnect(); observer = undefined; map?.remove(); map = undefined; markers = undefined }
function center() {
 const point = location.value
 if (point) map?.setView([point.lat, point.lng], point.zoom, { animate: false })
}
function modifierZoom(event: WheelEvent) {
 // Capture runs before Leaflet's wheel listener, retaining its trackpad debounce.
 if (event.metaKey || event.ctrlKey) map?.scrollWheelZoom.enable()
 else map?.scrollWheelZoom.disable()
}
async function update() {
 const request = ++generation
 await nextTick()
 if (!mounted || request !== generation) return
 if (!location.value || !host.value) { destroy(); return }
 try {
  const L = await import('leaflet')
  if (!mounted || request !== generation || !host.value || !location.value) return
  mapFailed.value = false
  if (!map) {
   tilesFailed.value = false
   map = L.map(host.value, { zoomControl: false, fadeAnimation: false, minZoom: 2, maxZoom: 19, worldCopyJump: true, scrollWheelZoom: false, attributionControl: true })
   L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, detectRetina: false,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
   }).on('tileerror', () => { tilesFailed.value = true }).addTo(map)
   L.control.scale({ imperial: false }).addTo(map)
   markers = L.layerGroup().addTo(map)
   map.on('zoomend', () => { zoom.value = map!.getZoom() })
   // v-show navigation and column resizing must not leave a half-rendered map.
   observer = new ResizeObserver(() => { if (host.value?.clientWidth) map?.invalidateSize({ pan: false }) })
   observer.observe(host.value)
  }
  markers!.clearLayers()
  const point = location.value
  if (point.bounds) L.rectangle(point.bounds, { color: '#16899c', weight: 1, fillOpacity: .07, interactive: false }).addTo(markers!)
  const text = document.createElement('span'); text.textContent = props.call
  const marker = L.marker([point.lat, point.lng], {
   icon: L.divIcon({ className: 'station-map-pin', html: '<span aria-hidden="true"></span>', iconSize: [24, 24], iconAnchor: [12, 12] }),
   title: `${props.call} · ${point.detail}`, keyboard: true,
  }).bindTooltip(text, { permanent: true, direction: 'top', offset: [0, -12] }).addTo(markers!)
  center()
  marker.getElement()?.setAttribute('aria-label', `Station location for ${props.call}`)
  ready.value = true
 } catch { if (request === generation) { destroy(); mapFailed.value = true } }
}
watch(() => JSON.stringify([props.call, location.value]), update)
onMounted(() => { mounted = true; update() })
onBeforeUnmount(() => { mounted = false; generation++; destroy() })
</script>
<template>
 <section class="station-map" aria-labelledby="station-map-title">
  <div class="station-map-heading"><div><h3 id="station-map-title">Station map</h3><p v-if="location">{{ call }} · {{ location.label }} · {{ location.detail }}</p></div><div v-if="location" class="station-map-controls" aria-label="Map controls"><button class="btn console-button" :disabled="zoom >= 19 || !ready" aria-label="Zoom in station map" @click="map?.zoomIn()">+</button><button class="btn console-button" :disabled="zoom <= 2 || !ready" aria-label="Zoom out station map" @click="map?.zoomOut()">−</button><button class="btn console-button" :disabled="!ready" @click="center">Center station</button></div></div>
  <p v-if="!location" class="station-map-empty" role="status">{{ enrichment?.result.call === call && enrichment.result.status === 'pending' ? `Locating ${call}…` : 'Station location unavailable. A reported grid or callbook location is needed.' }}</p>
  <template v-else><div ref="host" class="station-map-canvas" role="region" :aria-label="`Map showing ${call}`" :data-lat="location.lat" :data-lng="location.lng" :data-zoom="zoom" @wheel.capture="modifierZoom"></div><p v-if="mapFailed" class="station-map-note error-text" role="status">Map could not load. Refresh the page to try again.</p><p v-else-if="tilesFailed" class="station-map-note" role="status">Base map unavailable. The station marker is still shown; map tiles need an internet connection.</p></template>
 </section>
</template>
