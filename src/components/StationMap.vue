<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Map as LeafletMap, LayerGroup, Marker } from 'leaflet'
import type { EnrichmentState, Entry, PskReporterState } from '../types'
import { gridLocation, stationMapLocation } from '../stationMap'
import { receptionLabel, receptionSpots } from '../pskreporter'
import { calculateQsoOutlook } from '../qsoOutlook'
import QsoOutlookPopup from './QsoOutlookPopup.vue'
import { englishMapStyle, MAP_ATTRIBUTION, MAP_STYLE_URL } from '../mapStyle'
import 'leaflet/dist/leaflet.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

const props = defineProps<{ call: string; entry?: Entry; enrichment?: EnrichmentState; receptions?: PskReporterState; sender?: string; connected?: boolean; fullscreen?: boolean }>()
const location = computed(() => stationMapLocation(props.call, props.entry, props.enrichment))
const frame = ref<HTMLElement>(), fillHeight = ref(0)
let layoutObserver: ResizeObserver | undefined, layoutFrame = 0
function sizeToViewport() {
 cancelAnimationFrame(layoutFrame)
 layoutFrame = requestAnimationFrame(() => {
  if (!props.fullscreen || !frame.value?.clientWidth) return
  // Use document position so scrolling to contacts does not grow the map again.
  const top = frame.value.getBoundingClientRect().top + window.scrollY
  fillHeight.value = Math.max(0, window.innerHeight - top - 10)
 })
}
watch(() => props.fullscreen, sizeToViewport)
onMounted(() => {
 layoutObserver = new ResizeObserver(sizeToViewport)
 layoutObserver.observe(document.body)
 // Async profile/status changes and navigation can move the map's top edge.
 if (frame.value?.parentElement) {
  layoutObserver.observe(frame.value.parentElement)
  for (const sibling of Array.from(frame.value.parentElement.children)) {
   layoutObserver.observe(sibling)
   if (sibling === frame.value) break
  }
 }
 window.addEventListener('resize', sizeToViewport)
 sizeToViewport()
})
onBeforeUnmount(() => { layoutObserver?.disconnect(); cancelAnimationFrame(layoutFrame); window.removeEventListener('resize', sizeToViewport) })
const minutes = ref(props.receptions?.config.window_minutes ?? 15), now = ref(Date.now())
const spots = computed(() => receptionSpots(props.receptions, props.sender ?? '', props.entry?.band, minutes.value, now.value))
const outlook = computed(() => calculateQsoOutlook({ feed: props.receptions, sender: props.sender ?? '', call: props.call,
 band: props.entry?.band, mode: props.entry?.mode, location: location.value, minutes: minutes.value, now: now.value }))
