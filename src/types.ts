export interface Rig { id: string; name: string; band: string; mode: string; color: string }
export interface Profile { name: string; location: string; country: string; grid: string; initials: string; color: string; bio: string }
export interface Qso { id: string; date: string; band: string; mode: string; sent: string; received: string; station: string; grid: string; confirmed: boolean }
export interface Entry { call: string; rigId: string; selectedAt: number; band: string | null; browsedAt?: number; recency: number }
export type Lookup<T> = { status: 'pending' } | { status: 'loaded'; data: T; complete?: boolean } | { status: 'empty' } | { status: 'error'; message: string }
export interface QsoHistory { records: Qso[]; complete: boolean }
export interface Providers { profile(call: string, delay?: number): Promise<Profile | null>; qsos(call: string, delay?: number): Promise<QsoHistory> }
