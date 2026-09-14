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

import { registerSettingsHandlers } from '../src/main/handlers/settings'

type Handler = (...args: any[]) => Promise<any>

describe('settings IPC handlers', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, callback: Handler) => {
      handlers.set(channel, callback)
    })
    registerSettingsHandlers()
  })

  const handler = (channel: string): Handler => {
    const registered = handlers.get(channel)
    if (!registered) throw new Error(`Missing IPC handler: ${channel}`)
    return registered
  }

  /**
   * Test Item 测试项：设置 IPC 通道注册
   * Test Type：接口完整性测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：ipcMain.handle 已被 mock
   * Input 输入：调用 registerSettingsHandlers
   * Procedure 操作步骤：收集注册的通道名称并比较契约集合
   * Output 预期结果：保存、加载和 API Key 检测三个通道各注册一次
   */
  it('registers all settings communication channels', () => {
    expect([...handlers.keys()].sort()).toEqual([
      'load-settings',
      'save-settings',
      'test-api-key',
    ])
    expect(mocks.handle).toHaveBeenCalledTimes(3)
  })

  /**
   * Test Item 测试项：明显非法 API Key 校验
   * Test Type：无效等价类
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：test-api-key Handler 已注册
   * Input 输入：`invalid-key`
   * Procedure 操作步骤：直接调用 IPC Handler 并读取结构化响应
   * Output 预期结果：返回 success=false 和格式错误信息
   */
  it('rejects an API key without the required prefix', async () => {
    await expect(handler('test-api-key')({}, 'invalid-key')).resolves.toEqual({
      success: false,
      error: 'Invalid API key format',
    })
  })

  /**
   * Test Item 测试项：API Key 最短边界
   * Test Type：边界值分析
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：合法 Key 必须在 `sk-` 后包含密钥主体
   * Input 输入：仅包含前缀的 `sk-`
   * Procedure 操作步骤：调用 test-api-key 并比较业务结果
   * Output 预期结果：返回 success=false，空密钥主体不能通过校验
   */
  it('rejects an API key containing only the prefix', async () => {
    const result = await handler('test-api-key')({}, 'sk-')

    expect(result.success).toBe(false)
  })

  /**
   * Test Item 测试项：API Key 合法格式
   * Test Type：有效等价类
   * Test Criticality 重要级别：Medium
   * Pre-condition 预置条件：当前 Handler 只承担本地格式校验
   * Input 输入：`sk-valid-example`
   * Procedure 操作步骤：调用 test-api-key 并检查 success
   * Output 预期结果：格式校验通过，返回 success=true
   */
  it('accepts a non-empty API key with the expected prefix', async () => {
    await expect(handler('test-api-key')({}, 'sk-valid-example')).resolves.toEqual({
      success: true,
    })
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

    const result = await handler('load-settings')({})

    expect(result.success).toBe(true)
    expect(result.settings).toMatchObject({
      openaiBaseUrl: 'https://api.openai.com/v1',
      processingModel: 'gpt-4o-mini',
      storeDirectory: '',
      openaiApiKey: '',
    })
  })

  /**
   * Test Item 测试项：bootstrap 与主配置合并
   * Test Type：组合测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：两个配置文件均存在且 JSON 合法
   * Input 输入：bootstrap 提供 storeDirectory，主配置覆盖 processingModel
   * Procedure 操作步骤：按路径返回不同 JSON 后调用 load-settings
   * Output 预期结果：默认值、存储目录和主配置字段正确合并
   */
  it('merges bootstrap and main settings over defaults', async () => {
    mocks.access.mockResolvedValue(undefined)
    mocks.readFile.mockImplementation(async (filePath: unknown) =>
      String(filePath).endsWith('.videorag-bootstrap.json')
        ? JSON.stringify({ storeDirectory: 'D:\\store' })
        : JSON.stringify({ processingModel: 'custom-model' }),
    )

    const result = await handler('load-settings')({})

    expect(result.settings.storeDirectory).toBe('D:\\store')
    expect(result.settings.processingModel).toBe('custom-model')
    expect(result.settings.openaiBaseUrl).toBe('https://api.openai.com/v1')
  })

  /**
   * Test Item 测试项：设置持久化通信
   * Test Type：数据流测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：storeDirectory 有效且文件系统操作成功
   * Input 输入：存储目录、API Key 和模型设置
   * Procedure 操作步骤：调用 save-settings 并检查两次 writeFile 的 JSON
   * Output 预期结果：bootstrap 只保存目录，主配置不重复保存 storeDirectory
   */
  it('separates bootstrap location from main settings when saving', async () => {
    const settings = {
      storeDirectory: 'D:\\store',
      openaiApiKey: 'sk-example',
      processingModel: 'model-a',
    }
    mocks.access.mockResolvedValue(undefined)
    mocks.readFile.mockResolvedValue(JSON.stringify({ storeDirectory: 'D:\\store' }))
    mocks.writeFile.mockResolvedValue(undefined)
    mocks.mkdir.mockResolvedValue(undefined)

    const result = await handler('save-settings')({}, settings)
    const writtenJson = mocks.writeFile.mock.calls.map((call) => JSON.parse(call[1]))

    expect(result).toEqual({ success: true })
    expect(writtenJson[0]).toEqual({ storeDirectory: 'D:\\store' })
    expect(writtenJson[1]).toEqual({
      openaiApiKey: 'sk-example',
      processingModel: 'model-a',
    })
  })

  /**
   * Test Item 测试项：空设置对象异常处理
   * Test Type：健壮性测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：renderer 绕过类型声明直接发送 null
   * Input 输入：settings=`null`
   * Procedure 操作步骤：调用 save-settings 并观察是否产生未处理拒绝
   * Output 预期结果：返回可序列化的 success=false 响应，不写入文件
   */
  it('turns a null settings payload into a safe error response', async () => {
    const result = await handler('save-settings')({}, null)

    expect(result.success).toBe(false)
    expect(result.error).toBeTypeOf('string')
    expect(mocks.writeFile).not.toHaveBeenCalled()
  })
})
