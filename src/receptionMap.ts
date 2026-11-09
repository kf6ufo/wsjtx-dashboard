import type { LocalReceptionSpot, LocalReceptionState, ReceptionSpot } from './types'
import { gridLocation, type StationLocation } from './stationMap'
import { receptionLabel } from './pskreporter'

export type ReceptionView = 'sent' | 'recv' | 'both'
export interface MapReception {
 call: string; direction: ReceptionView; location: StationLocation
 sent?: ReceptionSpot; recv?: LocalReceptionSpot
}

export function localReceptionSpots(data: LocalReceptionState | undefined, sender: string, rigId: string | undefined, band: string | null | undefined, minutes: number, now: number) {
 if (!sender || !rigId || !band) return []
 const latest = new Map<string, LocalReceptionSpot>()
 for (const spot of data?.spots ?? []) {
  if (spot.rigId !== rigId || spot.stationCall !== sender || spot.band !== band || !Number.isFinite(spot.heardAt) || spot.heardAt <= now - Math.min(60, minutes) * 60000 || spot.heardAt > now + 30000 || !gridLocation(spot.grid)) continue
  if (!latest.has(spot.call) || latest.get(spot.call)!.heardAt < spot.heardAt) latest.set(spot.call, spot)
 }
 return [...latest.values()]
}

/** A mutual receiver is the exact same complete callsign, never a shared grid. */
export function mapReceptions(sent: ReceptionSpot[], recv: LocalReceptionSpot[], view: ReceptionView): MapReception[] {
 const stations = new Map<string, MapReception>()
 for (const spot of sent) {
  const location = gridLocation(spot.grid)
  if (location) stations.set(spot.receiver, { call: spot.receiver, direction: 'sent', sent: spot, location })
 }
 for (const spot of recv) {
  const location = gridLocation(spot.grid)
  if (!location) continue
  const existing = stations.get(spot.call)
  // Both inputs have already been scoped to one exact operating identity/band.
  const mutual = existing?.sent?.sender === spot.stationCall && existing.sent.band === spot.band
  stations.set(spot.call, { call: spot.call, direction: mutual ? 'both' : 'recv', sent: mutual ? existing!.sent : undefined, recv: spot, location })
 }
 return [...stations.values()].filter(station => view === 'both' || (view === 'sent' ? station.sent : station.recv))
}

export function localReceptionLabel(spot: LocalReceptionSpot, now: number) {
 const age = Math.max(0, Math.floor((now - spot.heardAt) / 60000))
 return `${spot.stationCall} heard ${spot.call} · ${spot.band} · ${age < 1 ? 'just now' : `${age} min ago`}${spot.snr === null ? '' : ` · ${spot.snr > 0 ? '+' : ''}${spot.snr} dB`} · ${spot.mode} · ${spot.grid} (${spot.gridSource || 'reported grid'}; approximate) · ${new Date(spot.heardAt).toISOString()} · ${spot.rigId}`
}

export function mapReceptionLabel(station: MapReception, now: number) {
 return [station.direction === 'both' ? 'Mutual reception' : '', station.sent ? `${receptionLabel(station.sent, now)} · ${new Date(station.sent.heardAt).toISOString()}` : '', station.recv ? localReceptionLabel(station.recv, now) : ''].filter(Boolean).join('\n')
}

export function receptionSummary(sent?: ReceptionSpot, recv?: LocalReceptionSpot) {
 return sent && recv ? 'Mutual reception' : sent ? 'Heard me' : recv ? 'I heard' : 'No recent evidence'
}
