import { handler, loadApplication, mocks } from './support'

// The production handler currently has no authentication request. These boundary
// responses are ready for axios/fetch; they are not fabricated server observations.
it.each(['unauthorized', 'authorized', 'timeout'])(
  'TC-SC-004 / %s requires provider verification instead of a prefix-only decision', async outcome => {
    await loadApplication()
    const apiKey = outcome === 'authorized' ? 'sk-fixture-valid' : 'sk-test-invalid'
    const error = outcome === 'timeout'
      ? Object.assign(new Error('Verification request timed out'), { code: 'ECONNABORTED' })
      : Object.assign(new Error('Authentication failed'), { response: { status: 401 } })
    if (outcome === 'authorized') {
      mocks.axios.mockResolvedValue({ status: 200, data: { data: [] } })
      mocks.fetch.mockResolvedValue({ ok: true, status: 200, json: async () => ({ data: [] }) })
    } else {
      mocks.axios.mockRejectedValue(error)
      if (outcome === 'timeout') mocks.fetch.mockRejectedValue(error)
      else mocks.fetch.mockResolvedValue({ ok: false, status: 401, json: async () => ({ error: { message: 'Authentication failed' } }) })
    }
    const result = await handler('test-api-key')(apiKey)
    expect.soft(mocks.axios.mock.calls.length + mocks.fetch.mock.calls.length,
      'No verification request means provider validity was never checked').toBeGreaterThan(0)
    expect.soft(result.success).toBe(outcome === 'authorized')
    if (outcome !== 'authorized') {
      expect.soft(result.error).toEqual(expect.any(String))
      expect.soft(String(result.error)).not.toContain(apiKey)
      if (outcome === 'timeout') expect.soft(String(result.error)).toMatch(/timeout|timed out|network|超时|网络/i)
    }
  },
)
