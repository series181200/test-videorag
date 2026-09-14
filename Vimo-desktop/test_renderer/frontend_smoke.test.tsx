import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'

import App from '../src/renderer/src/App'

type BootOptions = {
  initialized?: boolean
  storedSessions?: Record<string, any>
  videoCount?: 1 | 2
  analysisFailure?: boolean
}

function installRendererApi(options: BootOptions = {}) {
  const initialized = options.initialized ?? true
  const sessions = { ...(options.storedSessions ?? {}) }
  const videoCount = options.videoCount ?? 2
  const analysisFailure = options.analysisFailure ?? false
  const settings = initialized
    ? {
        storeDirectory: 'C:/VimoTestData',
        imagebindInstalled: true,
        openaiBaseUrl: 'https://api.openai.com/v1',
        processingModel: 'gpt-4o-mini',
        analysisModel: 'gpt-4o-mini',
      }
    : {}

  const saveSession = (id: string, patch: any) => {
    sessions[id] = { ...(sessions[id] || {}), ...patch, id }
    return { success: true }
  }

  const api = {
    invoke: vi.fn(async () => ({ success: true })),
    loadSettings: vi.fn(async () => ({ success: true, settings })),
    saveSettings: vi.fn(async (nextSettings: any) => {
      Object.assign(settings, nextSettings)
      return { success: true }
    }),
    selectFolder: vi.fn(async () => ({ success: true, path: 'C:/VimoTestData' })),
    checkModelFiles: vi.fn(async () => ({ imagebind: true })),
    downloadImageBind: vi.fn(async () => ({ success: true })),
    onDownloadProgress: vi.fn(),
    removeDownloadListeners: vi.fn(),
    chatSessions: {
      load: vi.fn(async (id: string) => ({ success: true, session: sessions[id] })),
      save: vi.fn(async (id: string, data: any) => saveSession(id, data)),
      list: vi.fn(async () => ({ success: true, sessions: Object.values(sessions) })),
      delete: vi.fn(async (id: string) => {
        delete sessions[id]
        return { success: true }
      }),
      getStorageInfo: vi.fn(async () => ({
        success: true,
        storeDirectory: 'C:/VimoTestData',
        isConfigured: true,
      })),
      ensureStorageDirectory: vi.fn(async () => ({ success: true })),
      updateSessionOrder: vi.fn(async () => ({ success: true })),
    },
    videorag: {
      systemStatus: vi.fn(async () => ({
        success: true,
        data: { total_sessions: 0, global_config_set: true, imagebind_loaded: true },
      })),
      imagebindStatus: vi.fn(async () => ({ success: true, data: { loaded: true } })),
      startService: vi.fn(async () => ({ success: true })),
      stopService: vi.fn(async () => ({ success: true })),
      loadImageBind: vi.fn(async () => ({ success: true })),
      releaseImageBind: vi.fn(async () => ({ success: true })),
      reinitializeConfig: vi.fn(async () => ({ success: true })),
      uploadVideo: vi.fn(async (id: string) => {
        saveSession(id, { analysisState: 'analyzing' })
        return { success: true, data: { status: 'processing' } }
      }),
      getStatus: vi.fn(async (_id: string, type?: string) =>
        type === 'query'
          ? {
              success: true,
              data: { status: 'completed', answer: '视频中出现了一辆汽车。' },
            }
          : analysisFailure
            ? {
                success: true,
                data: {
                  status: 'error',
                  current_step: 'Analyze',
                  message: '模型分析失败',
                },
              }
            : {
                success: true,
                data: { status: 'completed', current_step: 'Complete', message: 'Done' },
              },
      ),
      queryVideo: vi.fn(async () => ({ success: true, data: { status: 'processing' } })),
      query: vi.fn(async () => ({
        success: true,
        data: { answer: '视频中出现了一辆汽车。' },
      })),
      healthCheck: vi.fn(async () => ({ success: true })),
      initialize: vi.fn(async () => ({ success: true })),
      listIndexed: vi.fn(async () => ({ success: true, data: [] })),
      sessionStatus: vi.fn(async () => ({ success: true, data: {} })),
      getVideoDuration: vi.fn(async () => ({
        success: true,
        duration: 10,
        fps: 30,
        width: 1920,
        height: 1080,
      })),
      deleteSession: vi.fn(async () => ({ success: true })),
      serviceStatus: vi.fn(async () => ({ success: true, isRunning: true })),
    },
    selectVideoFiles: vi.fn(async () => ({
      success: true,
      files: [
        { name: 'sample-a.mp4', path: 'C:/fixtures/sample-a.mp4', size: 1024 * 1024 },
        { name: 'sample-b.mp4', path: 'C:/fixtures/sample-b.mp4', size: 2 * 1024 * 1024 },
      ].slice(0, videoCount),
    })),
    app: {
      restart: vi.fn(async () => ({ success: true })),
      clearConfig: vi.fn(async () => ({ success: true })),
    },
  }

  Object.defineProperty(window, 'api', {
    configurable: true,
    writable: true,
    value: api,
  })
  Object.defineProperty(window, 'electron', {
    configurable: true,
    writable: true,
    value: { process: { platform: 'win32' } },
  })
  window.location.hash = '#/'
  return api
}

