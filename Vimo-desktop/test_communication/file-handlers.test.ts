import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  handle: vi.fn(),
  showOpenDialog: vi.fn(),
  showSaveDialog: vi.fn(),
  readFile: vi.fn(),
  writeFile: vi.fn(),
  stat: vi.fn(),
}))

vi.mock('electron', () => ({
  ipcMain: { handle: mocks.handle },
  dialog: {
    showOpenDialog: mocks.showOpenDialog,
    showSaveDialog: mocks.showSaveDialog,
  },
}))

vi.mock('node:fs/promises', () => ({
  readFile: mocks.readFile,
  writeFile: mocks.writeFile,
  stat: mocks.stat,
}))

import { registerFileHandlers } from '../src/main/handlers/file-handlers'

type Handler = (...args: any[]) => Promise<any>

describe('file IPC handlers', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, handler: Handler) => {
      handlers.set(channel, handler)
    })
    registerFileHandlers()
  })

  const handler = (channel: string): Handler => {
    const registered = handlers.get(channel)
    if (!registered) throw new Error(`Missing IPC handler: ${channel}`)
    return registered
  }

  /**
   * Test Item 测试项：文件 IPC 通道注册
   * Test Type：接口完整性测试
   * Test Criticality 重要级别：Critical
   * Pre-condition 预置条件：ipcMain.handle 使用内存 registry 替代
   * Input 输入：调用 registerFileHandlers
   * Procedure 操作步骤：收集所有注册通道并与契约集合比较
   * Output 预期结果：五个文件相关 IPC 通道完整且无重复
   */
  it('registers the complete file communication contract', () => {
    expect([...handlers.keys()].sort()).toEqual([
      'echo-message',
      'read-file',
      'save-file',
      'select-folder',
      'select-video-files',
    ])
    expect(mocks.handle).toHaveBeenCalledTimes(5)
  })

  /**
   * Test Item 测试项：读取文本文件成功分支
   * Test Type：等价类划分
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：文件对话框返回一个有效路径
   * Input 输入：`D:\notes.txt`，文件内容 `hello`
   * Procedure 操作步骤：调用 read-file Handler 并检查读取编码和响应
   * Output 预期结果：以 UTF-8 读取并返回 success、content 和 path
   */
  it('returns selected text file content and path', async () => {
    mocks.showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['D:\\notes.txt'] })
    mocks.readFile.mockResolvedValue('hello')

    const result = await handler('read-file')({})

    expect(mocks.readFile).toHaveBeenCalledWith('D:\\notes.txt', 'utf-8')
    expect(result).toEqual({ success: true, content: 'hello', path: 'D:\\notes.txt' })
  })

  /**
   * Test Item 测试项：取消读取文件
   * Test Type：状态迁移测试
   * Test Criticality 重要级别：Medium
   * Pre-condition 预置条件：用户打开选择框后取消
   * Input 输入：`canceled=true`、空路径列表
   * Procedure 操作步骤：调用 read-file Handler 并检查是否访问磁盘
   * Output 预期结果：返回失败和 `No file selected`，不调用 readFile
   */
  it('does not read from disk when file selection is cancelled', async () => {
    mocks.showOpenDialog.mockResolvedValue({ canceled: true, filePaths: [] })

    const result = await handler('read-file')({})

    expect(result).toEqual({ success: false, error: 'No file selected' })
    expect(mocks.readFile).not.toHaveBeenCalled()
  })

  /**
   * Test Item 测试项：读取文件异常转换
   * Test Type：异常测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：选择成功但文件系统拒绝读取
   * Input 输入：readFile 抛出 `permission denied`
   * Procedure 操作步骤：调用 Handler 并观察 Promise 是否被安全转换
   * Output 预期结果：Handler 不向 IPC 抛异常，返回 success=false 和原错误消息
   */
  it('converts read failures into a serializable response', async () => {
    mocks.showOpenDialog.mockResolvedValue({ canceled: false, filePaths: ['D:\\secret.txt'] })
    mocks.readFile.mockRejectedValue(new Error('permission denied'))

    await expect(handler('read-file')({})).resolves.toEqual({
      success: false,
      error: 'permission denied',
    })
  })

  /**
   * Test Item 测试项：保存文件成功分支
   * Test Type：等价类划分
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：保存对话框返回目标路径
   * Input 输入：内容 `report`、路径 `D:\report.txt`
   * Procedure 操作步骤：调用 save-file Handler 并检查 writeFile 参数
   * Output 预期结果：以 UTF-8 写入原内容并返回成功路径
   */
  it('writes selected file content using UTF-8', async () => {
    mocks.showSaveDialog.mockResolvedValue({ canceled: false, filePath: 'D:\\report.txt' })
    mocks.writeFile.mockResolvedValue(undefined)

    const result = await handler('save-file')({}, 'report')

    expect(mocks.writeFile).toHaveBeenCalledWith('D:\\report.txt', 'report', 'utf-8')
    expect(result).toEqual({ success: true, path: 'D:\\report.txt' })
  })

  /**
   * Test Item 测试项：视频文件元数据组装
   * Test Type：组合测试
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：用户选择两个可读取的视频文件
   * Input 输入：Windows 与 POSIX 风格路径、不同文件大小
   * Procedure 操作步骤：调用 select-video-files 并检查返回数组
   * Output 预期结果：每项包含正确的 name、path 和 size，顺序不变
   */
  it('returns metadata for every selected video', async () => {
    mocks.showOpenDialog.mockResolvedValue({
      canceled: false,
      filePaths: ['D:\\video\\a.mp4', '/videos/b.mkv'],
    })
    mocks.stat.mockResolvedValueOnce({ size: 10 }).mockResolvedValueOnce({ size: 20 })

    const result = await handler('select-video-files')({})

    expect(result).toEqual({
      success: true,
      files: [
        { name: 'a.mp4', path: 'D:\\video\\a.mp4', size: 10 },
        { name: 'b.mkv', path: '/videos/b.mkv', size: 20 },
      ],
    })
  })

  /**
   * Test Item 测试项：全部视频元数据读取失败
   * Test Type：故障注入、错误推测
   * Test Criticality 重要级别：High
   * Pre-condition 预置条件：用户选择了文件，但 stat 对所有文件均失败
   * Input 输入：一个不存在的视频路径
   * Procedure 操作步骤：调用 select-video-files 并比较 success 与错误信息
   * Output 预期结果：返回 success=false，不能把空文件集合报告为上传选择成功
   */
  it('reports failure when none of the selected videos can be inspected', async () => {
    mocks.showOpenDialog.mockResolvedValue({
      canceled: false,
      filePaths: ['D:\\missing.mp4'],
    })
    mocks.stat.mockRejectedValue(new Error('not found'))

    const result = await handler('select-video-files')({})

    expect(result.success).toBe(false)
    expect(result.error).toBeTruthy()
  })
})
