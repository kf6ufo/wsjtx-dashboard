import type { PskReporterState, ReceptionSpot } from './types'
import { gridLocation, type StationLocation } from './stationMap'

export interface QsoOutlook {
 score: number | null
 classification: 'Favorable' | 'Moderate' | 'Limited evidence' | 'Unknown'
 color: 'green' | 'yellow' | 'red' | 'gray'
 direct?: ReceptionSpot
 within200: number
 within500: number
 nearestKm: number | null
 latestAt: number | null
 nearbyMode: string | null
 explanation: string
}

/** Local, deterministic reception evidence; never a calibrated QSO probability. */
export function calculateQsoOutlook({ feed, sender, call, band, mode, location, minutes, now }: {
 feed?: PskReporterState; sender: string; call: string; band?: string | null; mode?: string
 location?: StationLocation; minutes: number; now: number
}): QsoOutlook {
 const result: QsoOutlook = { score: null, classification: 'Unknown', color: 'gray', within200: 0, within500: 0,
  nearestKm: null, latestAt: null, nearbyMode: null, explanation: 'No qualifying recent reception evidence. Missing reports do not mean this station cannot hear you.' }
 if (!feed?.config.enabled) return { ...result, explanation: 'PSKReporter is off. Enable the existing reception overlay to collect evidence.' }
 if (!sender || !band || !call || !Number.isFinite(now) || !Number.isFinite(minutes) || minutes <= 0) return result
 const window = Math.min(15, minutes) * 60000
 const latest = new Map<string, ReceptionSpot>()
 for (const spot of feed.spots) {
  if (spot.sender !== sender || spot.band !== band || !Number.isFinite(spot.heardAt) || now - spot.heardAt > window || spot.heardAt > now + 30000 || !gridLocation(spot.grid)) continue
  if (!latest.has(spot.receiver) || latest.get(spot.receiver)!.heardAt < spot.heardAt) latest.set(spot.receiver, spot)
 }
 // Direct evidence always takes priority, including a report in another mode.
 result.direct = latest.get(call)
 result.latestAt = result.direct?.heardAt ?? null
 if (!location || location.isEntityEstimate || !Number.isFinite(location.lat) || !Number.isFinite(location.lng) || Math.abs(location.lat) > 90 || Math.abs(location.lng) > 180) {
  return { ...result, explanation: 'A station grid or callbook location is needed for QSO Outlook. An entity estimate is not a station position.' }
 }
 const nearby = [...latest.values()].filter(spot => now - spot.heardAt <= 10 * 60000).map(spot => {
  const receiver = gridLocation(spot.grid)!
  const radians = Math.PI / 180
  const a = Math.sin((receiver.lat - location.lat) * radians / 2) ** 2
   + Math.cos(location.lat * radians) * Math.cos(receiver.lat * radians) * Math.sin((receiver.lng - location.lng) * radians / 2) ** 2
  return { spot, km: 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, a)))) }
 }).filter(receiver => receiver.km <= 500)
 const operatingMode = mode?.trim().toUpperCase()
 const matching = operatingMode ? nearby.filter(receiver => receiver.spot.mode.trim().toUpperCase() === operatingMode) : []
 // Prefer the operating mode when nearby evidence exists; otherwise use this band.
 const receivers = matching.length ? matching : nearby
 result.nearbyMode = matching.length ? operatingMode! : null
 result.within200 = receivers.filter(receiver => receiver.km <= 200).length
 result.within500 = receivers.length
 for (const receiver of receivers) {
  result.nearestKm = Math.min(result.nearestKm ?? Infinity, receiver.km)
  result.latestAt = Math.max(result.latestAt ?? -Infinity, receiver.spot.heardAt)
 }
 if (result.direct) {
  result.score = now - result.direct.heardAt <= 5 * 60000 ? 90 : 80
  result.explanation = `This station directly reported decoding your signal on this band${result.direct.mode ? ` in ${result.direct.mode}` : ''}. Confirmed reception does not guarantee a QSO.`
 } else if (result.within200) {
  result.score = result.within200 >= 3 ? 75 : 60
  result.explanation = `${result.within200 >= 3 ? 'Several nearby stations have' : 'One or two nearby stations have'} recently decoded your signal within 200 km. This station has not reported hearing you.`
 } else if (result.within500) {
  result.score = result.within500 >= 3 ? 55 : 35
  result.explanation = `Stations within 500 km have recently decoded your signal. This is broader regional evidence; this station has not reported hearing you.`
 }
 if (result.score !== null) {
  result.classification = result.score >= 70 ? 'Favorable' : result.score >= 40 ? 'Moderate' : 'Limited evidence'
  result.color = result.score >= 70 ? 'green' : result.score >= 40 ? 'yellow' : 'red'
 }
 return result
}
