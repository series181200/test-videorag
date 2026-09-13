import { test, expect, type Page } from '@playwright/test';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

const rendererFile = resolve(__dirname, '../dist/renderer/index.html');

type BootOptions = {
  initialized?: boolean;
  storedSessions?: Record<string, unknown>;
  videoCount?: 1 | 2;
  analysisFailure?: boolean;
};

async function boot(page: Page, options: BootOptions = {}) {
  const initialized = options.initialized ?? true;
  const storedSessions = options.storedSessions ?? {};
  const videoCount = options.videoCount ?? 2;
  const analysisFailure = options.analysisFailure ?? false;

  await page.addInitScript(({ initialized, storedSessions, videoCount, analysisFailure }) => {
    const sessions = { ...storedSessions } as Record<string, any>;
    const settings = initialized
      ? {
          storeDirectory: 'C:/VimoTestData',
          imagebindInstalled: true,
          openaiBaseUrl: 'https://api.openai.com/v1',
          processingModel: 'gpt-4o-mini',
          analysisModel: 'gpt-4o-mini',
        }
      : {};

    const saveSession = (id: string, patch: any) => {
      sessions[id] = { ...(sessions[id] || {}), ...patch, id };
      return { success: true };
    };

    (window as any).api = {
      loadSettings: async () => ({ success: true, settings }),
      saveSettings: async (nextSettings: any) => {
        Object.assign(settings, nextSettings);
        return { success: true };
      },
      selectFolder: async () => ({ success: true, path: 'C:/VimoTestData' }),
      checkModelFiles: async () => ({ imagebind: true }),
      downloadImageBind: async () => ({ success: true }),
      onDownloadProgress: () => undefined,
      removeDownloadListeners: () => undefined,
      chatSessions: {
        load: async (id: string) => ({ success: true, session: sessions[id] }),
        save: async (id: string, data: any) => saveSession(id, data),
        list: async () => ({ success: true, sessions: Object.values(sessions) }),
        delete: async (id: string) => {
          delete sessions[id];
          return { success: true };
        },
        getStorageInfo: async () => ({ success: true, storeDirectory: 'C:/VimoTestData', isConfigured: true }),
        ensureStorageDirectory: async () => ({ success: true }),
        updateSessionOrder: async () => ({ success: true }),
      },
      videorag: {
        systemStatus: async () => ({ success: true, data: { total_sessions: 0, global_config_set: true, imagebind_loaded: true } }),
        imagebindStatus: async () => ({ success: true, data: { loaded: true } }),
        startService: async () => ({ success: true }),
        stopService: async () => ({ success: true }),
        loadImageBind: async () => ({ success: true }),
        releaseImageBind: async () => ({ success: true }),
        reinitializeConfig: async () => ({ success: true }),
        uploadVideo: async (id: string) => {
          saveSession(id, { analysisState: 'analyzing' });
          return { success: true, data: { status: 'processing' } };
        },
        getStatus: async (_id: string, type?: string) =>
          type === 'query'
            ? { success: true, data: { status: 'completed', answer: '视频中出现了一辆汽车。' } }
            : analysisFailure
              ? { success: true, data: { status: 'error', current_step: 'Analyze', message: '模型分析失败' } }
              : { success: true, data: { status: 'completed', current_step: 'Complete', message: 'Done' } },
        queryVideo: async () => ({ success: true, data: { status: 'processing' } }),
        query: async () => ({ success: true, data: { answer: '视频中出现了一辆汽车。' } }),
        healthCheck: async () => ({ success: true }),
        initialize: async () => ({ success: true }),
        listIndexed: async () => ({ success: true, data: [] }),
        sessionStatus: async () => ({ success: true, data: {} }),
        getVideoDuration: async () => ({ success: true, duration: 10, fps: 30, width: 1920, height: 1080 }),
        deleteSession: async () => ({ success: true }),
        serviceStatus: async () => ({ success: true, isRunning: true }),
      },
      selectVideoFiles: async () => ({
        success: true,
        files: [
          { name: 'sample-a.mp4', path: 'C:/fixtures/sample-a.mp4', size: 1024 * 1024 },
          { name: 'sample-b.mp4', path: 'C:/fixtures/sample-b.mp4', size: 2 * 1024 * 1024 },
        ].slice(0, videoCount),
      }),
      app: { restart: async () => ({ success: true }), clearConfig: async () => ({ success: true }) },
    };
  }, { initialized, storedSessions, videoCount, analysisFailure });

  await page.goto('/');
  if (initialized) {
    await expect(page.getByText("Welcome, it's")).toBeVisible();
    const serviceToggle = page.getByRole('button', { name: 'Toggle' });
    if (await serviceToggle.isVisible()) {
      await serviceToggle.click();
    }
  }
}

test.beforeAll(() => {
  if (!existsSync(rendererFile)) {
    throw new Error('未找到 dist/renderer/index.html，请先运行 pnpm build。');
  }
});

test('01 初始化向导可以完成首次配置', async ({ page }) => {
  await boot(page, { initialized: false });
  await expect(page.getByText('Select Storage Location')).toBeVisible();
  await page.getByRole('button', { name: 'Select' }).click();
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByText('AI Models Status')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Completed' })).toBeVisible({ timeout: 2_000 });
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByText('API Key Configuration')).toBeVisible();
  await page.getByRole('button', { name: 'Complete Setup' }).click();
  await expect(page.getByText('Setup Complete!')).toBeVisible();
  await page.getByRole('button', { name: 'Start Using Vimo' }).click();
  await expect(page.getByText("Welcome, it's")).toBeVisible();
});

test('02 上传视频并拦截重复上传', async ({ page }) => {
  await boot(page, { videoCount: 1 });
  await page.getByRole('button', { name: 'Choose Videos' }).click();
  await expect(page.getByText('1 Video Selected')).toBeVisible();
  await expect(page.getByText('sample-a.mp4')).toBeVisible();
  await page.getByRole('button', { name: 'Choose Videos' }).click();
  await expect(page.getByText(/has already been added and will not be duplicated/)).toBeVisible();
});

test('03 开始分析后进入完成状态', async ({ page }) => {
  await boot(page);
  await page.getByRole('button', { name: 'Choose Videos' }).click();
  await page.getByRole('button', { name: 'Start Analysis' }).click();
  await expect(page.getByText(/Video[s]? Analyzed/)).toBeVisible({ timeout: 10_000 });
});

test('04 分析完成后可以发送问题并收到回答', async ({ page }) => {
  await boot(page);
  await page.getByRole('button', { name: 'Choose Videos' }).click();
  await page.getByRole('button', { name: 'Start Analysis' }).click();
  await expect(page.getByText(/Video[s]? Analyzed/)).toBeVisible({ timeout: 10_000 });
  const input = page.getByPlaceholder('Ask me anything about your videos...');
  await input.fill('视频中出现了什么？');
  await input.press('Enter');
  await expect(page.getByRole('main').getByText('视频中出现了一辆汽车。')).toBeVisible({ timeout: 10_000 });
});

test('05 分析失败后显示错误反馈', async ({ page }) => {
  await boot(page, { analysisFailure: true });
  await page.getByRole('button', { name: 'Choose Videos' }).click();
  await page.getByRole('button', { name: 'Start Analysis' }).click();
  await expect(page.getByRole('main').getByText('Analysis Failed')).toBeVisible({ timeout: 10_000 });
});

