import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn(),
  invoke: vi.fn(),
  on: vi.fn(),
  removeAllListeners: vi.fn(),
  electronAPI: { process: { platform: 'test' } },
}))

vi.mock('electron', () => ({
  contextBridge: { exposeInMainWorld: mocks.exposeInMainWorld },
  ipcRenderer: {
    invoke: mocks.invoke,
    on: mocks.on,
    removeAllListeners: mocks.removeAllListeners,
  },
}))

vi.mock('@electron-toolkit/preload', () => ({ electronAPI: mocks.electronAPI }))

describe('preload IPC bridge', () => {
  let api: any

  beforeAll(() => {
    Object.defineProperty(process, 'contextIsolated', {
      configurable: true,
      value: true,
    })
  })

  beforeEach(async () => {
    vi.resetModules()
    mocks.exposeInMainWorld.mockReset()
    mocks.invoke.mockReset()
    mocks.on.mockReset()
    mocks.removeAllListeners.mockReset()
    await import('../src/preload/index')
    api = mocks.exposeInMainWorld.mock.calls.find(([name]) => name === 'api')?.[1]
  })

  /**
   * Test Item 测试项：preload API 暴露
   * Test Type：接口契约测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：Electron 开启 contextIsolation
   * Input 输入：加载 `src/preload/index.ts`
   * Procedure 操作步骤：mock contextBridge 后导入模块并检查暴露对象
   * Output 预期结果：`electron` 和 `api` 分别暴露到 renderer，且 api 为对象
   */
  it('exposes the Electron and application APIs', () => {
    expect(mocks.exposeInMainWorld).toHaveBeenCalledWith('electron', mocks.electronAPI)
    expect(api).toBeTypeOf('object')
  })

  /**
   * Test Item 测试项：通用 IPC 调用入口 `window.api.invoke`
   * Test Type：接口一致性测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：renderer 的 `useVideoRAG` 依赖通用 invoke 方法
   * Input 输入：preload 暴露的 api 对象
   * Procedure 操作步骤：读取 api.invoke 的运行时类型
   * Output 预期结果：api.invoke 是函数，能够转发 renderer 使用的 IPC 调用
   */
  it('provides the generic invoke function declared and used by renderer', () => {
    expect(typeof api.invoke).toBe('function')
  })

  /**
   * Test Item 测试项：基础消息 IPC 映射
   * Test Type：接口契约测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：ipcRenderer.invoke 已被 mock
   * Input 输入：消息 `hello`
   * Procedure 操作步骤：调用 echoMessage 并检查 IPC 通道与参数
   * Output 预期结果：调用 `echo-message`，参数保持为 `hello`
   */
  it('maps echoMessage to the correct channel', async () => {
    mocks.invoke.mockResolvedValue('Echo: hello')
    const result = await api.echoMessage('hello')

    expect(mocks.invoke).toHaveBeenCalledWith('echo-message', 'hello')
    expect(result).toBe('Echo: hello')
  })

  /**
   * Test Item 测试项：聊天会话保存 IPC 映射
   * Test Type：接口契约测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：preload API 已成功暴露
   * Input 输入：chatId=`chat-1`，sessionData=`{title:'Demo'}`
   * Procedure 操作步骤：调用 chatSessions.save 并检查转发参数
   * Output 预期结果：调用 `save-chat-session` 且参数顺序不变
   */
  it('forwards chat session save arguments in order', async () => {
    const session = { title: 'Demo' }
    await api.chatSessions.save('chat-1', session)

    expect(mocks.invoke).toHaveBeenCalledWith('save-chat-session', 'chat-1', session)
  })

  /**
   * Test Item 测试项：VideoRAG 查询 IPC 映射
   * Test Type：接口契约测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：preload API 已成功暴露
   * Input 输入：chatId=`c1`、query=`总结视频`、mode=`videorag`
   * Procedure 操作步骤：调用 videorag.query 并检查 IPC 调用
   * Output 预期结果：通道为 `videorag:query`，三个参数完整且顺序正确
   */
  it('forwards a VideoRAG query without changing arguments', async () => {
    await api.videorag.query('c1', '总结视频', 'videorag')

    expect(mocks.invoke).toHaveBeenCalledWith(
      'videorag:query',
      'c1',
      '总结视频',
      'videorag',
    )
  })

  /**
   * Test Item 测试项：视频上传 IPC 映射
   * Test Type：组合测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：preload API 已成功暴露
   * Input 输入：会话 ID、两个视频路径、存储路径
   * Procedure 操作步骤：调用 uploadVideo 并检查数组和路径参数
   * Output 预期结果：所有视频路径作为同一数组转发且未丢失
   */
  it('forwards all video upload arguments', async () => {
    const videos = ['D:\\a.mp4', 'D:\\b.mp4']
    await api.videorag.uploadVideo('c1', videos, 'D:\\store')

    expect(mocks.invoke).toHaveBeenCalledWith(
      'videorag:upload-video',
      'c1',
      videos,
      'D:\\store',
    )
  })

  /**
   * Test Item 测试项：下载事件监听注册
   * Test Type：事件接口测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：ipcRenderer.on 已被 mock
   * Input 输入：进度回调函数
   * Procedure 操作步骤：调用 onDownloadProgress 并检查监听通道
   * Output 预期结果：只在 `download-progress` 通道注册一次监听器
   */
  it('registers the download progress listener on the expected channel', () => {
    const callback = vi.fn()
    api.onDownloadProgress(callback)

    expect(mocks.on).toHaveBeenCalledTimes(1)
    expect(mocks.on.mock.calls[0][0]).toBe('download-progress')
  })

  /**
   * Test Item 测试项：下载监听器清理
   * Test Type：状态清理测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：进度和错误监听器可能已经注册
   * Input 输入：调用 removeDownloadListeners
   * Procedure 操作步骤：检查 removeAllListeners 接收到的通道
   * Output 预期结果：进度与错误两个下载通道均被清理
   */
  it('removes both download event channel listeners', () => {
    api.removeDownloadListeners()

    expect(mocks.removeAllListeners).toHaveBeenCalledWith('download-progress')
    expect(mocks.removeAllListeners).toHaveBeenCalledWith('download-error')
  })

  /**
   * Test Item 测试项：Electron 事件对象隔离
   * Test Type：安全测试、故障推测
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：renderer 仅需要下载数据，不应接触原始 Electron event
   * Input 输入：模拟 event 和下载进度 data
   * Procedure 操作步骤：取得 preload 注册的监听函数并模拟事件触发
   * Output 预期结果：renderer 回调仅收到数据对象，原始 event 不跨越安全边界
   */
  it('does not expose the raw Electron event to renderer callbacks', () => {
    const callback = vi.fn()
    const event = { sender: { privileged: true } }
    const data = { type: 'imagebind', progress: 50 }
    api.onDownloadProgress(callback)
    const registeredListener = mocks.on.mock.calls[0][1]

    registeredListener(event, data)

    expect(callback).toHaveBeenCalledWith(data)
  })
})
