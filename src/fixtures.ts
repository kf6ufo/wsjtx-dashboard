import type { Profile, Qso, Rig } from './types'
export const rigs: Rig[] = [
 { id: 'WSJT-X - IC7300', name: 'IC-7300', band: '20m', mode: 'FT8', color: '#70c9bd' },
 { id: 'WSJT-X - QRPLabsQDX', name: 'QRP Labs QDX', band: '10m', mode: 'FT8', color: '#b6a0ef' },
 { id: 'WSJT-X - Field', name: 'Field station', band: '15m', mode: 'FT8', color: '#e9b77a' },
]
// Entirely fictional operator identities and contact records; callsigns are illustrative.
export const profiles: Record<string, Profile> = {
 JA2HDE: { name: 'Haruto Mori', location: 'Nagoya, Aichi', country: 'Japan', grid: 'PM85', initials: 'HM', color: '#d6a770', bio: 'A small rooftop station, a love of weak signals, and a window to the world.' },
 VK3DEMO: { name: 'Alex Bennett', location: 'Melbourne, Victoria', country: 'Australia', grid: 'QF22', initials: 'AB', color: '#8db9ce', bio: 'Exploring the bands from southeastern Australia.' },
 DL1DEMO: { name: 'Lena Fischer', location: 'Freiburg', country: 'Germany', grid: 'JN48', initials: 'LF', color: '#b6a0ef', bio: 'Digital modes and weekend portable operating.' },
 PY2DEMO: { name: 'Rafael Silva', location: 'São Paulo', country: 'Brazil', grid: 'GG66', initials: 'RS', color: '#88b69a', bio: 'Chasing quiet signals from a busy city.' },
 ZS6DEMO: { name: 'Morgan Botha', location: 'Pretoria', country: 'South Africa', grid: 'KG44', initials: 'MB', color: '#d59893', bio: 'An illustrative operator profile for this demonstration.' },
 W7DEMO: { name: 'Sam Taylor', location: 'Portland, Oregon', country: 'United States', grid: 'CN85', initials: 'ST', color: '#91a9de', bio: 'Low power, long distances.' },
}
export const calls = Object.keys(profiles)
export function sampleQsos(call: string): Qso[] {
 if (call === 'VK3DEMO') return []
 return Array.from({ length: call === 'JA2HDE' ? 24 : 7 }, (_, i) => ({ id: `${call}-${i}`, date: new Date(Date.UTC(2026, 9, 10 - i * 8, 19, 42 - i)).toISOString(), band: ['20m','15m','10m','40m'][i % 4]!, mode: i % 5 === 0 ? 'FT4' : 'FT8', sent: `-${String(7 + i % 12).padStart(2, '0')}`, received: `-${String(4 + i % 17).padStart(2, '0')}`, station: i < 12 ? 'KF6UFO' : 'KF0TKE', grid: profiles[call]?.grid ?? '—', confirmed: i % 3 !== 0 }))
}
