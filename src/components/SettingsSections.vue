<script setup lang="ts">
import { nextTick } from 'vue'
export type SettingsSection = 'workspace' | 'receiver' | 'enrichment' | 'wavelog' | 'qso' | 'history' | 'forwarding' | 'installation'
const section = defineModel<SettingsSection>({ default: 'workspace' })
const sections: { id: SettingsSection; label: string }[] = [
 { id: 'workspace', label: 'Workspace' }, { id: 'receiver', label: 'Radio receiver' },
 { id: 'enrichment', label: 'Callbook & enrichment' }, { id: 'wavelog', label: 'Wavelog connection' },
 { id: 'qso', label: 'QSO history & logging' }, { id: 'history', label: 'Focus History' },
 { id: 'forwarding', label: 'UDP forwarding' }, { id: 'installation', label: 'Installation' },
]
async function navigate(event: KeyboardEvent, index: number) {
 let next: number
 if (event.key === 'ArrowRight') next = (index + 1) % sections.length
 else if (event.key === 'ArrowLeft') next = (index + sections.length - 1) % sections.length
 else if (event.key === 'Home') next = 0
 else if (event.key === 'End') next = sections.length - 1
 else return
 event.preventDefault(); section.value = sections[next]!.id
 await nextTick(); document.getElementById(`settings-tab-${section.value}`)?.focus()
}
</script>
<template>
 <section class="utility-panel settings-view" aria-label="Settings">
  <h2>Settings</h2><p class="settings-intro">Choose a section. Each Save button applies only to that section. Unsaved edits stay here while you switch tabs.</p>
  <div class="settings-tabs" role="tablist" aria-label="Settings sections">
   <button v-for="(item, index) in sections" :key="item.id" :id="`settings-tab-${item.id}`" role="tab" :aria-selected="section === item.id" :aria-controls="`settings-panel-${item.id}`" :tabindex="section === item.id ? 0 : -1" @click="section = item.id" @keydown="navigate($event, index)">{{ item.label }}</button>
  </div>
  <section v-for="item in sections" :key="item.id" v-show="section === item.id" :id="`settings-panel-${item.id}`" class="settings-section-panel" role="tabpanel" :aria-labelledby="`settings-tab-${item.id}`" tabindex="0">
   <p class="settings-save-scope">{{ item.id === 'installation' ? 'Read-only installation information' : `Save scope: ${item.label}` }}</p>
   <slot :name="item.id"/>
  </section>
 </section>
</template>
