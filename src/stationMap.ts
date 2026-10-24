import type { EnrichmentState, Entry } from './types'

export interface StationLocation {
 lat: number; lng: number; label: string; detail: string; zoom: number
 bounds?: [[number, number], [number, number]]
}

/** Maidenhead locations describe a cell, never an exact antenna position. */
export function gridLocation(raw: unknown): StationLocation | undefined {
 if (typeof raw !== 'string') return
 const grid = raw.trim().toUpperCase()
 if (!/^[A-R]{2}[0-9]{2}(?:[A-X]{2}(?:[0-9]{2})?)?$/.test(grid)) return
 let lng = -180 + (grid.charCodeAt(0) - 65) * 20 + Number(grid[2]) * 2
 let lat = -90 + (grid.charCodeAt(1) - 65) * 10 + Number(grid[3])
 let width = 2, height = 1
 if (grid.length >= 6) {
  width /= 24; height /= 24
  lng += (grid.charCodeAt(4) - 65) * width
  lat += (grid.charCodeAt(5) - 65) * height
 }
 if (grid.length === 8) {
  width /= 10; height /= 10
  lng += Number(grid[6]) * width; lat += Number(grid[7]) * height
 }
 return { lat: lat + height / 2, lng: lng + width / 2, bounds: [[lat, lng], [lat + height, lng + width]], label: grid, detail: 'Approximate grid center', zoom: grid.length === 4 ? 6 : 9 }
}

function coordinate(raw: unknown, limit: number): number | undefined {
 if (!['string', 'number'].includes(typeof raw) || String(raw).trim() === '') return
 const value = Number(raw)
 return Number.isFinite(value) && Math.abs(value) <= limit ? value : undefined
}

/** Prefer the selected contact's operating grid over a potentially different home address. */
export function stationMapLocation(call: string, entry?: Entry, enrichment?: EnrichmentState): StationLocation | undefined {
 const data = enrichment?.result.call === call ? enrichment.result : undefined
 const reported = gridLocation(entry?.call === call ? entry.dxGrid : undefined) ?? gridLocation(data?.reportedGrid)
 if (reported) return { ...reported, detail: 'WSJT-X operating grid · approximate center' }
 if (!data) return
 const lat = coordinate(data.fields?.latitude, 90), lng = coordinate(data.fields?.longitude, 180)
 if (lat !== undefined && lng !== undefined && data.fieldSources?.latitude === 'QRZ XML' && data.fieldSources?.longitude === 'QRZ XML') {
  return { lat, lng, label: data.callbookGrid || 'Callbook location', detail: 'QRZ callbook coordinates · home location', zoom: 9 }
 }
 const home = gridLocation(data.callbookGrid)
 if (home) return { ...home, detail: 'Callbook home grid · approximate center' }
 const estimate = enrichment?.config.allow_country_estimate && gridLocation(data.locationGrid)
 if (estimate && data.locationSource?.startsWith('Approximate provider coordinates')) return { ...estimate, detail: 'Approximate entity location · not a station position', zoom: 3 }
}
