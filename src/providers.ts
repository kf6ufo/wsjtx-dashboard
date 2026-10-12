import { profiles, sampleQsos } from './fixtures'
import type { Providers } from './types'
const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
export const mockProviders: Providers = {
 async profile(call, delay = 450) { await wait(delay); if (call === 'ZS6DEMO') return null; return profiles[call] ?? null },
 async qsos(call, delay = 850) { await wait(delay); if (call === 'PY2DEMO') throw new Error('Sample logbook lookup unavailable. Retry or select another station.'); if (!profiles[call]) throw new Error('No sample QSO fixture for this live callsign. Real logbook lookup is not connected.'); return { records: sampleQsos(call), complete: true } },
}