async function boot(options: BootOptions = {}) {
  const api = installRendererApi(options)
  const user = userEvent.setup()
  render(<App />)

  if (options.initialized ?? true) {
    await screen.findByText(/Welcome, it's/)
    const toggle = screen.getByRole('button', { name: 'Toggle' })
    await user.click(toggle)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Choose Videos' })).toBeEnabled())
  }
  return { api, user }
}

/*
Test Item 测试项：InitializationWizard 完成首次配置
Test Type：场景法
Test Criticality 重要级别：High
Pre-condition 预置条件：应用尚未初始化，模型文件已经存在
Input 输入：存储目录 C:/VimoTestData
Procedure 操作步骤：选择目录，依次完成模型、API Key 和完成页面
Output 预期结果：保存配置并进入应用主页
*/
test('01 初始化向导可以完成首次配置', async () => {
  const { api, user } = await boot({ initialized: false })
  await screen.findByText('Select Storage Location')
  await user.click(screen.getByRole('button', { name: 'Select' }))
  await user.click(screen.getByRole('button', { name: 'Next' }))
  await screen.findByText('AI Models Status')
  await screen.findByRole('button', { name: 'Completed' }, { timeout: 2_000 })
  await user.click(screen.getByRole('button', { name: 'Next' }))
  await screen.findByText('API Key Configuration')
  await user.click(screen.getByRole('button', { name: 'Complete Setup' }))
  await screen.findByText(/Setup Complete!/) 
  await user.click(screen.getByRole('button', { name: 'Start Using Vimo' }))

  await screen.findByText(/Welcome, it's/)
  expect(api.saveSettings).toHaveBeenCalledOnce()
})

/*
Test Item 测试项：useVideoUpload 拦截重复视频
Test Type：等价类划分（重复文件等价类）
Test Criticality 重要级别：High
Pre-condition 预置条件：服务与 ImageBind 已加载
Input 输入：连续两次选择同一个 sample-a.mp4
Procedure 操作步骤：点击两次 Choose Videos
Output 预期结果：只保留一个视频并显示重复提示
*/
test('02 上传视频并拦截重复上传', async () => {
  const { user } = await boot({ videoCount: 1 })
  await user.click(screen.getByRole('button', { name: 'Choose Videos' }))
  await screen.findByText('1 Video Selected')
  expect(screen.getByText('sample-a.mp4')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Choose Videos' }))

  await screen.findByText(/has already been added and will not be duplicated/)
  expect(screen.getAllByText('sample-a.mp4')).toHaveLength(1)
})

/*
Test Item 测试项：视频分析完成状态
Test Type：场景法
Test Criticality 重要级别：High
Pre-condition 预置条件：服务可用且已选择两个视频
Input 输入：sample-a.mp4、sample-b.mp4
Procedure 操作步骤：选择视频并启动分析，模拟后端返回 completed
Output 预期结果：页面显示两个视频分析完成
*/
test('03 开始分析后进入完成状态', async () => {
  const { user } = await boot()
  await user.click(screen.getByRole('button', { name: 'Choose Videos' }))
  await user.click(await screen.findByRole('button', { name: 'Start Analysis' }))

  await screen.findByText(/2 Videos Analyzed/, undefined, { timeout: 10_000 })
})

/*
Test Item 测试项：分析完成后的问答流程
Test Type：场景法
Test Criticality 重要级别：High
Pre-condition 预置条件：视频分析已经完成
Input 输入：视频中出现了什么？
Procedure 操作步骤：输入问题并按 Enter，模拟查询完成状态
Output 预期结果：页面显示模型返回的视频回答
*/
test('04 分析完成后可以发送问题并收到回答', async () => {
  const { user } = await boot()
  await user.click(screen.getByRole('button', { name: 'Choose Videos' }))
  await user.click(await screen.findByRole('button', { name: 'Start Analysis' }))
  await screen.findByText(/2 Videos Analyzed/, undefined, { timeout: 10_000 })

  const input = screen.getByPlaceholderText('Ask me anything about your videos...')
  await user.type(input, '视频中出现了什么？{Enter}')

  await screen.findByText('视频中出现了一辆汽车。', undefined, { timeout: 10_000 })
})

/*
Test Item 测试项：视频分析失败反馈
Test Type：场景法（异常场景）
Test Criticality 重要级别：High
Pre-condition 预置条件：服务可用且视频已选择
Input 输入：后端返回 error 和“模型分析失败”
Procedure 操作步骤：启动分析并等待错误状态处理
Output 预期结果：页面向用户显示 Analysis Failed
*/
test('05 分析失败后显示错误反馈', async () => {
  const { user } = await boot({ analysisFailure: true })
  await user.click(screen.getByRole('button', { name: 'Choose Videos' }))
  await user.click(await screen.findByRole('button', { name: 'Start Analysis' }))

  await screen.findByText(/Analysis Failed/, undefined, { timeout: 10_000 })
})
