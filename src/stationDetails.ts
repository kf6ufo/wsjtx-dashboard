import type { EnrichmentResult } from './types'

export interface StationField { key: string; label: string; value: string; source?: string; href?: string }
export interface StationGroup { title: string; fields: StationField[] }

export function hasValue(value: unknown): boolean {
 if (value === null || value === undefined) return false
 if (typeof value === 'string') return !!value.trim()
 if (typeof value === 'number') return Number.isFinite(value)
 if (Array.isArray(value)) return value.some(hasValue)
 if (typeof value === 'object') return Object.values(value).some(hasValue)
 return true
}
export function fieldText(value: unknown): string {
 if (!hasValue(value)) return ''
 if (typeof value === 'boolean') return value ? 'Yes' : 'No'
 return typeof value === 'object' ? JSON.stringify(value) : String(value).trim()
}
export function webLink(value: unknown): string | undefined {
 if (typeof value !== 'string') return
 try {
  const url = new URL(value)
  if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) return url.href
 } catch { /* Unusable links remain readable text. */ }
}
export function emailLink(value: unknown): string | undefined {
 const text = fieldText(value)
 return /^[^\s@\r\n]+@[^\s@\r\n]+$/.test(text) ? `mailto:${encodeURIComponent(text)}` : undefined
}
export function operatorName(fields: Record<string, unknown>): string {
 return fieldText(fields.name_fmt) || [fields.fname, fields.name].map(fieldText).filter(Boolean).join(' ')
}

const definitions: [string, [string, string][]][] = [
 ['Contact & QSL', [['email', 'Email'], ['url', 'Website'], ['qslmgr', 'QSL manager'], ['lotw', 'LoTW'], ['eqsl', 'eQSL'], ['mqsl', 'Mail QSL'], ['lotw_user', 'LoTW member'], ['eqsl_user', 'eQSL member']]],
 ['License & identity', [['license_class', 'License class'], ['codes', 'License codes'], ['efdate', 'Effective date'], ['expdate', 'Expiry date'], ['aliases', 'Other callsigns'], ['p_call', 'Previous callsign'], ['nickname', 'Preferred name'], ['attn', 'Attention']]],
 ['Location', [['addr1', 'Address'], ['addr2', 'City / locality'], ['state', 'State / province'], ['zipcode', 'Postal code'], ['country', 'Country / entity'], ['county', 'County'], ['ccode', 'Country code'], ['fips', 'FIPS code'], ['timezone', 'Time zone'], ['gmtoffset', 'UTC offset'], ['latitude', 'Provider latitude'], ['longitude', 'Provider longitude'], ['geoloc', 'Coordinate source'], ['iota', 'IOTA']]],
]
const yesNo = new Set(['lotw', 'eqsl', 'mqsl', 'lotw_user', 'eqsl_user'])

export function stationGroups(data: EnrichmentResult): StationGroup[] {
 const values = data.fields ?? {}, sources = data.fieldSources ?? {}
 const groups: StationGroup[] = []
 const location: StationField[] = []
 const add = (key: string, label: string, raw: unknown, source?: string) => {
  if (hasValue(raw)) location.push({ key, label, value: fieldText(raw), source })
 }
 add('reportedGrid', 'Reported operating grid', data.reportedGrid, 'WSJT-X')
 add('callbookGrid', 'Callbook home grid', data.callbookGrid, sources.locator)
 add('stationGrid', 'Your station grid', data.stationGrid, data.stationGridSource)
 add('continent', 'Continent', values.continent, sources.continent)
 add('bandPlan', 'Frequency band', data.computed?.frequencyBand?.adif, 'pyhamtools band plan')
 if (data.computed?.longPathKm !== undefined) add('longPath', 'Long path', `${data.computed.longPathKm.toLocaleString()} km${data.computed.longPathHeading !== undefined ? ` · ${data.computed.longPathHeading}°` : ''}`, 'Calculated from grids')
 if (data.computed?.homeCall) add('homeCall', 'Home callsign', data.computed.homeCall, 'pyhamtools')
 for (const [title, keys] of definitions) {
  const fields: StationField[] = []
  for (const [key, label] of keys) {
   const raw = values[key]
   if (!hasValue(raw)) continue
   let value = fieldText(raw)
   if (yesNo.has(key)) {
    if (['0', 'false', 'no'].includes(value.toLowerCase())) value = 'No'
    else if (['1', 'true', 'yes'].includes(value.toLowerCase())) value = 'Yes'
   }
   const href = key === 'url' ? webLink(raw) : key === 'email' ? emailLink(raw) : undefined
   fields.push({ key, label, value, source: sources[key], href })
  }
  if (fields.length) groups.push({ title, fields })
 }
 if (location.length) {
  const address = groups.findIndex(group => group.title === 'Location')
  groups.splice(address < 0 ? groups.length : address, 0, { title: 'Operating location', fields: location })
 }
 return groups
}

export function stationKeyFacts(data: EnrichmentResult): StationField[] {
 const fields = data.fields ?? {}, computed = data.computed ?? {}
 const facts: StationField[] = []
 if (computed.distanceKm !== undefined) facts.push({ key: 'distance', label: 'Distance', value: `${computed.distanceKm.toLocaleString()} km` })
 if (computed.heading !== undefined) facts.push({ key: 'heading', label: 'Azimuth', value: `${computed.heading}°` })
 if (data.locationGrid) facts.push({ key: 'grid', label: data.reportedGrid ? 'Operating grid' : data.callbookGrid ? 'Home grid' : 'Estimated grid', value: data.locationGrid, source: data.locationSource })
 const qsl = stationGroups(data).flatMap(group => group.fields)
 for (const key of ['lotw', 'eqsl']) {
  const field = qsl.find(field => field.key === key)
  if (field) facts.push(field)
 }
 return facts
}

export function stationTableRows(data: EnrichmentResult): StationField[] {
 const fields = data.fields ?? {}, sources = data.fieldSources ?? {}
 const rows = stationGroups(data).flatMap(group => group.fields)
 const add = (key: string, label: string, raw: unknown, source?: string) => {
  if (hasValue(raw)) rows.push({ key, label, value: fieldText(raw), source })
 }
 add('dxcc', 'DXCC', [fields.adif, fields.country].filter(hasValue).map(fieldText).join(' · '), sources.adif || sources.country)
 add('cqz', 'CQ zone', fields.cqz, sources.cqz)
 add('ituz', 'ITU zone', fields.ituz, sources.ituz)
 for (const fact of stationKeyFacts(data)) if (fact.key !== 'grid' && !rows.some(row => row.key === fact.key)) rows.push(fact)
 const order = ['license_class', 'codes', 'efdate', 'expdate', 'aliases', 'p_call', 'dxcc', 'reportedGrid', 'callbookGrid', 'distance', 'heading', 'lotw', 'eqsl', 'mqsl', 'email', 'url', 'qslmgr', 'county', 'state', 'fips', 'timezone', 'gmtoffset', 'latitude', 'longitude']
 return rows.sort((a,b) => (order.indexOf(a.key) < 0 ? 100 : order.indexOf(a.key)) - (order.indexOf(b.key) < 0 ? 100 : order.indexOf(b.key)))
}