const focusSpot = computed(() => spots.value.find(spot => spot.receiver === props.call) ?? outlook.value.direct)
const outlookSummary = computed(() => `QSO Outlook: ${outlook.value.score === null ? 'Unknown' : `${outlook.value.score}/100 — ${outlook.value.classification}`}`)
const popupOpen = ref(false), popup = ref<InstanceType<typeof QsoOutlookPopup>>()
async function toggleOutlook() {
 if (popupOpen.value) { closeOutlook(); return }
 popupOpen.value = true
 await nextTick()
 popup.value?.focus()
}
function closeOutlook() { popupOpen.value = false; focusMarker?.getElement()?.focus({ preventScroll: true }) }
const receptionStatus = computed(() => {
 const feed = props.receptions
 if (!feed?.config.enabled) return 'Reception overlay off · enable PSKReporter in Settings.'
 if (!props.connected) return 'Dashboard disconnected · reports may be incomplete; recent dots continue to expire.'
 if (!props.sender) return 'Waiting for the selected radio’s station callsign. Set a callsign override in PSKReporter Settings if needed.'
 if (!props.entry?.band) return 'Focus band unknown · no reception dots shown.'
 if (feed.status !== 'connected') return `PSKReporter ${feed.status} · ${feed.error || 'Waiting for the live feed.'} Recent dots continue to expire.`
 return `${spots.value.length} ${spots.value.length === 1 ? 'station' : 'stations'} reported hearing ${props.sender} on ${props.entry.band} · last ${minutes.value} min · collecting while Dashboard runs`
})
const receptionNeedsAttention = computed(() => props.receptions?.config.enabled && (!props.connected || !props.sender || !props.entry?.band || props.receptions.status !== 'connected'))
const receptionSummary = computed(() => {
 if (!props.receptions?.config.enabled) return 'PSKReporter off'
 if (receptionNeedsAttention.value) return 'PSKReporter · check status'
 return `${spots.value.length} heard ${props.sender} · ${props.entry?.band}`
})
const host = ref<HTMLDivElement>(), tilesFailed = ref(false), mapFailed = ref(false), zoom = ref(4), ready = ref(false)
const basemapReady = ref(false)
let map: LeafletMap | undefined, markers: LayerGroup | undefined, receptionMarkers: LayerGroup | undefined, observer: ResizeObserver | undefined
let focusMarker: Marker | undefined
let ageTimer: number | undefined
let basemapRequest: AbortController | undefined
let mounted = false, generation = 0
function destroy() { ready.value = false; basemapReady.value = false; basemapRequest?.abort(); observer?.disconnect(); observer = undefined; map?.remove(); map = undefined; markers = undefined; receptionMarkers = undefined; focusMarker = undefined }
function updateOutlook() {
 const element = focusMarker?.getElement()
 if (!element) return
 element.dataset.outlook = outlook.value.color
 element.dataset.outlookScore = String(outlook.value.score ?? 'unknown')
 element.setAttribute('aria-label', `Station location for ${props.call}. ${outlookSummary.value}. Open outlook details`)
 element.title = `${props.call} · ${outlookSummary.value} · Activate for evidence`
 element.setAttribute('aria-haspopup', 'dialog')
 element.setAttribute('aria-expanded', String(popupOpen.value))
}
async function updateReceptions() {
 const target = map
 if (!target || !receptionMarkers) return
 const L = await import('leaflet')
 if (map !== target || !receptionMarkers) return
 receptionMarkers.clearLayers()
 for (const spot of spots.value) {
  const point = spot.receiver === props.call ? location.value : gridLocation(spot.grid)
  if (!point) continue
  const text = document.createElement('span'); text.textContent = receptionLabel(spot, now.value)
  // Plot nearby receivers across the date line in the focus station's world.
  const lng = point.lng + 360 * Math.round(((location.value?.lng ?? point.lng) - point.lng) / 360)
  const marker = L.marker([point.lat, lng], {
   icon: L.divIcon({ className: 'station-map-reception', html: '<span aria-hidden="true"></span>', iconSize: [10, 10], iconAnchor: [5, 5] }),
   title: text.textContent, keyboard: true, zIndexOffset: spot.receiver === props.call ? 1100 : 1000,
  }).bindTooltip(text, { direction: 'top' }).addTo(receptionMarkers)
  marker.getElement()?.setAttribute('aria-label', text.textContent)
  // The amber center dot sits above the pin; it toggles the same focus popup.
  if (spot.receiver === props.call) marker.on('click', toggleOutlook)
 }
}
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
   receptionMarkers = L.layerGroup().addTo(map)
   map.on('zoomend', () => { zoom.value = map!.getZoom() })
   // v-show navigation and column resizing must not leave a half-rendered map.
   observer = new ResizeObserver(() => { if (host.value?.clientWidth) map?.invalidateSize({ animate: false, pan: true }) })
   observer.observe(host.value)
  }
  markers!.clearLayers()
  const point = location.value
  if (point.bounds) L.rectangle(point.bounds, { color: '#16899c', weight: 1, fillOpacity: .07, interactive: false }).addTo(markers!)
  const text = document.createElement('span'); text.textContent = props.call
  const marker = focusMarker = L.marker([point.lat, point.lng], {
   icon: L.divIcon({ className: 'station-map-pin', html: '<span aria-hidden="true"></span>', iconSize: [24, 24], iconAnchor: [12, 12] }),
   title: `${props.call} · ${point.detail}`, keyboard: true,
  }).bindTooltip(text, { permanent: true, direction: 'top', offset: [0, -18] })
   .addTo(markers!)
  // A new Leaflet map creates marker elements only after its first setView.
  center()
  const element = marker.getElement()
  element?.setAttribute('aria-expanded', 'false')
  element?.addEventListener('keydown', event => {
   if (event.key === ' ' || event.key === 'Enter') { event.preventDefault(); event.stopPropagation(); void toggleOutlook() }
  })
  marker.on('click', toggleOutlook)
  updateOutlook()
  if (!basemapRequest || basemapRequest.signal.aborted) void loadBasemap(map)
  ready.value = true
  void updateReceptions()
 } catch { if (request === generation) { destroy(); mapFailed.value = true } }
}
watch(() => JSON.stringify([props.call, location.value]), () => { popupOpen.value = false; void update() })
watch(() => props.receptions?.config.window_minutes, value => { if (value) minutes.value = value })
watch(() => JSON.stringify([spots.value, props.call, Math.floor(now.value / 60000)]), updateReceptions)
watch(() => JSON.stringify([outlook.value, popupOpen.value, props.entry?.band, props.entry?.mode]), updateOutlook)
onMounted(() => { mounted = true; update(); ageTimer = window.setInterval(() => { now.value = Date.now() }, 10000) })
onBeforeUnmount(() => { mounted = false; generation++; window.clearInterval(ageTimer); destroy() })
</script>
<template>
 <section ref="frame" class="station-map" :class="{ 'station-map-fill': fullscreen && location }" :style="fullscreen && location ? { minHeight: `${fillHeight}px` } : undefined" aria-labelledby="station-map-title">
  <div class="station-map-heading">
   <div class="station-map-identity"><h3 id="station-map-title">Station map</h3><span v-if="location" class="station-map-location" :title="`${call} · ${location.label} · ${location.detail}`">{{ call }} · {{ location.label }}<span class="visually-hidden"> · {{ location.detail }}</span></span></div>
   <div v-if="receptions" class="station-map-summary" :title="receptionStatus" role="status"><span class="station-map-heard"><i v-if="receptions.config.enabled" class="reception-legend-dot" aria-hidden="true"></i>{{ receptionSummary }}</span><span v-if="focusSpot" class="station-map-focus-heard">Heard you: Confirmed · {{ Math.max(0, Math.floor((now - focusSpot.heardAt) / 60000)) }} min ago</span></div>
   <label v-if="receptions?.config.enabled" class="station-map-window"><span class="visually-hidden">Reception time window</span><select v-model.number="minutes" aria-label="Reception time window"><option v-for="n in [5,15,30,60]" :key="n" :value="n">Last {{ n }} min</option></select></label>
   <div v-if="location" class="station-map-controls" aria-label="Map controls"><button class="btn console-button" :disabled="zoom >= 19 || !ready" aria-label="Zoom in station map" @click="map?.zoomIn()">+</button><button class="btn console-button" :disabled="zoom <= 2 || !ready" aria-label="Zoom out station map" @click="map?.zoomOut()">−</button><button class="btn console-button" :disabled="!ready" aria-label="Center station" @click="center">Center</button></div>
  </div>
  <p v-if="receptionNeedsAttention || receptions?.evicted" class="station-map-note" role="status"><span v-if="receptionNeedsAttention">{{ receptionStatus }}</span><span v-if="receptions?.evicted"> Reception cache reached capacity; some reports were dropped.</span></p>
  <p v-if="!location" class="station-map-empty" role="status">{{ enrichment?.result.call === call && enrichment.result.status === 'pending' ? `Locating ${call}…` : 'Station location unavailable. A reported grid or callbook location is needed.' }} QSO Outlook: Unknown.</p>
  <template v-else><div class="station-map-surface"><div ref="host" class="station-map-canvas" role="region" :aria-label="`Map showing ${call}`" :data-lat="location.lat" :data-lng="location.lng" :data-zoom="zoom" :data-basemap-state="tilesFailed ? 'unavailable' : basemapReady ? 'ready' : 'loading'" @wheel.capture="modifierZoom"></div><QsoOutlookPopup v-if="popupOpen" ref="popup" :call="call" :band="entry?.band" :mode="entry?.mode" :outlook="outlook" :confirmation="focusSpot" :minutes="minutes" :now="now" @close="closeOutlook" /></div><p v-if="mapFailed" class="station-map-note error-text" role="status">Map could not load. Refresh the page to try again.</p><p v-else-if="tilesFailed" class="station-map-note" role="status">Base map unavailable. The station marker is still shown; map tiles need an internet connection and a browser with WebGL support.</p></template>
  <p v-if="receptions?.config.enabled" class="station-map-note reception-footnote">PSKReporter · reports may be delayed; no dot means no recent report. Dots use approximate receiver grids. Focus reception stays centered inside its marker. QSO Outlook ring is experimental; activate the station marker for evidence. <a href="https://www.mqtt.pskreporter.info/" target="_blank" rel="noopener noreferrer">Feed by M0LTE, data by PSKReporter ↗</a></p>
 </section>
</template>
