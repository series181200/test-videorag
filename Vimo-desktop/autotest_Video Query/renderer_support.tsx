import React from 'react'
import { act, cleanup, renderHook } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { useChat } from '../src/renderer/src/hooks/useChat'

// Context and background index metadata are fixtures. useChat and utils/chat
// remain real, including query submission, polling, messages and recovery.
const boundary = vi.hoisted(() => ({ context: {} as any, rag: {} as any }))
vi.mock('../src/renderer/src/contexts/ChatSessionContext', () => ({ useChatSessionContext: () => boundary.context }))
vi.mock('../src/renderer/src/hooks/useVideoRAG', () => ({ useVideoRAG: () => boundary.rag }))

export const sessionId = 'vq-session'
export let session: any
export let api: any
export let queryState: any
const clone = (value: any) => JSON.parse(JSON.stringify(value))
let revokeDescriptor: PropertyDescriptor | undefined

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-21T00:00:00Z'))
  session = {
    id: sessionId, title: 'Query fixture', analysisState: 'completed',
    videos: [{ name: 'lesson.mp4', path: 'C:/fixtures/lesson.mp4', url: 'blob:fixture', size: 100 }],
    messages: [{ id: 'historic-answer', type: 'assistant', content: 'historic answer', timestamp: '2026-09-20T00:00:00Z' }],
  }
  boundary.context = {
    isLoading: false, getSessionInfo: (id: string) => id === sessionId ? session : null,
    createSessionInfo: vi.fn(), updateSessionInfo: vi.fn(),
  }
  boundary.rag = { sessionStatus: {}, indexedVideos: [], processingVideos: [], videoStatus: {}, error: null }
  queryState = { status: 'processing', query: '', message: 'Working', current_step: 'Processing' }
  api = {
    chatSessions: {
      load: vi.fn(async (id: string) => {
        if (id !== sessionId) throw new Error('Unexpected session load')
        return { success: true, session: clone(session) }
      }),
      save: vi.fn(async (id: string, data: any) => {
        if (id !== sessionId) throw new Error('Unexpected session save')
        session = clone(data)
        return { success: true }
      }),
    },
    videorag: {
      queryVideo: vi.fn(async (id: string, query: string) => {
        if (id !== sessionId) throw new Error('Unexpected query session')
        queryState = { status: 'processing', query, message: 'Working', current_step: 'Processing' }
        return { success: true, data: { status: 'started' } }
      }),
      getStatus: vi.fn(async (id: string, type: string) => {
        if (id !== sessionId || type !== 'query') throw new Error('Unexpected polling request')
        return { success: true, data: clone(queryState) }
      }),
    },
  }
  vi.stubGlobal('api', api)
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Live network disabled') }))
  revokeDescriptor = Object.getOwnPropertyDescriptor(URL, 'revokeObjectURL')
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
})

afterEach(() => {
  cleanup()
  vi.clearAllTimers()
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  if (revokeDescriptor) Object.defineProperty(URL, 'revokeObjectURL', revokeDescriptor)
  else delete (URL as any).revokeObjectURL
})

export async function flush() {
  // Drain bounded promise chains inside React act without advancing polling time.
  await act(async () => { for (let i = 0; i < 40; i++) await Promise.resolve() })
}
export async function mountChat(state = 'completed') {
  session.analysisState = state
  if (state === 'none') session.videos = []
  const hook = renderHook(() => useChat(), {
    wrapper: ({ children }) => <MemoryRouter initialEntries={['/chat/' + sessionId]}>
      <Routes><Route path="/chat/:chatId" element={children} /></Routes>
    </MemoryRouter>,
  })
  await flush()
  expect(hook.result.current.messages.some(message => message.content === 'historic answer')).toBe(true)
  return hook
}
export async function submit(hook: Awaited<ReturnType<typeof mountChat>>, text: string) {
  // A later event obtains the latest callback after the input state renders.
  await act(async () => { hook.result.current.setInputValue(text) })
  await act(async () => { await hook.result.current.handleSendMessage() })
  await flush()
}
export async function tick(ms = 2000) {
  await act(async () => { await vi.advanceTimersByTimeAsync(ms) })
  await flush()
}
export function respond(state: Record<string, unknown>) { queryState = { ...queryState, ...state } }
