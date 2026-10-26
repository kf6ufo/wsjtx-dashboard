import type { DiagnosticRow } from './types'

export const activities = [
 ['signals', 'Decoded signals'], ['radio', 'Radio status'], ['contacts', 'Logged contacts'],
 ['connection', 'Connection checks'], ['other', 'Other messages'], ['errors', 'Invalid data'],
] as const
export const packetTypes = [[0, 'Heartbeat'], [1, 'Status'], [2, 'Decode'], [3, 'Clear'], [5, 'QSO Logged'], [6, 'Close'], [10, 'WSPR Decode'], [12, 'Logged ADIF']] as const
export function packetActivity(row: DiagnosticRow): string {
 if (row.error) return 'errors'
 if (row.kind === 2 || row.kind === 10) return 'signals'
 if (row.kind === 1) return 'radio'
 if (row.kind === 5 || row.kind === 12) return 'contacts'
 if (row.kind === 0 || row.kind === 6) return 'connection'
 return 'other'
}
export function packetLabel(row: DiagnosticRow): string {
 return ({ 0: 'Heartbeat · check-in', 1: 'Status · radio state', 2: 'Decode · received signal', 3: 'Clear · decode window', 5: 'QSO Logged · contact', 6: 'Close · instance stopped', 10: 'WSPR · received signal', 12: 'Logged ADIF · contact record' } as Record<number, string>)[row.kind ?? -1] ?? row.name
}
export function packetSummary(row: DiagnosticRow): string {
 if (row.error) return row.error
 const f = row.preview ?? {}
 if (row.kind === 0) return f.version ? `WSJT-X ${f.version} is checking in` : 'WSJT-X is checking in'
 if (row.kind === 1) {
  const frequency = typeof f.frequency === 'number' ? `${(f.frequency / 1e6).toFixed(6)} MHz` : ''
  const transmitting = f.transmitting === true ? 'Transmitting' : f.decoding === true ? 'Decoding' : 'Receiving'
  return [frequency, f.mode, f.dxCall ? `DX ${f.dxCall}` : 'No DX callsign', transmitting].filter(Boolean).join(' · ')
 }
 if (row.kind === 2) return [f.message || 'Decoded message', typeof f.snr === 'number' ? `${f.snr > 0 ? '+' : ''}${f.snr} dB` : '', typeof f.deltaFrequency === 'number' ? `${f.deltaFrequency} Hz audio` : ''].filter(Boolean).join(' · ')
 return ({ 3: 'Decode window cleared', 5: 'WSJT-X reported a completed QSO', 6: 'WSJT-X instance closed', 10: 'WSPR reception report', 12: 'Completed QSO record received; logging is configured separately' } as Record<number, string>)[row.kind ?? -1] ?? 'Additional protocol message · expand for technical details'
}
