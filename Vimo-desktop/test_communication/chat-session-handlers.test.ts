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

import { registerChatSessionHandlers } from '../src/main/handlers/chat-session-handlers'

type Handler = (...args: any[]) => Promise<any>

describe('chat session IPC handlers', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, callback: Handler) => {
      handlers.set(channel, callback)
    })
    registerChatSessionHandlers()
  })

  const handler = (channel: string): Handler => {
    const registered = handlers.get(channel)
    if (!registered) throw new Error(`Missing IPC handler: ${channel}`)
    return registered
  }

  const mockBootstrap = (storeDirectory = 'D:\\store') => {
    mocks.readFile.mockImplementation(async (filePath: unknown) => {
      const path = String(filePath)
      if (path.endsWith('.videorag-bootstrap.json')) {
        return JSON.stringify({ storeDirectory })
      }
      if (path.endsWith('session-order.json')) {
        return JSON.stringify({ sessionOrder: [] })
      }
      throw new Error(`Unexpected read: ${path}`)
    })
  }

  /**
   * Test Item 测试项：聊天会话 IPC 通道注册
   * Test Type：接口完整性测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：ipcMain.handle 已被 mock
   * Input 输入：调用 registerChatSessionHandlers
   * Procedure 操作步骤：收集注册通道并与公开契约比较
   * Output 预期结果：七个会话管理通道各注册一次
   */
  it('registers the complete chat session contract', () => {
    expect([...handlers.keys()].sort()).toEqual([
      'delete-chat-session',
      'ensure-storage-directory',
      'get-storage-info',
      'list-chat-sessions',
      'load-chat-session',
      'save-chat-session',
      'update-session-order',
    ])
    expect(mocks.handle).toHaveBeenCalledTimes(7)
  })

  /**
   * Test Item 测试项：未配置存储目录时加载会话
   * Test Type：状态测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：bootstrap 文件不存在
   * Input 输入：chatId=`chat-1`
   * Procedure 操作步骤：令 access 失败后调用 load-chat-session
   * Output 预期结果：返回 success=false 和未配置提示，不尝试读取会话文件
   */
  it('reports an unconfigured storage directory when loading', async () => {
    mocks.access.mockRejectedValue(new Error('missing'))

    const result = await handler('load-chat-session')({}, 'chat-1')

    expect(result).toEqual({ success: false, error: 'Storage directory not configured' })
    expect(mocks.readFile).not.toHaveBeenCalled()
  })

  /**
   * Test Item 测试项：加载不存在的会话
   * Test Type：无效等价类
   * Test Criticality 重要级别：Medium
   * Pre-condition 预置条件：存储目录已配置但会话文件不存在
   * Input 输入：chatId=`missing`
   * Procedure 操作步骤：bootstrap 读取成功，会话 access 抛出 ENOENT
   * Output 预期结果：返回 success=true、session=null，表示正常的未找到状态
   */
  it('returns a null session for a missing session file', async () => {
    mockBootstrap()
    mocks.access
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(Object.assign(new Error('missing'), { code: 'ENOENT' }))

    const result = await handler('load-chat-session')({}, 'missing')

    expect(result).toEqual({ success: true, session: null })
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
    mockBootstrap()
    mocks.access.mockResolvedValue(undefined)
    mocks.mkdir.mockResolvedValue(undefined)
    mocks.writeFile.mockResolvedValue(undefined)
    const session = { id: 'chat-1', title: 'Demo', messages: ['hello'] }

    const result = await handler('save-chat-session')({}, 'chat-1', session)
    const sessionWrite = mocks.writeFile.mock.calls.find(([path]) =>
      String(path).endsWith('chat-chat-1.json'),
    )
    const written = JSON.parse(sessionWrite?.[1])

    expect(result).toEqual({ success: true })
    expect(written).toMatchObject(session)
    expect(Number.isNaN(Date.parse(written.lastUpdated))).toBe(false)
  })

  /**
   * Test Item 测试项：会话默认时间排序
   * Test Type：状态序列测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：存在两个会话且没有自定义顺序
   * Input 输入：旧会话和新会话的 JSON
   * Procedure 操作步骤：模拟目录与文件读取后调用 list-chat-sessions
   * Output 预期结果：会话按 lastUpdated 从新到旧排列
   */
  it('sorts sessions newest first when no custom order exists', async () => {
    mocks.access.mockResolvedValue(undefined)
    mocks.readdir.mockResolvedValue(['chat-old.json', 'ignore.txt', 'chat-new.json'])
    mocks.readFile.mockImplementation(async (filePath: unknown) => {
      const path = String(filePath)
      if (path.endsWith('.videorag-bootstrap.json')) {
        return JSON.stringify({ storeDirectory: 'D:\\store' })
      }
      if (path.endsWith('chat-old.json')) {
        return JSON.stringify({ id: 'old', lastUpdated: '2024-01-01T00:00:00Z' })
      }
      if (path.endsWith('chat-new.json')) {
        return JSON.stringify({ id: 'new', lastUpdated: '2025-01-01T00:00:00Z' })
      }
      if (path.endsWith('session-order.json')) {
        return JSON.stringify({ sessionOrder: [] })
      }
      throw new Error(`Unexpected read: ${path}`)
    })

    const result = await handler('list-chat-sessions')({})

    expect(result.sessions.map((session: any) => session.id)).toEqual(['new', 'old'])
  })

  /**
   * Test Item 测试项：会话 ID 路径分隔符校验
   * Test Type：安全测试、无效等价类
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：renderer 参数可能绕过 TypeScript 类型直接进入 IPC
   * Input 输入：chatId=`../../../outside`
   * Procedure 操作步骤：直接调用 save-chat-session 并监测 writeFile
   * Output 预期结果：拒绝包含路径分隔符的 ID 且不执行任何会话写入
   */
  it('rejects a chat ID capable of escaping the storage directory', async () => {
    mockBootstrap()
    mocks.access.mockResolvedValue(undefined)
    mocks.mkdir.mockResolvedValue(undefined)
    mocks.writeFile.mockResolvedValue(undefined)

    const result = await handler('save-chat-session')({}, '../../../outside', { id: 'x' })

    expect(result.success).toBe(false)
    expect(mocks.writeFile).not.toHaveBeenCalled()
  })

  /**
   * Test Item 测试项：非法会话排序操作校验
   * Test Type：无效等价类、健壮性测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：运行时 IPC 参数不受 TypeScript 联合类型保护
   * Input 输入：operation=`overwrite`
   * Procedure 操作步骤：绕过静态类型调用 update-session-order
   * Output 预期结果：返回 success=false，不把未知操作当作 reorder 执行
   */
  it('rejects an unsupported session order operation at runtime', async () => {
    mockBootstrap()
    mocks.access.mockResolvedValue(undefined)
    mocks.mkdir.mockResolvedValue(undefined)
    mocks.writeFile.mockResolvedValue(undefined)

    const result = await handler('update-session-order')({}, ['chat-1'], 'overwrite')

    expect(result.success).toBe(false)
    expect(mocks.writeFile).not.toHaveBeenCalled()
  })

  /**
   * Test Item 测试项：会话删除异常映射
   * Test Type：异常测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：会话路径有效但 unlink 失败
   * Input 输入：unlink 抛出 `permission denied`
   * Procedure 操作步骤：调用 delete-chat-session 并读取响应
   * Output 预期结果：返回 success=false 和原始错误消息，不产生未处理异常
   */
  it('converts session deletion failures into an IPC response', async () => {
    mockBootstrap()
    mocks.access.mockResolvedValue(undefined)
    mocks.unlink.mockRejectedValue(new Error('permission denied'))

    const result = await handler('delete-chat-session')({}, 'chat-1')

    expect(result).toEqual({ success: false, error: 'permission denied' })
  })
})
