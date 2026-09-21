import { api, mountChat, respond, sessionId, submit, tick } from './renderer_support'

it('TC-VQ-003 / timeout ends polling, preserves history and permits successful retry', async () => {
  const hook = await mountChat()
  await submit(hook, 'failing question')
  expect(hook.result.current.isQueryProcessing).toBe(true)
  respond({ status: 'error', message: 'model timed out', current_step: 'Error', answer: 'stale active answer' })
  await tick()
  expect(hook.result.current.isQueryProcessing).toBe(false)
  expect(hook.result.current.isLoading).toBe(false)
  expect(hook.result.current.messages.some(m => m.content.includes('model timed out'))).toBe(true)
  expect(hook.result.current.messages.some(m => m.content === 'historic answer')).toBe(true)
  expect(hook.result.current.messages.some(m => m.content === 'stale active answer')).toBe(false)
  expect(hook.result.current.messages.some(m => m.isQueryAnalyzing)).toBe(false)
  const polls = api.videorag.getStatus.mock.calls.length
  await tick(6000)
  expect(api.videorag.getStatus).toHaveBeenCalledTimes(polls)
  await submit(hook, 'retry question')
  expect(api.videorag.queryVideo.mock.calls).toEqual([[sessionId, 'failing question'], [sessionId, 'retry question']])
  respond({ status: 'completed', answer: 'new answer', current_step: 'Completed' })
  await tick()
  expect(hook.result.current.isQueryProcessing).toBe(false)
  const messages = hook.result.current.messages
  expect(messages[messages.length - 1].content).toBe('new answer')
  expect(messages.filter(m => m.content === 'new answer')).toHaveLength(1)
  expect(messages.some(m => m.isQueryAnalyzing)).toBe(false)
  const completedPolls = api.videorag.getStatus.mock.calls.length
  await tick(6000)
  expect(api.videorag.getStatus).toHaveBeenCalledTimes(completedPolls)
})
