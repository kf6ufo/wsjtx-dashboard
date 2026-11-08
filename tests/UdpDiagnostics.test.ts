import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import UdpDiagnostics from '../src/components/UdpDiagnostics.vue'
import { createDashboard } from '../src/focus'
import type { DiagnosticPage } from '../src/types'

function page(id: number): DiagnosticPage {
 return { generation: 0, latest: id, limit: 200, rows: [{ id, at: 1000, source: `127.0.0.1:${id}`, instance: 'Test radio', kind: 0, name: 'Heartbeat', schema: 3, size: 80, error: null, preview: {} }] }
}
function response(id: number) { return new Response(JSON.stringify(page(id))) }
function deferred() {
 let resolve!: (value: Response) => void, reject!: (reason: Error) => void
 const promise = new Promise<Response>((accept, fail) => { resolve = accept; reject = fail })
 return { promise, resolve, reject }
}

describe('UDP diagnostics polling recovery', () => {
 let wrapper: VueWrapper | undefined
 beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] })
 })
 afterEach(() => {
  wrapper?.unmount(); wrapper = undefined
  vi.useRealTimers(); vi.unstubAllGlobals()
 })
 function show() { return wrapper = mount(UdpDiagnostics, { props: { dashboard: createDashboard(undefined, true) } }) }

 it('times out a stalled request, retries, and ignores its late response without interrupting the next poll', async () => {
  const first = deferred(), second = deferred(), third = deferred()
  const fetcher = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise).mockReturnValueOnce(third.promise)
  vi.stubGlobal('fetch', fetcher)
  const view = show()
  const signal = fetcher.mock.calls[0]![1].signal as AbortSignal
  await vi.advanceTimersByTimeAsync(9000)
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(signal.aborted).toBe(false)
  await vi.advanceTimersByTimeAsync(2000)
  expect(signal.aborted).toBe(true)
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(view.text()).toContain('Diagnostics request timed out')
  // A late result must not release the newer request's ownership or replace rows.
  first.resolve(response(1)); await flushPromises()
  await vi.advanceTimersByTimeAsync(1000)
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(view.find('[aria-label="Inspect packet 1"]').exists()).toBe(false)
  second.resolve(response(2)); await flushPromises()
  expect(view.find('[aria-label="Inspect packet 2"]').exists()).toBe(true)
  expect(view.text()).not.toContain('Diagnostics request timed out')
  await vi.advanceTimersByTimeAsync(1000)
  expect(fetcher).toHaveBeenCalledTimes(3)
 })

 it('aborts when inactive and resumes immediately while ignoring an older error', async () => {
  const first = deferred(), second = deferred()
  const fetcher = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
  vi.stubGlobal('fetch', fetcher)
  const view = show()
  const signal = fetcher.mock.calls[0]![1].signal as AbortSignal
  await view.setProps({ active: false })
  expect(signal.aborted).toBe(true)
  await vi.advanceTimersByTimeAsync(15000)
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(view.text()).not.toContain('Diagnostics request timed out')
  await view.setProps({ active: true })
  expect(fetcher).toHaveBeenCalledTimes(2)
  second.resolve(response(2)); await flushPromises()
  first.reject(new Error('Expired request failed late')); await flushPromises()
  expect(view.find('[aria-label="Inspect packet 2"]').exists()).toBe(true)
  expect(view.text()).not.toContain('Expired request failed late')
 })

 it('cancels a pending request while paused and polls again on resume', async () => {
  const first = deferred(), second = deferred()
  const fetcher = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
  vi.stubGlobal('fetch', fetcher)
  const view = show()
  const signal = fetcher.mock.calls[0]![1].signal as AbortSignal
  await view.findAll('button').find(button => button.text() === 'Pause display')!.trigger('click')
  expect(signal.aborted).toBe(true)
  await vi.advanceTimersByTimeAsync(15000)
  expect(fetcher).toHaveBeenCalledTimes(1)
  await view.findAll('button').find(button => button.text() === 'Resume display')!.trigger('click')
  expect(fetcher).toHaveBeenCalledTimes(2)
  second.resolve(response(2)); await flushPromises()
  expect(view.find('[aria-label="Inspect packet 2"]').exists()).toBe(true)
 })

 it('recovers on the next poll after an HTTP failure', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce(new Response('Unavailable', { status: 503 })).mockResolvedValueOnce(response(2))
  vi.stubGlobal('fetch', fetcher)
  const view = show(); await flushPromises()
  expect(view.text()).toContain('Diagnostics unavailable')
  await vi.advanceTimersByTimeAsync(1000); await flushPromises()
  expect(view.find('[aria-label="Inspect packet 2"]').exists()).toBe(true)
  expect(view.text()).not.toContain('Diagnostics unavailable')
 })

 it('aborts on unmount and removes polling and request deadlines', async () => {
  const first = deferred(), fetcher = vi.fn().mockReturnValue(first.promise)
  vi.stubGlobal('fetch', fetcher)
  show()
  const signal = fetcher.mock.calls[0]![1].signal as AbortSignal
  wrapper!.unmount(); wrapper = undefined
  expect(signal.aborted).toBe(true)
  expect(vi.getTimerCount()).toBe(0)
  first.reject(new Error('Aborted request settled after unmount')); await flushPromises()
  await vi.advanceTimersByTimeAsync(20000)
  expect(fetcher).toHaveBeenCalledTimes(1)
 })
})
