import { api, mountChat, respond, sessionId, submit, tick } from './renderer_support'

it('TC-VQ-004 / B waits for A and each question receives its own answer', async () => {
  const hook = await mountChat()
  await submit(hook, 'question A')
  expect(hook.result.current.isQueryProcessing).toBe(true)
  await submit(hook, 'question B')
  expect(api.videorag.queryVideo.mock.calls.map(call => call[1])).toEqual(['question A'])
  respond({ status: 'completed', answer: 'answer A' })
  await tick()
  expect(hook.result.current.isQueryProcessing).toBe(false)
  await submit(hook, 'question B')
  expect(api.videorag.queryVideo.mock.calls).toEqual([[sessionId, 'question A'], [sessionId, 'question B']])
  respond({ status: 'completed', answer: 'answer B' })
  await tick()
  // Ignore unrelated status messages; retain the pairing/order contract.
  const relevant = new Set(['question A', 'answer A', 'question B', 'answer B'])
  const dialogue = hook.result.current.messages.map(m => m.content).filter(text => relevant.has(text))
  expect(dialogue).toEqual(['question A', 'answer A', 'question B', 'answer B'])
  expect(hook.result.current.isQueryProcessing).toBe(false)
})
