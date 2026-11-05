import type { Entry, LiveRig, PskReporterState, ReceptionSpot } from './types'
import { gridLocation } from './stationMap'

export function receptionCall(feed: PskReporterState | undefined, entry: Entry | undefined, rigs: LiveRig[]) {
 return (feed?.config.callsign || entry?.stationCall || rigs.find(r => r.id === entry?.rigId)?.stationCall || '').trim().toUpperCase()
}

/** Exact transmitted identity + focus band. Modes intentionally share a band. */
export function receptionSpots(feed: PskReporterState | undefined, sender: string, band: string | null | undefined, minutes: number, now: number) {
 if (!feed?.config.enabled || !sender || !band) return []
 const latest = new Map<string, ReceptionSpot>()
 for (const spot of feed.spots) {
  if (spot.sender !== sender || spot.band !== band || spot.heardAt <= now - minutes * 60000 || spot.heardAt > now + 30000 || !gridLocation(spot.grid)) continue
  if ((latest.get(spot.receiver)?.heardAt ?? 0) < spot.heardAt) latest.set(spot.receiver, spot)
 }
 return [...latest.values()]
}

export function receptionLabel(spot: ReceptionSpot, now: number) {
 const age = Math.max(0, Math.floor((now - spot.heardAt) / 60000))
 return `${spot.receiver} heard ${spot.sender} · ${spot.band} · ${age < 1 ? 'just now' : `${age} min ago`}${spot.snr === null ? '' : ` · ${spot.snr > 0 ? '+' : ''}${spot.snr} dB`} · ${spot.mode} · ${spot.grid} (approximate)`
}
