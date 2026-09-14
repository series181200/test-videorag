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

import { setupVideoRAGHandlers } from '../src/main/handlers/videorag-handlers'

type Handler = (...args: any[]) => Promise<any>

describe('VideoRAG backend communication handlers', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, callback: Handler) => {
      handlers.set(channel, callback)
    })
    setupVideoRAGHandlers()
  })

  const handler = (channel: string): Handler => {
    const registered = handlers.get(channel)
    if (!registered) throw new Error(`Missing IPC handler: ${channel}`)
    return registered
  }

  /**
   * Test Item 测试项：VideoRAG IPC 通道注册
   * Test Type：接口完整性测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：ipcMain.handle 已被 mock
   * Input 输入：调用 setupVideoRAGHandlers
   * Procedure 操作步骤：检查所有后端通信和应用控制通道
   * Output 预期结果：预定的二十一个通道均注册且名称唯一
   */
  it('registers every VideoRAG and app control channel', () => {
    expect([...handlers.keys()].sort()).toEqual([
      'app:clear-config',
      'app:restart',
      'videorag:delete-session',
      'videorag:get-localStorage-config',
      'videorag:get-status',
      'videorag:get-video-duration',
      'videorag:health-check',
      'videorag:imagebind-status',
      'videorag:initialize',
      'videorag:list-indexed',
      'videorag:load-imagebind',
      'videorag:query',
      'videorag:query-video',
      'videorag:reinitialize-config',
      'videorag:release-imagebind',
      'videorag:service-status',
      'videorag:session-status',
      'videorag:start-service',
      'videorag:stop-service',
      'videorag:system-status',
      'videorag:upload-video',
    ])
    expect(mocks.handle).toHaveBeenCalledTimes(21)
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

    const result = await handler('videorag:health-check')({})

    expect(mocks.axios).toHaveBeenCalledWith({
      method: 'GET',
      url: 'http://localhost:64451/api/health',
      data: undefined,
      timeout: 30000,
    })
    expect(result).toEqual({ success: true, data: { status: 'ok' } })
  })

  /**
   * Test Item 测试项：VideoRAG 初始化请求
   * Test Type：数据流测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：Python API 正常响应
   * Input 输入：包含 API Key 与存储路径的 config
   * Procedure 操作步骤：调用 initialize Handler 并检查 axios 请求体
   * Output 预期结果：POST 到 `/initialize`，配置原样传递且超时为 120000ms
   */
  it('posts initialization configuration with the long timeout', async () => {
    const config = { openai_api_key: 'sk-test', base_storage_path: 'D:\\store' }
    mocks.axios.mockResolvedValue({ data: { success: true } })

    await handler('videorag:initialize')({}, config)

    expect(mocks.axios).toHaveBeenCalledWith({
      method: 'POST',
      url: 'http://localhost:64451/api/initialize',
      data: config,
      timeout: 120000,
    })
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

    const result = await handler('videorag:upload-video')(
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
   * Test Item 测试项：查询默认模式
   * Test Type：默认值测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：调用时省略 mode
   * Input 输入：chatId=`c1`、query=`summary`
   * Procedure 操作步骤：调用 query Handler 并检查请求体
   * Output 预期结果：请求体自动包含 mode=`videorag`
   */
  it('uses videorag as the default query mode', async () => {
    mocks.axios.mockResolvedValue({ data: { response: 'answer' } })

    await handler('videorag:query')({}, 'c1', 'summary')

    expect(mocks.axios.mock.calls[0][0].data).toEqual({
      query: 'summary',
      mode: 'videorag',
    })
  })

  /**
   * Test Item 测试项：视频时长请求超时配置
   * Test Type：边界配置测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：视频探测可能超过默认请求时长
   * Input 输入：videoPath=`D:\video.mp4`
   * Procedure 操作步骤：调用 get-video-duration 并检查 HTTP 请求
   * Output 预期结果：POST `/video/duration`，请求体字段为 video_path，超时 60000ms
   */
  it('uses the dedicated timeout for video duration detection', async () => {
    mocks.axios.mockResolvedValue({ data: { duration: 12.5, fps: 25 } })

    const result = await handler('videorag:get-video-duration')({}, 'D:\\video.mp4')

    expect(mocks.axios).toHaveBeenCalledWith({
      method: 'POST',
      url: 'http://localhost:64451/api/video/duration',
      data: { video_path: 'D:\\video.mp4' },
      timeout: 60000,
    })
    expect(result).toMatchObject({ success: true, duration: 12.5, fps: 25 })
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

    const result = await handler('videorag:list-indexed')({}, 'missing')

    expect(result).toEqual({ success: false, error: 'session not found' })
  })

  /**
   * Test Item 测试项：HTTP 超时错误转换
   * Test Type：异常测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：axios 以 ECONNABORTED 拒绝
   * Input 输入：状态查询超时
   * Procedure 操作步骤：调用 get-status Handler 并检查错误文本中的超时值
   * Output 预期结果：返回 success=false，错误说明 10000ms 超时
   */
  it('reports the endpoint-specific timeout to renderer', async () => {
    mocks.axios.mockRejectedValue({ code: 'ECONNABORTED', message: 'timeout' })

    const result = await handler('videorag:get-status')({}, 'c1')

    expect(result.success).toBe(false)
    expect(result.error).toContain('10000ms')
  })

  /**
   * Test Item 测试项：空查询参数校验
   * Test Type：无效等价类
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：renderer 校验可被绕过，main 是 IPC 信任边界
   * Input 输入：chatId=`c1`、query 为空字符串
   * Procedure 操作步骤：直接调用 query Handler 并监测 axios
   * Output 预期结果：返回 success=false，且不向 Python 后端发送空查询
   */
  it('rejects an empty query before contacting Python', async () => {
    mocks.axios.mockResolvedValue({ data: { response: '' } })

    const result = await handler('videorag:query')({}, 'c1', '')

    expect(result.success).toBe(false)
    expect(mocks.axios).not.toHaveBeenCalled()
  })

  /**
   * Test Item 测试项：会话 ID 的 URL 编码
   * Test Type：安全测试、等价类划分
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：chatId 可能包含空格、斜杠或查询字符
   * Input 输入：chatId=`a/b?admin=true`
   * Procedure 操作步骤：调用 session-status 并读取 axios URL
   * Output 预期结果：动态路径段经 encodeURIComponent 编码，不能改变后端路由
   */
  it('URL-encodes a chat ID before adding it to the backend path', async () => {
    mocks.axios.mockResolvedValue({ data: {} })

    await handler('videorag:session-status')({}, 'a/b?admin=true')

    expect(mocks.axios.mock.calls[0][0].url).toBe(
      'http://localhost:64451/api/sessions/a%2Fb%3Fadmin%3Dtrue/status',
    )
  })

  /**
   * Test Item 测试项：状态类型查询参数编码
   * Test Type：安全测试、组合测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：type 来自 renderer 且可含 URL 控制字符
   * Input 输入：type=`video&admin=true`
   * Procedure 操作步骤：调用 get-status 并读取生成的 URL
   * Output 预期结果：type 被编码为单一参数值，不注入额外查询参数
   */
  it('URL-encodes the optional status type query parameter', async () => {
    mocks.axios.mockResolvedValue({ data: {} })

    await handler('videorag:get-status')({}, 'c1', 'video&admin=true')

    expect(mocks.axios.mock.calls[0][0].url).toBe(
      'http://localhost:64451/api/sessions/c1/status?type=video%26admin%3Dtrue',
    )
  })

  /**
   * Test Item 测试项：应用重启 IPC
   * Test Type：状态迁移测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：Electron app API 已被 mock
   * Input 输入：调用 app:restart
   * Procedure 操作步骤：执行 Handler 并检查 relaunch 与 exit 顺序参数
   * Output 预期结果：调用 relaunch、以状态码 0 退出并返回 success=true
   */
  it('relaunches and exits the application on restart', async () => {
    const result = await handler('app:restart')({})

    expect(mocks.appRelaunch).toHaveBeenCalledOnce()
    expect(mocks.appExit).toHaveBeenCalledWith(0)
    expect(result).toEqual({ success: true })
  })

  /**
   * Test Item 测试项：清理不存在的配置文件
   * Test Type：幂等性测试
   * Test Criticality 重要级别：Medium
   * Pre-condition 预置条件：bootstrap 配置文件已经不存在
   * Input 输入：unlink 抛出 ENOENT
   * Procedure 操作步骤：调用 app:clear-config 并检查响应
   * Output 预期结果：重复清理仍返回 success=true
   */
  it('treats clearing an absent bootstrap file as successful', async () => {
    mocks.unlink.mockRejectedValue(Object.assign(new Error('missing'), { code: 'ENOENT' }))

    const result = await handler('app:clear-config')({})

    expect(result).toEqual({ success: true })
  })
})
