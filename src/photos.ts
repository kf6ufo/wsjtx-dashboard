export function photoUrl(value: unknown): string {
 if (typeof value !== 'string' || value.length > 4096) return ''
 try {
  const url = new URL(value)
  return url.protocol === 'https:' && url.hostname && !url.username && !url.password ? url.href : ''
 } catch { return '' }
}
