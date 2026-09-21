import { handler, loadApplication, mocks } from './support'

it('TC-SC-004 / invalid key with sk prefix must not be accepted', async () => {
  await loadApplication()
  // Simulate provider rejection without a real key or live HTTP request.
  mocks.axios.mockRejectedValue(Object.assign(new Error('Authentication failed'), {
    response: { status: 401 },
  }))
  mocks.fetch.mockResolvedValue({
    ok: false, status: 401, json: async () => ({ error: { message: 'Authentication failed' } }),
  })
  const result = await handler('test-api-key')('sk-test-invalid')
  // Judge the functional outcome, not a specific transport or error wording.
  expect(result.success).toBe(false)
})
