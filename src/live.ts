import type { Dashboard } from './focus'
import type { Snapshot } from './types'

const CHECK_AFTER_MS = 30_000
const REQUEST_TIMEOUT_MS = 8_000

export function connectLive(dashboard: Dashboard) {
 let events: EventSource | undefined
 let connection = 0
 let disposed = false
 let lastCheckAt = Date.now()
 let lastStreamAt = Date.now()
 let latestSnapshot: Pick<Snapshot, 'epoch' | 'revision'> | undefined
 let streamSnapshot: Pick<Snapshot, 'epoch' | 'revision'> | undefined
 let probe: { abort: () => void } | undefined

 function applySnapshot(snapshot: Snapshot, allowEpochChange = true) {
  if (latestSnapshot && snapshot.epoch === latestSnapshot.epoch && snapshot.revision < latestSnapshot.revision) return false
  dashboard.applySnapshot(snapshot, allowEpochChange)
  latestSnapshot = { epoch: snapshot.epoch, revision: snapshot.revision }
  dashboard.state.lastServerUpdateAt = Date.now()
  return true
 }

 function disconnect() {
  ++connection
  probe?.abort()
  probe = undefined
  events?.close()
  events = undefined
  dashboard.state.connection = 'disconnected'
 }

 async function validate() {
  if (disposed || !navigator.onLine || probe) return
  const token = connection
  const epoch = latestSnapshot?.epoch
  const controller = new AbortController()
  let rejectDeadline!: (error: Error) => void
  const deadline = new Promise<never>((_, reject) => { rejectDeadline = reject })
  let timeout: number | undefined
  const request = { abort() {
   controller.abort()
   window.clearTimeout(timeout)
   rejectDeadline(new Error('Snapshot request stopped'))
  } }
  probe = request
  lastCheckAt = Date.now()
  timeout = window.setTimeout(request.abort, REQUEST_TIMEOUT_MS)
  try {
   const snapshot = await Promise.race([
    fetch('/api/snapshot', { cache: 'no-store', signal: controller.signal }).then(async response => {
     if (!response.ok) throw new Error('Snapshot unavailable')
     return await response.json() as Snapshot
    }), deadline,
   ])
   if (disposed || token !== connection || controller.signal.aborted) return
   // An old HTTP response cannot undo a service restart already seen by SSE.
   if (epoch !== latestSnapshot?.epoch && snapshot.epoch !== latestSnapshot?.epoch) return
   const changedEpoch = !!latestSnapshot && snapshot.epoch !== latestSnapshot.epoch
   const observed = streamSnapshot ?? latestSnapshot
   const missed = !!observed && (snapshot.epoch !== observed.epoch || snapshot.revision > observed.revision)
   if (!applySnapshot(snapshot, changedEpoch || !latestSnapshot)) return
   lastCheckAt = Date.now()
   dashboard.state.connection = 'connected'
   // Equal revisions are healthy on a quiet station. Only proven missed state,
   // a service restart or a closed source warrants replacing the stream.
   if (changedEpoch || events?.readyState === EventSource.CLOSED ||
       (missed && Date.now() - lastStreamAt >= CHECK_AFTER_MS)) connect()
  } catch {
   if (!disposed && token === connection && Date.now() - lastStreamAt >= CHECK_AFTER_MS) {
    dashboard.state.connection = 'disconnected'
   }
  } finally {
   window.clearTimeout(timeout)
   if (probe === request) probe = undefined
  }
 }

 function connect() {
  disconnect()
  if (disposed || !navigator.onLine) return
  lastStreamAt = Date.now()
  streamSnapshot = undefined
  dashboard.state.connection = 'connecting'
  const source = new EventSource('/api/events')
  events = source
  source.onopen = () => {
   if (events !== source) return
   dashboard.state.connection = 'connected'
   void validate()
  }
  source.addEventListener('snapshot', event => {
   if (events !== source) return
   try {
    const snapshot = JSON.parse((event as MessageEvent).data) as Snapshot
    if (!applySnapshot(snapshot)) return
    if (!streamSnapshot || snapshot.epoch !== streamSnapshot.epoch || snapshot.revision > streamSnapshot.revision) {
     streamSnapshot = { epoch: snapshot.epoch, revision: snapshot.revision }
    }
    lastStreamAt = lastCheckAt = Date.now()
    dashboard.state.connection = 'connected'
   }
   catch { dashboard.state.connection = 'disconnected' }
  })
  source.onerror = () => {
   if (events === source) dashboard.state.connection = 'disconnected'
  }
 }

 function resume() {
  if (disposed || !navigator.onLine) return
  if (!events) connect()
  void validate()
 }
 function visible() { if (document.visibilityState === 'visible') resume() }
 const timer = window.setInterval(() => {
  if (Date.now() - lastCheckAt >= CHECK_AFTER_MS) void validate()
 }, 5_000)
 window.addEventListener('offline', disconnect)
 window.addEventListener('online', resume)
 window.addEventListener('focus', resume)
 window.addEventListener('pageshow', resume)
 document.addEventListener('visibilitychange', visible)
 connect()
 return () => {
  disposed = true
  window.clearInterval(timer)
  window.removeEventListener('offline', disconnect)
  window.removeEventListener('online', resume)
  window.removeEventListener('focus', resume)
  window.removeEventListener('pageshow', resume)
  document.removeEventListener('visibilitychange', visible)
  disconnect()
 }
}
