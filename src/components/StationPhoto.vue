<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { photoUrl } from '../photos'
const props = defineProps<{ call: string; src?: unknown; compact?: boolean }>()
const image = computed(() => photoUrl(props.src))
const failed = ref(false)
watch(() => [props.call, image.value], () => { failed.value = false })
</script>
<template>
 <div class="station-photo" :class="{ 'station-photo-compact': compact }">
  <img v-if="image && !failed" :src="image" :alt="`QRZ profile for ${call}`" referrerpolicy="no-referrer" :loading="compact ? 'lazy' : 'eager'" decoding="async" @error="failed = true">
  <div v-else class="station-photo-placeholder" role="img" :aria-label="`No profile photo available for ${call}`"><svg viewBox="0 0 80 80" aria-hidden="true"><circle cx="40" cy="28" r="14"/><path d="M12 76v-6a28 28 0 0 1 56 0v6Z"/></svg><span v-if="!compact">No profile pic</span></div>
 </div>
</template>
<style scoped>
.station-photo{width:100%;aspect-ratio:1;overflow:hidden;border:1px solid var(--line);border-radius:9px;background:rgba(120,150,160,.08)}
.station-photo img{display:block;width:100%;height:100%;object-fit:contain}
.station-photo-placeholder{height:100%;display:flex;align-items:center;justify-content:center;flex-direction:column;color:var(--muted)}
.station-photo-placeholder svg{width:65%;max-width:110px;fill:currentColor;opacity:.45}.station-photo-placeholder span{font-size:11px;margin-top:12px}
.station-photo-compact{width:58px;height:58px;aspect-ratio:auto;flex-shrink:0;border-radius:7px}
</style>
