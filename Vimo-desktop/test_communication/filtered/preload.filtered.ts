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

describe('filtered preload daily scenarios', () => {
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
    await import('../../src/preload/index')
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
})

