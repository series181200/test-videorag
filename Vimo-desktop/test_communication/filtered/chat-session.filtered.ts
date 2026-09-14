import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  handle: vi.fn(),
  readFile: vi.fn(),
  writeFile: vi.fn(),
  access: vi.fn(),
  mkdir: vi.fn(),
  readdir: vi.fn(),
  unlink: vi.fn(),
}))

vi.mock('electron', () => ({ ipcMain: { handle: mocks.handle } }))
vi.mock('node:fs/promises', () => ({
  readFile: mocks.readFile,
  writeFile: mocks.writeFile,
  access: mocks.access,
  mkdir: mocks.mkdir,
  readdir: mocks.readdir,
  unlink: mocks.unlink,
}))

import { registerChatSessionHandlers } from '../../src/main/handlers/chat-session-handlers'

type Handler = (...args: any[]) => Promise<any>

describe('filtered chat persistence scenario', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, callback: Handler) => {
      handlers.set(channel, callback)
    })
    registerChatSessionHandlers()
  })

  /**
   * Test Item 测试项：会话保存数据通信
   * Test Type：数据流测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：存储目录已配置且会话已存在
   * Input 输入：chatId=`chat-1`、标题和消息数组
   * Procedure 操作步骤：调用 save-chat-session 并解析写入 JSON
   * Output 预期结果：原字段完整保存并追加可解析的 lastUpdated
   */
  it('writes session data with a last-updated timestamp', async () => {
    mocks.readFile.mockImplementation(async (filePath: unknown) => {
      if (String(filePath).endsWith('.videorag-bootstrap.json')) {
        return JSON.stringify({ storeDirectory: 'D:\\store' })
      }
      throw new Error(`Unexpected read: ${filePath}`)
    })
    mocks.access.mockResolvedValue(undefined)
    mocks.mkdir.mockResolvedValue(undefined)
    mocks.writeFile.mockResolvedValue(undefined)
    const session = { id: 'chat-1', title: 'Demo', messages: ['hello'] }

    const result = await handlers.get('save-chat-session')?.({}, 'chat-1', session)
    const sessionWrite = mocks.writeFile.mock.calls.find(([path]) =>
      String(path).endsWith('chat-chat-1.json'),
    )
    const written = JSON.parse(sessionWrite?.[1])

    expect(result).toEqual({ success: true })
    expect(written).toMatchObject(session)
    expect(Number.isNaN(Date.parse(written.lastUpdated))).toBe(false)
  })
})

