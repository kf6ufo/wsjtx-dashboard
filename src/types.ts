export interface Rig { id: string; name: string; band: string; mode: string; color: string }
export interface Profile { name: string; location: string; country: string; grid: string; initials: string; color: string; bio: string }
export interface Qso { id: string; date: string; band: string; mode: string; sent: string; received: string; station: string; grid: string; confirmed: boolean }
export interface Entry { call: string; rigId: string; selectedAt: number; band: string | null; mode?: string; frequency?: number; browsedAt?: number; recency: number }
export type Lookup<T> = { status: 'pending' } | { status: 'loaded'; data: T; complete?: boolean } | { status: 'empty' } | { status: 'error'; message: string }
export interface QsoHistory { records: Qso[]; complete: boolean }
export interface Providers { profile(call: string, delay?: number): Promise<Profile | null>; qsos(call: string, delay?: number): Promise<QsoHistory> }
export interface LiveRig { id: string; name: string; band: string | null; mode: string; color: string; call: string; frequency: number; lastSeen: number; online: boolean }
export interface Preferences { title: string; appearance: 'dark' | 'light'; radioStrip: boolean }
export interface Snapshot { sample?: boolean; preferences?: Preferences; epoch: string; revision: number; call: string; source: 'radio' | 'browse'; history: Entry[]; rigs: LiveRig[]; counters: { decodes: number; malformed: number }; receiver: { status: 'disabled' | 'listening' | 'error'; error: string | null } }
