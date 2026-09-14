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

import { registerFileHandlers } from '../../src/main/handlers/file-handlers'

type Handler = (...args: any[]) => Promise<any>

describe('filtered daily video selection scenario', () => {
  const handlers = new Map<string, Handler>()

  beforeEach(() => {
    handlers.clear()
    for (const mock of Object.values(mocks)) mock.mockReset()
    mocks.handle.mockImplementation((channel: string, callback: Handler) => {
      handlers.set(channel, callback)
    })
    registerFileHandlers()
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

    const result = await handlers.get('select-video-files')?.({})

    expect(result).toEqual({
      success: true,
      files: [
        { name: 'a.mp4', path: 'D:\\video\\a.mp4', size: 10 },
        { name: 'b.mkv', path: '/videos/b.mkv', size: 20 },
      ],
    })
  })
})

