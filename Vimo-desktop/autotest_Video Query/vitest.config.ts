import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { existsSync } from 'node:fs'

const require = createRequire(import.meta.url)
// Resolve the renderer dependencies from one installation, not per-package
// fallback through the application's node_modules (which creates two Reacts).
const dependencyRoot = existsSync(resolve(__dirname, 'node_modules/react/package.json'))
  ? __dirname : resolve(__dirname, '../test_renderer')
const packageRoot = (name: string) => dirname(require.resolve(name + '/package.json', { paths: [dependencyRoot] }))
export default {
  root: __dirname,
  esbuild: { jsx: 'automatic' },
  resolve: {
    alias: Object.fromEntries(['react', 'react-dom', 'react-router', '@testing-library/react'].map(
      name => [name, packageRoot(name)],
    )),
    dedupe: ['react', 'react-dom'],
  },
  test: {
    globals: true,
    include: ['query_*.test.tsx'],
    setupFiles: ['./renderer_support.tsx'],
    environment: 'jsdom',
    pool: 'forks',
    maxWorkers: 1, minWorkers: 1,
    testTimeout: 10000,
    onConsoleLog: () => false,
  },
}
