import { files, handler, healthCalls, initializationCalls, loadApplication, mocks, observe, policy } from './support'

it('TC-SC-001 / missing-packaged-executable rejects without spawning or scanning', async () => {
  vi.stubEnv('NODE_ENV', 'production')
  mocks.existsSync.mockReturnValue(false)
  const service = await loadApplication()
  await expect(service.startVideoRAGService()).rejects.toThrow(/executable not found/i)
  expect(mocks.existsSync.mock.calls[0][0]).toContain('python_backend')
  expect(mocks.spawn).not.toHaveBeenCalled()
  expect(mocks.axios).not.toHaveBeenCalled()
  expect(vi.getTimerCount()).toBe(0)
})

it.each(['connection-refused', 'request-timeout'])(
  'TC-SC-002 / %s exits within the scan and elapsed-time budgets', async mode => {
    mocks.axios.mockImplementation(config => {
      const error = Object.assign(new Error(mode), { code: mode === 'connection-refused' ? 'ECONNREFUSED' : 'ECONNABORTED' })
      return mode === 'connection-refused' ? Promise.reject(error)
        : new Promise((_, reject) => setTimeout(() => reject(error), config.timeout))
    })
    const service = await loadApplication()
    const attempt = observe(service.startVideoRAGService())
    await vi.advanceTimersByTimeAsync(policy.startupBudgetMs)
    expect.soft(attempt.status, 'Startup must have rejected, not remain pending').toBe('rejected')
    expect.soft(healthCalls().length, 'At most 3 complete scans of 20 ports').toBeLessThanOrEqual(policy.maxScanRounds * policy.portsPerRound)
    expect.soft(vi.getTimerCount(), 'No retry or in-flight timeout survives the budget').toBe(0)
    expect(initializationCalls()).toHaveLength(0)
  },
)

it('TC-SC-002 / recovery starts a fresh attempt without old scans initializing again', async () => {
  const service = await loadApplication()
  mocks.axios.mockRejectedValue(Object.assign(new Error('offline'), { code: 'ECONNREFUSED' }))
  const first = observe(service.startVideoRAGService())
  await vi.advanceTimersByTimeAsync(policy.startupBudgetMs)
  expect.soft(first.status, 'The first attempt must finish before retry').toBe('rejected')
  expect.soft(vi.getTimerCount()).toBe(0)
  mocks.axios.mockImplementation(async config => ({ data: config.url.endsWith('/health') ? { status: 'ok' } : { success: true } }))
  const retry = observe(handler('videorag:start-service')())
  await vi.advanceTimersByTimeAsync(policy.startupBudgetMs)
  expect(retry.status).toBe('fulfilled')
  expect(retry.value).toMatchObject({ success: true })
  expect.soft(first.status, 'An expired attempt must not become successful later').toBe('rejected')
  expect.soft(initializationCalls(), 'Only the new attempt initializes').toHaveLength(1)
  expect(vi.getTimerCount()).toBe(0)
})

it('TC-SC-002 / healthy backend with invalid configuration is not successful application startup', async () => {
  files.set('bootstrap', '{broken')
  await loadApplication()
  const result = observe(handler('videorag:start-service')())
  await vi.advanceTimersByTimeAsync(10_000)
  expect(result.status).toBe('fulfilled')
  expect(result.value).toMatchObject({ success: false })
  expect(initializationCalls()).toHaveLength(0)
})
