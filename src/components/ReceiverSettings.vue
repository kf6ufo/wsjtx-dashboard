<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Dashboard } from '../focus'
import type { ReceiverConfig } from '../types'
const props = defineProps<{ dashboard: Dashboard }>()
const state = props.dashboard.state
const config = computed<ReceiverConfig>(() => ({ enabled: state.receiver.enabled ?? false, listen: state.receiver.listen ?? '0.0.0.0', port: state.receiver.port ?? 2238, group: state.receiver.group ?? '239.255.0.73', interface: state.receiver.interface ?? '127.0.0.1', retention: state.receiver.retention ?? 200 }))
const draft = ref<ReceiverConfig>({ ...config.value })
watch(() => JSON.stringify(config.value), () => { draft.value = { ...config.value } })
const saving = ref(false), message = ref('')
async function save() {
 saving.value = true; message.value = ''
 try {
  await props.dashboard.configureReceiver(draft.value)
  message.value = state.receiver.status === 'error' ? 'Configuration saved, but the receiver could not start. See the error below.' : 'Saved to config.toml and applied now. Network changes restart only this receiver; new Status baselines are established.'
 } catch (error) { message.value = error instanceof Error ? error.message : 'Save failed' }
 finally { saving.value = false }
}
async function restart() {
 saving.value = true
 try { await props.dashboard.restartReceiver(); message.value = 'Receiver restarted. The next Status per instance establishes a fresh baseline.' }
 catch (error) { message.value = error instanceof Error ? error.message : 'Restart failed' }
 finally { saving.value = false }
}
</script>
<template>
 <section class="receiver-settings" aria-labelledby="receiver-title"><span class="section-eyebrow">PRIMARY REPORTING INTERFACE</span><h3 id="receiver-title">WSJT-X receiver</h3><p>Receives selections, diagnostics and completed-QSO events. No radio commands or forwarding; logging is configured separately. Saved changes apply immediately; no server restart is required.</p>
 <form class="settings-form receiver-form" @submit.prevent="save"><label class="check-setting"><input type="checkbox" v-model="draft.enabled"> Enable UDP receiver</label><label>UDP listen address<input class="form-control" v-model.trim="draft.listen" required placeholder="0.0.0.0"><small>Usually 0.0.0.0 for multicast; use 127.0.0.1 for isolated local unicast tests.</small></label><label>UDP port<input class="form-control" type="number" min="1024" max="65535" v-model.number="draft.port" required></label><label>Multicast group<input class="form-control" v-model.trim="draft.group" placeholder="239.255.0.73"><small>Leave empty for unicast reception.</small></label><label>Receiving interface IPv4<input class="form-control" v-model.trim="draft.interface" placeholder="This computer’s LAN IPv4"><small>The receiving host’s address, not a radio’s address. Required for multicast.</small></label><label>Diagnostic retention (packets)<input class="form-control" type="number" min="50" max="500" v-model.number="draft.retention" required><small>50–500 packets in server memory. Changes apply without resetting baselines.</small></label><div class="receiver-actions"><button class="btn btn-success" :disabled="saving || state.connection !== 'connected'">{{ saving ? 'Applying…' : 'Save receiver settings' }}</button><button type="button" class="btn console-button" :disabled="saving || state.connection !== 'connected'" @click="restart">Restart receiver</button></div><p role="status">{{ message }}</p></form>
 <p class="connection-note" v-if="state.receiver.error" role="alert">{{ state.receiver.error }}</p><p>First Status per instance is a baseline. A later changed DX Call selects; ordinary decodes never select. Reselecting an unchanged callsign may be undetectable.</p>
 </section>
</template>
