<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { Dashboard } from '../focus'
import UdpDiagnostics from './UdpDiagnostics.vue'
import PskReporterDiagnostics from './PskReporterDiagnostics.vue'
defineProps<{ dashboard: Dashboard }>()
const tab = ref<'udp' | 'pskreporter'>('udp')
const tabs = [{id:'udp',label:'UDP'}, {id:'pskreporter',label:'PSKReporter MQTT'}] as const
async function navigate(event: KeyboardEvent, index: number) {
 if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return
 event.preventDefault()
 tab.value = tabs[event.key === 'Home' ? 0 : event.key === 'End' ? 1 : (index+1)%2]!.id
 await nextTick(); document.getElementById(`diagnostics-tab-${tab.value}`)?.focus()
}
</script>
<template>
 <section class="utility-panel diagnostics-view" aria-label="Diagnostics">
  <h2>Diagnostics</h2>
  <p class="diagnostic-note">{{ dashboard.state.preferences.title }} · receive-only interface diagnostics</p>
  <div class="settings-tabs diagnostics-tabs" role="tablist" aria-label="Diagnostics interfaces">
   <button v-for="(item,index) in tabs" :key="item.id" :id="`diagnostics-tab-${item.id}`" role="tab" :aria-selected="tab === item.id" :aria-controls="`diagnostics-panel-${item.id}`" :tabindex="tab === item.id ? 0 : -1" @click="tab = item.id" @keydown="navigate($event,index)">{{ item.label }}</button>
  </div>
  <div v-show="tab === 'udp'" id="diagnostics-panel-udp" class="diagnostics-interface" role="tabpanel" aria-labelledby="diagnostics-tab-udp"><UdpDiagnostics :dashboard="dashboard" :active="tab === 'udp'"/></div>
  <div v-show="tab === 'pskreporter'" id="diagnostics-panel-pskreporter" class="diagnostics-interface" role="tabpanel" aria-labelledby="diagnostics-tab-pskreporter"><PskReporterDiagnostics :dashboard="dashboard" :active="tab === 'pskreporter'"/></div>
 </section>
</template>
