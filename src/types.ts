export interface Rig { id: string; name: string; band: string; mode: string; color: string }
export interface Profile { name: string; location: string; country: string; grid: string; initials: string; color: string; bio: string }
export interface Qso { id: string; date: string; band: string; mode: string; sent: string; received: string; station: string; grid: string; confirmed: boolean }
export interface Entry { call: string; rigId: string; selectedAt: number; band: string | null; mode?: string; frequency?: number; dxGrid?: string; deGrid?: string; browsedAt?: number; recency: number }
export type Lookup<T> = { status: 'pending' } | { status: 'loaded'; data: T; complete?: boolean } | { status: 'empty' } | { status: 'error'; message: string }
export interface QsoHistory { records: Qso[]; complete: boolean }
export interface Providers { profile(call: string, delay?: number): Promise<Profile | null>; qsos(call: string, delay?: number): Promise<QsoHistory> }
export interface LiveRig { id: string; name: string; band: string | null; mode: string; color: string; call: string; frequency: number; source?: string; lastSeen: number; online: boolean }
export interface Preferences { title: string; appearance: 'dark' | 'light'; radioStrip: boolean }
export interface ReceiverConfig { enabled: boolean; listen: string; port: number; group: string; interface: string; retention: number }
export interface ReceiverState extends Partial<ReceiverConfig> { status: 'disabled' | 'listening' | 'error'; error: string | null; lastPacketAt?: number }
export interface DiagnosticRow { id: number; at: number; source: string; instance: string | null; kind: number | null; name: string; schema: number | null; size: number; error: string | null }
export interface DiagnosticDetail extends DiagnosticRow { fields: Record<string, unknown>; rawBase64: string }
export interface DiagnosticPage { generation: number; latest: number; limit: number; rows: DiagnosticRow[] }
export interface Snapshot { photoUrls?: Record<string, string>; enrichment?: EnrichmentState; step?: number; storageError?: string | null; diagnostics?: { retained: number; limit: number; latest: number; generation: number }; sample?: boolean; preferences?: Preferences; epoch: string; revision: number; call: string; source: 'radio' | 'browse'; history: Entry[]; rigs: LiveRig[]; counters: { decodes: number; malformed: number; packets?: number; receiverErrors?: number; ignored?: number; capacity?: number }; receiver: ReceiverState }

export interface EnrichmentConfig {
 enabled: boolean; source: 'countryfile' | 'clublogxml' | 'clublogapi' | 'qrz'; filename: string;
 station_grid: string; refresh_hours: number; cache_minutes: number; cache_limit: number;
 qrz_enabled: boolean; qrz_version: string; field_priority: 'qrz_first' | 'source_first'; allow_country_estimate: boolean;
 clublog_key_configured?: boolean; qrz_username_configured?: boolean; qrz_password_configured?: boolean;
}
export interface ProviderResult { status: string; fields: Record<string, unknown>; message?: string; subscription?: string; updatedAt?: number; cached?: boolean; dataStatus?: string }
export interface EnrichmentResult { message?: string; status: string; call: string; fields?: Record<string, unknown>; fieldSources?: Record<string, string>; providers?: Record<string, ProviderResult>; computed?: { distanceKm?: number; heading?: number; longPathKm?: number; longPathHeading?: number; homeCall?: string; frequencyBand?: Record<string, unknown> }; reportedGrid?: string; callbookGrid?: string; locationGrid?: string; locationSource?: string; stationGrid?: string; stationGridSource?: string; updatedAt?: number }
export interface EnrichmentState { config: EnrichmentConfig; result: EnrichmentResult; health: Record<string, { status: string; message?: string; updatedAt?: number }> }
