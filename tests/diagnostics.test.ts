import { describe, expect, it } from 'vitest'
import { packetActivity, packetLabel, packetSummary } from '../src/diagnostics'
import type { DiagnosticRow } from '../src/types'

const row = (kind: number, preview = {}): DiagnosticRow => ({ id: 1, at: 0, source: '127.0.0.1:2238', instance: 'Radio A', kind, name: 'Unknown', schema: 3, size: 80, error: null, preview })
describe('operator-friendly diagnostics', () => {
 it('distinguishes routine check-ins, radio state, received signals and logged contacts', () => {
  expect([0,1,2,5,6,10,12,999].map(kind => packetActivity(row(kind)))).toEqual(['connection','radio','signals','contacts','connection','signals','contacts','other'])
  expect(packetActivity({ ...row(1), error: 'truncated packet' })).toBe('errors')
  expect(packetLabel(row(0))).toBe('Heartbeat · check-in')
  expect(packetSummary(row(12))).toContain('logging is configured separately')
 })
 it('shows reported frequency, DX selection, transmit state and decoded signal measurements', () => {
  expect(packetSummary(row(1, { frequency: 14074000, mode: 'FT8', dxCall: 'JA1ABC', transmitting: true }))).toBe('14.074000 MHz · FT8 · DX JA1ABC · Transmitting')
  expect(packetSummary(row(2, { message: 'CQ JA1ABC PM95', snr: -12, deltaFrequency: 1200 }))).toBe('CQ JA1ABC PM95 · -12 dB · 1200 Hz audio')
  expect(packetSummary({ ...row(1), error: 'truncated packet' })).toBe('truncated packet')
 })
})
