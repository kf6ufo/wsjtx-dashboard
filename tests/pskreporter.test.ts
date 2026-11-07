import { describe, expect, it } from 'vitest'
import { receptionCall, receptionLabel, receptionSpots } from '../src/pskreporter'
import type { Entry, PskReporterState, ReceptionSpot } from '../src/types'
const now = Date.UTC(2026,10,5,12)
const spot: ReceptionSpot = { sender:'N0CALL', receiver:'K1FOCUS', band:'20m', grid:'FN31', heardAt:now-60000, frequency:14074000, mode:'FT8', snr:-12 }
const feed = (spots: ReceptionSpot[]): PskReporterState => ({ config:{enabled:true,callsign:'',window_minutes:15}, status:'connected', error:'', callsigns:['N0CALL'], spots, connectedAt:now-120000, evicted:0 })

describe('recent reception overlay', () => {
 it('keeps base and suffixed receivers distinct and preserves the full label', () => {
  const receivers = [spot, {...spot,receiver:'K1FOCUS-888'}, {...spot,receiver:'K1FOCUS-1'}]
  const newer = {...receivers[1]!,heardAt:now-30000}
  expect(receptionSpots(feed([...receivers,newer]),'N0CALL','20m',15,now)).toEqual([spot,newer,receivers[2]])
  expect(receptionLabel(newer,now)).toContain('K1FOCUS-888 heard N0CALL')
 })
 it('includes ten-character receiver grids without truncating their precision', () => {
  const extended = {...spot, grid:'EN34qb49ta', band:'12m', frequency:24915791}
  expect(receptionSpots(feed([extended]),'N0CALL','12m',15,now)).toEqual([extended])
  expect(receptionLabel(extended,now)).toContain('EN34qb49ta (approximate)')
 })
 it('shows only the transmitting identity and focus band, deduplicates latest receiver across modes', () => {
  const data = feed([spot, {...spot,mode:'FT4',heardAt:now-30000}, {...spot,sender:'K2OTHER'}, {...spot,band:'15m'}, {...spot,receiver:'K3OLD',heardAt:now-20*60000}, {...spot,receiver:'K4BAD',grid:'ZZ99'}, {...spot,receiver:'K5FUTURE',heardAt:now+60000}])
  expect(receptionSpots(data,'N0CALL','20m',15,now)).toEqual([{...spot,mode:'FT4',heardAt:now-30000}])
  expect(receptionSpots(data,'N0CALL',null,15,now)).toEqual([])
  expect(receptionSpots(data,'','20m',15,now)).toEqual([])
  expect(receptionSpots({...data,config:{...data.config,enabled:false}},'N0CALL','20m',15,now)).toEqual([])
 })
 it('expires by report time and allows immediate expansion to an hour during an outage', () => {
  const data = feed([{...spot,heardAt:now-30*60000}]); data.status='reconnecting'
  expect(receptionSpots(data,'N0CALL','20m',15,now)).toHaveLength(0)
  expect(receptionSpots(data,'N0CALL','20m',60,now)).toHaveLength(1)
  expect(receptionSpots(data,'N0CALL','20m',60,now+30*60000)).toHaveLength(0)
 })
 it('prefers captured selection identity and explicit override, with same-rig legacy fallback', () => {
  const data = feed([]), entry = {rigId:'A',stationCall:'N0CALL/P'} as Entry
  expect(receptionCall(data,entry,[])).toBe('N0CALL/P')
  expect(receptionCall({...data,config:{...data.config,callsign:'K2OVERRIDE'}},entry,[])).toBe('K2OVERRIDE')
  expect(receptionCall(data,{rigId:'A'} as Entry,[{id:'B',stationCall:'K3WRONG'} as any,{id:'A',stationCall:'N0CALL'} as any])).toBe('N0CALL')
  expect(receptionLabel(spot,now)).toContain('K1FOCUS heard N0CALL · 20m · 1 min ago · -12 dB')
 })
})
