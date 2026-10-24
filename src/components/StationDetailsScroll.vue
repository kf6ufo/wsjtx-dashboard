<script setup lang="ts">
import { computed, onMounted, onUnmounted, onUpdated, reactive, ref, useId } from 'vue'
const props = defineProps<{ label: string }>()
const id = useId()
const viewport = ref<HTMLElement | null>(null), content = ref<HTMLElement | null>(null)
const sizes = reactive({ x: 0, y: 0, width: 0, height: 0, contentWidth: 0, contentHeight: 0 })
const maxX = computed(() => Math.max(0, sizes.contentWidth - sizes.width))
const maxY = computed(() => Math.max(0, sizes.contentHeight - sizes.height))
const thumbX = computed(() => Math.min(100, Math.max(8, sizes.width / (sizes.contentWidth || 1) * 100)))
const thumbY = computed(() => Math.min(100, Math.max(8, sizes.height / (sizes.contentHeight || 1) * 100)))
const left = computed(() => maxX.value ? sizes.x / maxX.value * (100 - thumbX.value) : 0)
const top = computed(() => maxY.value ? sizes.y / maxY.value * (100 - thumbY.value) : 0)
function measure() {
 const el = viewport.value
 if (el) Object.assign(sizes, { x: el.scrollLeft, y: el.scrollTop, width: el.clientWidth, height: el.clientHeight, contentWidth: el.scrollWidth, contentHeight: el.scrollHeight })
}
function setPosition(axis: 'x' | 'y', value: number) {
 const el = viewport.value
 if (!el) return
 if (axis === 'x') el.scrollLeft = value
 else el.scrollTop = value
 measure()
}
let dragging: { axis: 'x' | 'y'; offset: number } | null = null
function move(event: PointerEvent) {
 if (!dragging) return
 const track = event.currentTarget as HTMLElement, box = track.getBoundingClientRect()
 const horizontal = dragging.axis === 'x', length = horizontal ? box.width : box.height
 const thumb = horizontal ? thumbX.value : thumbY.value
 const point = horizontal ? event.clientX - box.left : event.clientY - box.top
 const ratio = (point - dragging.offset) / (length * (1 - thumb / 100) || 1)
 setPosition(dragging.axis, Math.max(0, Math.min(1, ratio)) * (horizontal ? maxX.value : maxY.value))
}
function start(event: PointerEvent, axis: 'x' | 'y') {
 if (event.button !== 0 || !(axis === 'x' ? maxX.value : maxY.value)) return
 const track = event.currentTarget as HTMLElement, thumb = track.firstElementChild!.getBoundingClientRect()
 const isThumb = event.target === track.firstElementChild
 dragging = { axis, offset: isThumb ? axis === 'x' ? event.clientX - thumb.left : event.clientY - thumb.top : (axis === 'x' ? thumb.width : thumb.height) / 2 }
 track.focus(); track.setPointerCapture(event.pointerId); move(event); event.preventDefault()
}
function stop(event: PointerEvent) {
 dragging = null
 const track = event.currentTarget as HTMLElement
 if (track.hasPointerCapture(event.pointerId)) track.releasePointerCapture(event.pointerId)
}
function key(event: KeyboardEvent, axis: 'x' | 'y') {
 const current = axis === 'x' ? sizes.x : sizes.y, page = axis === 'x' ? sizes.width : sizes.height, maximum = axis === 'x' ? maxX.value : maxY.value
 const changes: Record<string, number> = { ArrowLeft: -40, ArrowUp: -40, ArrowRight: 40, ArrowDown: 40, PageUp: -page, PageDown: page }
 if (event.key === 'Home') setPosition(axis, 0)
 else if (event.key === 'End') setPosition(axis, maximum)
 else if (event.key in changes) setPosition(axis, current + changes[event.key]!)
 else return
 event.preventDefault()
}
let observer: ResizeObserver | undefined
onMounted(() => {
 measure()
 if (typeof ResizeObserver !== 'undefined') {
  observer = new ResizeObserver(measure)
  if (viewport.value) observer.observe(viewport.value)
  if (content.value) observer.observe(content.value)
 }
})
onUpdated(measure)
onUnmounted(() => observer?.disconnect())
</script>
<template>
 <div class="details-scroll-frame">
  <div :id="id" ref="viewport" class="station-details-scroll" tabindex="0" role="region" :aria-label="props.label" @scroll="measure"><div ref="content" class="details-scroll-content"><slot/></div></div>
  <div class="details-scrollbar details-scrollbar-y" role="scrollbar" aria-label="Scroll station details vertically" aria-orientation="vertical" :aria-controls="id" :aria-valuemin="0" :aria-valuemax="maxY" :aria-valuenow="sizes.y" :aria-disabled="maxY === 0" :tabindex="maxY ? 0 : -1" @keydown="key($event, 'y')" @pointerdown="start($event, 'y')" @pointermove="move" @pointerup="stop" @pointercancel="stop"><div class="details-scroll-thumb" :style="{ top: `${top}%`, height: `${thumbY}%` }"/></div>
  <div class="details-scrollbar details-scrollbar-x" role="scrollbar" aria-label="Scroll station details horizontally" aria-orientation="horizontal" :aria-controls="id" :aria-valuemin="0" :aria-valuemax="maxX" :aria-valuenow="sizes.x" :aria-disabled="maxX === 0" :tabindex="maxX ? 0 : -1" @keydown="key($event, 'x')" @pointerdown="start($event, 'x')" @pointermove="move" @pointerup="stop" @pointercancel="stop"><div class="details-scroll-thumb" :style="{ left: `${left}%`, width: `${thumbX}%` }"/></div>
 </div>
</template>
