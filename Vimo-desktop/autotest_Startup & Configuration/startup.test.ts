import { healthCalls, loadApplication, mocks, observe } from './support'

it('TC-SC-001 / missing backend executable prevents startup', async () => {
  vi.stubEnv('NODE_ENV', 'production')
  mocks.existsSync.mockReturnValue(false)
  const service = await loadApplication()
  await expect(service.startVideoRAGService()).rejects.toThrow()
  expect(mocks.spawn).not.toHaveBeenCalled()
})

it('TC-SC-002 / temporarily unavailable backend reconnects after service recovery', async () => {
  const service = await loadApplication()
  mocks.axios.mockRejectedValue(Object.assign(new Error('offline'), { code: 'ECONNREFUSED' }))
  const attempt = observe(service.startVideoRAGService())
  // Advance the existing scheduler; this is not a product latency requirement.
  await vi.advanceTimersByTimeAsync(11_000)
  expect(healthCalls().length).toBeGreaterThan(0)
  expect(attempt.status).not.toBe('fulfilled')
  mocks.axios.mockImplementation(async config => ({
    data: config.url.endsWith('/health') ? { status: 'ok' } : { success: true },
  }))
  // Bounded virtual-time guard, not a prolonged-outage retry exhaustion test.
  for (let step = 0; step < 20 && attempt.status === 'pending'; step++) {
    await vi.advanceTimersByTimeAsync(10_000)
  }
  expect(attempt.status).toBe('fulfilled')
  expect(attempt.value).toBe(true)
})
