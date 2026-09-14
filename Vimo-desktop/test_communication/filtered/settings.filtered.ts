import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  handle: vi.fn(),
  readFile: vi.fn(),
  writeFile: vi.fn(),
  access: vi.fn(),
  mkdir: vi.fn(),
}))

vi.mock('electron', () => ({ ipcMain: { handle: mocks.handle } }))
vi.mock('node:fs/promises', () => ({
  readFile: mocks.readFile,
  writeFile: mocks.writeFile,
  access: mocks.access,
  mkdir: mocks.mkdir,
}))

import { registerSettingsHandlers } from '../../src/main/handlers/settings'

type Handler = (...args: any[]) => Promise<any>

describe('filtered settings startup scenario', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, callback: Handler) => {
      handlers.set(channel, callback)
    })
    registerSettingsHandlers()
  })

  /**
   * Test Item 测试项：无配置文件时加载默认设置
   * Test Type：等价类划分、异常分支
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：bootstrap 配置文件不存在
   * Input 输入：access 抛出 ENOENT
   * Procedure 操作步骤：调用 load-settings 并检查默认字段
   * Output 预期结果：返回 success=true，默认 URL、模型和空存储路径完整
   */
  it('returns complete defaults when configuration files are absent', async () => {
    mocks.access.mockRejectedValue(Object.assign(new Error('missing'), { code: 'ENOENT' }))

    const result = await handlers.get('load-settings')?.({})

    expect(result.success).toBe(true)
    expect(result.settings).toMatchObject({
      openaiBaseUrl: 'https://api.openai.com/v1',
      processingModel: 'gpt-4o-mini',
      storeDirectory: '',
      openaiApiKey: '',
    })
  })
})

