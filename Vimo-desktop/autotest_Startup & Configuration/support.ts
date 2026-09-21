import path from 'node:path'
import { constants } from 'node:fs'

const boundaryMocks = vi.hoisted(() => ({
  handle: vi.fn(), axios: vi.fn(), spawn: vi.fn(), existsSync: vi.fn(),
  readFile: vi.fn(), writeFile: vi.fn(), access: vi.fn(), mkdir: vi.fn(),
  unlink: vi.fn(), open: vi.fn(), fetch: vi.fn(),
}))
vi.mock('electron', () => ({ ipcMain: { handle: boundaryMocks.handle }, app: {} }))
vi.mock('axios', () => ({ default: Object.assign(boundaryMocks.axios, {
  get: boundaryMocks.axios, post: boundaryMocks.axios, request: boundaryMocks.axios,
}) }))
vi.mock('child_process', () => ({ spawn: boundaryMocks.spawn }))
vi.mock('fs', async importOriginal => {
  const actual = await importOriginal<typeof import('node:fs')>()
  return { ...actual, existsSync: boundaryMocks.existsSync,
    default: { ...actual, existsSync: boundaryMocks.existsSync } }
})
vi.mock('node:fs/promises', () => ({
  readFile: boundaryMocks.readFile, writeFile: boundaryMocks.writeFile, access: boundaryMocks.access,
  mkdir: boundaryMocks.mkdir, unlink: boundaryMocks.unlink, open: boundaryMocks.open,
}))
export const mocks = boundaryMocks

export const STORE = path.resolve('/sc-fixture/store')
export const validSettings = () => ({
  storeDirectory: STORE,
  openaiApiKey: 'sk-fixture-openai', dashscopeApiKey: 'fixture-dashscope',
})
export const files = new Map<string, string>()
export const handlers = new Map<string, (...args: any[]) => Promise<any>>()
export const permissions = { modelMissing: false, storeReadOnly: false }
const fileError = (code: string, file: string) => Object.assign(new Error(`${code}: ${file}`), { code })
const key = (file: unknown) => path.normalize(String(file))
const isStore = (file: unknown) => key(file) === STORE || key(file).startsWith(STORE + path.sep)

export function setConfiguration(settings: Record<string, unknown> = validSettings()) {
  files.clear()
  // Match both production loaders, which locate this file using the actual homedir.
  files.set('bootstrap', JSON.stringify({ storeDirectory: settings.storeDirectory }))
  files.set(path.join(STORE, 'config.json'), JSON.stringify(settings))
}

export function handler(channel: string) {
  const callback = handlers.get(channel)
  if (!callback) throw new Error(`Unregistered production IPC handler: ${channel}`)
  return (...args: any[]) => callback({}, ...args)
}

export async function loadApplication() {
  const service = await import('../src/main/handlers/videorag-handlers')
  const settings = await import('../src/main/handlers/settings')
  service.setupVideoRAGHandlers()
  settings.registerSettingsHandlers()
  return service
}

export function observe<T>(promise: Promise<T>) {
  const state: { status: 'pending' | 'fulfilled' | 'rejected'; value?: T; error?: Error } = { status: 'pending' }
  // Attach both handlers immediately: expected rejection must never be unhandled.
  void promise.then(value => { state.status = 'fulfilled'; state.value = value },
    error => { state.status = 'rejected'; state.error = error })
  return state
}

export const initializationCalls = () => mocks.axios.mock.calls.filter(
  ([config]) => typeof config === 'object' && config.url?.endsWith('/initialize'),
)
export const healthCalls = () => mocks.axios.mock.calls.filter(
  ([config]) => typeof config === 'object' && config.url?.endsWith('/health'),
)

let resourceDescriptor: PropertyDescriptor | undefined
beforeEach(() => {
  vi.resetModules()
  Object.values(mocks).forEach(mock => mock.mockReset())
  handlers.clear()
  permissions.modelMissing = false
  permissions.storeReadOnly = false
  setConfiguration()
  vi.useFakeTimers()
  vi.stubEnv('NODE_ENV', 'development')
  vi.stubGlobal('fetch', mocks.fetch)
  resourceDescriptor = Object.getOwnPropertyDescriptor(process, 'resourcesPath')
  Object.defineProperty(process, 'resourcesPath', { configurable: true, value: path.resolve('/sc-fixture/resources') })
  mocks.handle.mockImplementation((channel, callback) => handlers.set(channel, callback))
  mocks.existsSync.mockReturnValue(true)
  mocks.spawn.mockImplementation(() => {
    const child = {
      killed: false, stdout: { on: vi.fn() }, stderr: { on: vi.fn() }, on: vi.fn(),
      kill: vi.fn(() => { child.killed = true; return true }),
    }
    return child
  })
  mocks.readFile.mockImplementation(async file => {
    const name = key(file).endsWith('.videorag-bootstrap.json') ? 'bootstrap' : key(file)
    if (!files.has(name)) throw fileError('ENOENT', String(file))
    return files.get(name)
  })
  mocks.access.mockImplementation(async (file, mode = constants.F_OK) => {
    if (permissions.modelMissing && key(file).endsWith('imagebind_huge.pth')) throw fileError('ENOENT', String(file))
    if (permissions.storeReadOnly && isStore(file) && (mode & constants.W_OK)) throw fileError('EACCES', String(file))
  })
  mocks.writeFile.mockImplementation(async (file, contents) => {
    if (permissions.storeReadOnly && isStore(file)) throw fileError('EACCES', String(file))
    files.set(key(file).endsWith('.videorag-bootstrap.json') ? 'bootstrap' : key(file), String(contents))
  })
  mocks.mkdir.mockImplementation(async file => {
    if (permissions.storeReadOnly && isStore(file)) throw fileError('EACCES', String(file))
  })
  mocks.open.mockImplementation(async (file, flags = 'r') => {
    if (permissions.storeReadOnly && isStore(file) && /[wa+]/.test(String(flags))) throw fileError('EACCES', String(file))
    return { close: vi.fn(), writeFile: vi.fn() }
  })
  mocks.unlink.mockResolvedValue(undefined)
  mocks.axios.mockImplementation(async config => {
    if (config.url?.endsWith('/health')) return { data: { status: 'ok' } }
    if (config.url?.endsWith('/initialize')) return { data: { success: true } }
    throw new Error(`Unexpected mocked HTTP request: ${config.url}`)
  })
  mocks.fetch.mockRejectedValue(new Error('Unexpected fetch: live network is disabled'))
})

afterEach(() => {
  // Pending startup promises have no real timers/handles after cleanup.
  vi.clearAllTimers()
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  if (resourceDescriptor) Object.defineProperty(process, 'resourcesPath', resourceDescriptor)
  else delete (process as any).resourcesPath
})
