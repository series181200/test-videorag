import { api, mountChat, respond, sessionId, submit, tick } from './renderer_support'

it.each(['', '   ', '\n', '\t', ' \n\t '])('TC-VQ-001 / blank %j never dispatches a query', async text => {
  const hook = await mountChat()
  await submit(hook, text)
  expect(api.videorag.queryVideo).not.toHaveBeenCalled()
  expect(hook.result.current.isQueryProcessing).toBe(false)
  expect(api.videorag.getStatus).not.toHaveBeenCalled()
})

it('TC-VQ-001 / valid question is trimmed and dispatched once', async () => {
  const hook = await mountChat()
  await submit(hook, '  视频讲了什么？  ')
  expect(api.videorag.queryVideo).toHaveBeenCalledTimes(1)
  expect(api.videorag.queryVideo).toHaveBeenCalledWith(sessionId, '视频讲了什么？')
  respond({ status: 'completed', answer: 'answer' })
  await tick()
  expect(hook.result.current.isQueryProcessing).toBe(false)
})

it.each(['none', 'analyzing'])('TC-VQ-002 / %s session cannot submit a model query', async state => {
  const hook = await mountChat(state)
  await submit(hook, 'question')
  expect(api.videorag.queryVideo).not.toHaveBeenCalled()
  expect(hook.result.current.isQueryProcessing).toBe(false)
})

it('TC-VQ-004 / B is blocked during A then answers stay paired after retry', async () => {
  const hook = await mountChat()
  await submit(hook, 'question A')
  expect(hook.result.current.isQueryProcessing).toBe(true)
  await submit(hook, 'question B')
  expect(api.videorag.queryVideo).toHaveBeenCalledTimes(1)
  expect(hook.result.current.messages.filter(m => m.type === 'user').map(m => m.content)).toEqual(['question A'])
  respond({ status: 'completed', answer: 'answer A' })
  await tick()
  expect(hook.result.current.isQueryProcessing).toBe(false)
  await submit(hook, 'question B')
  expect(api.videorag.queryVideo.mock.calls).toEqual([[sessionId, 'question A'], [sessionId, 'question B']])
  respond({ status: 'completed', answer: 'answer B' })
  await tick()
  const dialogue = hook.result.current.messages.filter(m => !m.isQueryAnalyzing).map(m => m.content)
  expect(dialogue).toEqual(['historic answer', 'question A', 'answer A', 'question B', 'answer B'])
  expect(hook.result.current.isQueryProcessing).toBe(false)
  const polls = api.videorag.getStatus.mock.calls.length
  await tick(6000)
  expect(api.videorag.getStatus).toHaveBeenCalledTimes(polls)
})
