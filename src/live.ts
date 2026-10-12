import type { Dashboard } from './focus'
import type { Snapshot } from './types'

export function connectLive(dashboard: Dashboard) {
 let events: EventSource | undefined
 let connection = 0
 function disconnect() {
  ++connection
  events?.close()
  events = undefined
  dashboard.state.connection = 'disconnected'
 }
 function connect() {
  disconnect()
  if (!navigator.onLine) return
  dashboard.state.connection = 'connecting'
  const source = new EventSource('/api/events')
  events = source
  // Fetch complete state on every initial/re-established connection. SSE also
  // supplies full snapshots, so bounded queues can safely coalesce updates.
  source.onopen = () => {
   if (events !== source) return
   const token = ++connection
   dashboard.state.connection = 'connected'
   fetch('/api/snapshot', { cache: 'no-store' }).then(response => {
    if (!response.ok) throw new Error('Snapshot unavailable')
    return response.json() as Promise<Snapshot>
   }).then(snapshot => {
    if (events === source && connection === token) dashboard.applySnapshot(snapshot, false)
   }).catch(() => { /* The subscribed stream supplies its own complete snapshot. */ })
  }
  source.addEventListener('snapshot', event => {
   if (events !== source) return
   try { dashboard.applySnapshot(JSON.parse((event as MessageEvent).data) as Snapshot) }
   catch { dashboard.state.connection = 'disconnected' }
  })
  source.onerror = () => {
   if (events === source) { ++connection; dashboard.state.connection = 'disconnected' }
  }
 }
 window.addEventListener('offline', disconnect)
 window.addEventListener('online', connect)
 connect()
 return () => {
  window.removeEventListener('offline', disconnect)
  window.removeEventListener('online', connect)
  disconnect()
 }
}
