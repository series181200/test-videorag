import { resolve } from 'node:path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  root: resolve(__dirname, '..'),
  test: {
    include: ['test_communication/**/*.test.ts'],
    environment: 'node',
    clearMocks: true,
    restoreMocks: true,
    testTimeout: 5_000,
  },
})
