export default {
  root: __dirname,
  test: {
    globals: true,
    include: ['*.test.ts'],
    setupFiles: ['./support.ts'],
    environment: 'node',
    pool: 'forks',
    maxWorkers: 1,
    minWorkers: 1,
    testTimeout: 5000,
    hookTimeout: 10000,
    onConsoleLog: () => false,
  },
}
