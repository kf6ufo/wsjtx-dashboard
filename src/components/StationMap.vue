<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Map as LeafletMap, LayerGroup } from 'leaflet'
import type { EnrichmentState, Entry } from '../types'
import { stationMapLocation } from '../stationMap'
import { englishMapStyle, MAP_ATTRIBUTION, MAP_STYLE_URL } from '../mapStyle'
import 'leaflet/dist/leaflet.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

const props = defineProps<{ call: string; entry?: Entry; enrichment?: EnrichmentState }>()
const location = computed(() => stationMapLocation(props.call, props.entry, props.enrichment))
const host = ref<HTMLDivElement>(), tilesFailed = ref(false), mapFailed = ref(false), zoom = ref(4), ready = ref(false)
const basemapReady = ref(false)
let map: LeafletMap | undefined, markers: LayerGroup | undefined, observer: ResizeObserver | undefined
let basemapRequest: AbortController | undefined
let mounted = false, generation = 0
function destroy() { ready.value = false; basemapReady.value = false; basemapRequest?.abort(); observer?.disconnect(); observer = undefined; map?.remove(); map = undefined; markers = undefined }
async function loadBasemap(target: LeafletMap) {
 const controller = basemapRequest = new AbortController()
 const timeout = window.setTimeout(() => controller.abort(), 10000)
 try {
  const [adapter, renderer, response] = await Promise.all([
   import('@maplibre/maplibre-gl-leaflet/leaflet-maplibre-gl.js'), import('maplibre-gl'),
   fetch(MAP_STYLE_URL, { signal: controller.signal }),
  ])
  renderer.setWorkerUrl(mapWorkerUrl)
  if (!response.ok) throw new Error('Base map style unavailable')
  const style = englishMapStyle(await response.json())
  if (!mounted || map !== target || controller.signal.aborted) return
  const layer = adapter.maplibreGL({ style, attributionControl: false }).addTo(target)
  const vectorMap = layer.getMaplibreMap()
  vectorMap.on('load', () => { if (map === target) basemapReady.value = true })
  vectorMap.on('error', () => { if (map === target) tilesFailed.value = true })
 } catch { if (mounted && map === target) tilesFailed.value = true }
 finally { window.clearTimeout(timeout) }
}
function center() {
 const point = location.value
 if (point && map) map.setView([point.lat, point.lng], Math.max(map.getMinZoom(), point.zoom - 2), { animate: false })
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
   map = L.map(host.value, { zoomControl: false, fadeAnimation: false, minZoom: 2, maxZoom: 19, worldCopyJump: true, scrollWheelZoom: false, attributionControl: true, maxBounds: [[-85, -Infinity], [85, Infinity]], maxBoundsViscosity: 1 })
   map.attributionControl.addAttribution(MAP_ATTRIBUTION)
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
  if (!basemapRequest || basemapRequest.signal.aborted) void loadBasemap(map)
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
  <template v-else><div ref="host" class="station-map-canvas" role="region" :aria-label="`Map showing ${call}`" :data-lat="location.lat" :data-lng="location.lng" :data-zoom="zoom" :data-basemap-state="tilesFailed ? 'unavailable' : basemapReady ? 'ready' : 'loading'" @wheel.capture="modifierZoom"></div><p v-if="mapFailed" class="station-map-note error-text" role="status">Map could not load. Refresh the page to try again.</p><p v-else-if="tilesFailed" class="station-map-note" role="status">Base map unavailable. The station marker is still shown; map tiles need an internet connection and a browser with WebGL support.</p></template>
 </section>
</template>
