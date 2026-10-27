export interface Rig { id: string; name: string; band: string; mode: string; color: string }
export interface Profile { name: string; location: string; country: string; grid: string; initials: string; color: string; bio: string }
export interface Qso { verifiedHistory?: boolean; observed?: boolean; observationStatus?: string; observedRig?: string; call?: string; stationId?: number; stationName?: string; confirmations?: { type: string; date: string }[]; details?: Record<string, string>; id: string; date: string; band: string; mode: string; sent: string; received: string; station: string; grid: string; confirmed: boolean | null }
export interface Entry { call: string; rigId: string; selectedAt: number; band: string | null; mode?: string; frequency?: number; dxGrid?: string; deGrid?: string; browsedAt?: number; recency: number }
export type Lookup<T> = { status: 'pending' } | { status: 'loaded'; data: T; complete?: boolean; message?: string } | { status: 'empty' } | { status: 'error'; message: string }
export interface QsoHistory { records: Qso[]; complete: boolean }
export interface Providers { profile(call: string, delay?: number): Promise<Profile | null>; qsos(call: string, delay?: number): Promise<QsoHistory> }
export interface LiveRig { id: string; name: string; band: string | null; mode: string; color: string; call: string; frequency: number; source?: string; lastSeen: number; online: boolean }
export interface Preferences { title: string; appearance: 'dark' | 'light'; radioStrip: boolean }
export interface ReceiverConfig { enabled: boolean; listen: string; port: number; group: string; interface: string; retention: number }
export interface ReceiverState extends Partial<ReceiverConfig> { status: 'disabled' | 'listening' | 'error'; error: string | null; lastPacketAt?: number }
export interface DiagnosticRow { preview?: Record<string, string | number | boolean>; id: number; at: number; source: string; instance: string | null; kind: number | null; name: string; schema: number | null; size: number; error: string | null }
export interface DiagnosticDetail extends DiagnosticRow { fields: Record<string, unknown>; rawBase64: string }
export interface DiagnosticPage { generation: number; latest: number; limit: number; rows: DiagnosticRow[] }
export interface Snapshot { observations?: ObservationState; historySettings?: HistorySettings; forwarding?: ForwardingState;  qso?: QsoServiceState; qsoHistory?: HistorySelectionState; wavelog?: WavelogState; photoUrls?: Record<string, string>; enrichment?: EnrichmentState; step?: number; storageError?: string | null; diagnostics?: { retained: number; limit: number; latest: number; generation: number }; sample?: boolean; preferences?: Preferences; epoch: string; revision: number; call: string; source: 'radio' | 'browse'; history: Entry[]; rigs: LiveRig[]; counters: { decodes: number; malformed: number; packets?: number; receiverErrors?: number; ignored?: number; capacity?: number }; receiver: ReceiverState }

export interface EnrichmentConfig {
 enabled: boolean; source: 'countryfile' | 'clublogxml' | 'clublogapi' | 'qrz'; filename: string;
 station_grid: string; refresh_hours: number; cache_minutes: number; cache_limit: number;
 qrz_enabled: boolean; qrz_version: string; field_priority: 'qrz_first' | 'source_first'; allow_country_estimate: boolean;
 clublog_key_configured?: boolean; qrz_username_configured?: boolean; qrz_password_configured?: boolean;
}
export interface ProviderResult { status: string; fields: Record<string, unknown>; message?: string; subscription?: string; updatedAt?: number; cached?: boolean; dataStatus?: string }
export interface EnrichmentResult { message?: string; status: string; call: string; fields?: Record<string, unknown>; fieldSources?: Record<string, string>; providers?: Record<string, ProviderResult>; computed?: { distanceKm?: number; heading?: number; longPathKm?: number; longPathHeading?: number; homeCall?: string; frequencyBand?: Record<string, unknown> }; reportedGrid?: string; callbookGrid?: string; locationGrid?: string; locationSource?: string; stationGrid?: string; stationGridSource?: string; updatedAt?: number }
export interface EnrichmentState { config: EnrichmentConfig; result: EnrichmentResult; health: Record<string, { status: string; message?: string; updatedAt?: number }> }

export interface WavelogConfig { enabled: boolean; url: string; token_configured?: boolean; scope_mode: 'all' | 'stations' | 'logbook'; station_ids: number[]; logbook_id: number; cache_minutes: number; cache_limit: number; page_size: number; max_pages: number; max_records: number; timeout_seconds: number }
export interface WavelogStation { id: number; name: string; callsign: string; grid: string; active: boolean }
export interface WavelogLogbook { id: number; name: string; stationIds: number[]; active: boolean }
export interface WavelogConnection { status: string; message?: string; api?: string; owner?: string; expiresAt?: string; scopes: string[]; stations: WavelogStation[]; logbooks: WavelogLogbook[]; notices?: string[]; checkedAt?: number }
export interface WavelogResult { status: string; call: string; complete: boolean; lookupId?: string; recordCount?: number; total?: number | null; scope?: string; cached?: boolean; updatedAt?: number; message?: string; confirmationStatus?: string }
export interface WavelogState { config: WavelogConfig; connection: WavelogConnection; result: WavelogResult }

export interface QsoConfig { history_source: 'auto' | 'wavelog' | 'adif'; adif_path: string; adif_complete: boolean; logging_enabled: boolean; log_to_wavelog: boolean; recovery_seconds: number; rigs: { id: string; station_callsign: string; operator: string; wavelog_station_id: number; tx_power: string }[] }
export interface HistorySelectionState { provider: string; label: string; notice?: string; result: WavelogResult }
export interface StationAssociation { rigId: string; stationCall: string; status: string; stationId: number; location?: string; message: string }
export interface QsoServiceState { associations?: StationAssociation[]; config: QsoConfig; enabled: boolean; warning: string; error: string; queue: { jobs: Record<string, number>; destinations: { destination: string; status: string; count: number }[]; recent: { contact?: Record<string,string>; id: string; rig: string; status: string; message: string; created: number; deliveries: { destination: string; status: string; attempts: number; message: string; remoteId?: string }[] }[] } }

export interface HistorySettings { limit: 50 | 100 | 200 | 500; retention_days: 0 | 7 | 30 }
export interface HistorySummary { count?: number; complete?: boolean; source?: string; bands?: string[]; modes?: string[]; pendingObserved?: number }
export interface ObservationState { pending: number; capacity: number; error: string; summaries: Record<string, HistorySummary>; result: (WavelogResult & { pendingObserved?: number; historicalCount?: number; source?: string }) | null }
export interface ForwardDestination { id: string; name: string; enabled: boolean; host: string; port: number; rigs: string[]; packets: number[]; format: 'raw' | 'enriched-adif' }
export interface ForwardingState { config: { destinations: ForwardDestination[] }; error: string; loopDrops: number; completedQueued: number; destinations: { id: string; enabled: boolean; dispatched: number; filtered: number; dropped: number; lastSentAt: number | null; lastError: string; status: string; queued: number }[] }
