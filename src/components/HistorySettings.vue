<script setup lang="ts">
import { ref, reactive, watch, nextTick } from 'vue'
import type { Dashboard } from '../focus'
import type { HistorySettings } from '../types'
const props = defineProps<{ dashboard: Dashboard }>()
const draft = reactive<HistorySettings>({ limit: 200, retention_days: 0 })
const busy = ref(false), message = ref(''), confirm = ref<HTMLDialogElement>()
watch(() => JSON.stringify(props.dashboard.state.historySettings), value => { if (value) Object.assign(draft, JSON.parse(value)) }, { immediate: true })
async function save() {
 busy.value = true; message.value = ''
 try {
  const response = await fetch('/api/history/settings', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(draft) })
  if (!response.ok) throw new Error()
  props.dashboard.applySnapshot(await response.json(), false); message.value = 'Focus History settings saved.'
 } catch { message.value = 'History settings could not be saved. Check the server connection.' }
 finally { busy.value = false }
}
async function openClear() { await nextTick(); confirm.value?.showModal() }
async function clear() {
 busy.value = true; message.value = ''
 try {
  const response = await fetch('/api/history', { method: 'DELETE' })
  if (!response.ok) throw new Error()
  props.dashboard.applySnapshot(await response.json(), false); message.value = 'Focus History cleared. The next changed radio selection will appear.'; confirm.value?.close()
 } catch { message.value = 'History could not be cleared. Check local storage and the connection.' }
 finally { busy.value = false }
}
</script>
<template>
 <form class="settings-form focus-history-form" aria-label="Focus History settings" @submit.prevent="save">
  <h3>Focus History</h3>
  <label>Maximum saved stations<select v-model.number="draft.limit" class="form-select"><option v-for="n in [50,100,200,500]" :key="n" :value="n">{{ n }}</option></select></label>
  <label>Retain selected stations<select v-model.number="draft.retention_days" class="form-select"><option :value="0">Until manually cleared</option><option :value="30">30 days</option><option :value="7">7 days</option></select></label>
  <p>Age follows radio selection time. Browsing, received telemetry and contact updates do not extend retention.</p>
  <button class="btn btn-success" :disabled="busy || dashboard.state.connection !== 'connected'">Save Focus History settings</button>
  <button class="btn console-button" type="button" @click="openClear" :disabled="busy || dashboard.state.connection !== 'connected'">Clear Focus History…</button>
  <p role="status">{{ message }}</p>
 </form>
 <dialog ref="confirm" class="history-clear-dialog" aria-labelledby="history-clear-title"><h3 id="history-clear-title">Clear Focus History?</h3><p>This removes saved station selections and clears the current station display in every browser. Contacts in Wavelog/ADIF, observed contacts and pending delivery work are preserved. Radio operation continues.</p><div class="dialog-actions"><button class="btn console-button" @click="confirm?.close()" :disabled="busy">Cancel</button><button class="btn btn-danger" @click="clear" :disabled="busy">Clear Focus History</button></div></dialog>
</template>
