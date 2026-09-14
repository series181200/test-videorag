import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  handle: vi.fn(),
  axios: vi.fn(),
  spawn: vi.fn(),
  existsSync: vi.fn(),
  appRelaunch: vi.fn(),
  appExit: vi.fn(),
  unlink: vi.fn(),
  access: vi.fn(),
  readFile: vi.fn(),
  mkdir: vi.fn(),
}))

vi.mock('electron', () => ({
  ipcMain: { handle: mocks.handle },
  app: { relaunch: mocks.appRelaunch, exit: mocks.appExit },
}))
vi.mock('axios', () => ({ default: mocks.axios }))
vi.mock('child_process', () => ({ spawn: mocks.spawn }))
vi.mock('fs', () => ({ default: { existsSync: mocks.existsSync } }))
vi.mock('node:fs/promises', () => ({
  unlink: mocks.unlink,
  access: mocks.access,
  readFile: mocks.readFile,
  mkdir: mocks.mkdir,
}))

import { setupVideoRAGHandlers } from '../../src/main/handlers/videorag-handlers'

type Handler = (...args: any[]) => Promise<any>

describe('filtered Python API daily scenarios', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, callback: Handler) => {
      handlers.set(channel, callback)
    })
    setupVideoRAGHandlers()
  })

  /**
   * Test Item 测试项：后端健康检查请求
   * Test Type：接口契约测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：axios 返回健康状态
   * Input 输入：调用 videorag:health-check
   * Procedure 操作步骤：执行 Handler 并检查 HTTP 配置和 IPC 响应
   * Output 预期结果：向 `/api/health` 发 GET 请求，默认超时 30000ms
   */
  it('maps health checks to the Python health endpoint', async () => {
    mocks.axios.mockResolvedValue({ data: { status: 'ok' } })

    const result = await handlers.get('videorag:health-check')?.({})

    expect(mocks.axios).toHaveBeenCalledWith({
      method: 'GET',
      url: 'http://localhost:64451/api/health',
      data: undefined,
      timeout: 30000,
    })
    expect(result).toEqual({ success: true, data: { status: 'ok' } })
  })

  /**
   * Test Item 测试项：视频上传请求映射
   * Test Type：接口契约测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：Python API 正常响应
   * Input 输入：chatId、两个视频路径、baseStoragePath
   * Procedure 操作步骤：调用 upload-video Handler 并检查 URL、方法和 snake_case 请求体
   * Output 预期结果：POST 到会话上传端点，超时为 60000ms
   */
  it('maps video uploads to the expected backend payload', async () => {
    mocks.axios.mockResolvedValue({ data: { task_id: 't1' } })
    const videos = ['D:\\a.mp4', 'D:\\b.mp4']

    const result = await handlers.get('videorag:upload-video')?.(
      {},
      'chat-1',
      videos,
      'D:\\store',
    )

    expect(mocks.axios).toHaveBeenCalledWith({
      method: 'POST',
      url: 'http://localhost:64451/api/sessions/chat-1/videos/upload',
      data: { video_path_list: videos, base_storage_path: 'D:\\store' },
      timeout: 60000,
    })
    expect(result).toEqual({ success: true, data: { task_id: 't1' } })
  })

  /**
   * Test Item 测试项：Python API 业务错误转换
   * Test Type：异常测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：axios 拒绝且 response.data.error 存在
   * Input 输入：后端错误 `session not found`
   * Procedure 操作步骤：调用 list-indexed Handler 并检查 IPC 响应
   * Output 预期结果：返回 success=false 和后端业务错误，不泄漏 Axios 对象
   */
  it('returns backend error text as a serializable IPC failure', async () => {
    mocks.axios.mockRejectedValue({
      message: 'Request failed',
      response: { data: { error: 'session not found' } },
    })

    const result = await handlers.get('videorag:list-indexed')?.({}, 'missing')

    expect(result).toEqual({ success: false, error: 'session not found' })
  })
})

