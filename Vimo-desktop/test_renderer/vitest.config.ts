import { resolve } from 'node:path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  root: resolve(__dirname, '..'),
  esbuild: {
    jsx: 'automatic',
  },
  resolve: {
    alias: {
      '@radix-ui/react-slot': resolve(__dirname, 'node_modules/@radix-ui/react-slot'),
      'class-variance-authority': resolve(__dirname, 'node_modules/class-variance-authority'),
      clsx: resolve(__dirname, 'node_modules/clsx'),
      'lucide-react': resolve(__dirname, 'node_modules/lucide-react'),
      react: resolve(__dirname, 'node_modules/react'),
      'react-dom': resolve(__dirname, 'node_modules/react-dom'),
      'react-router': resolve(__dirname, 'node_modules/react-router'),
      sonner: resolve(__dirname, 'node_modules/sonner'),
      'tailwind-merge': resolve(__dirname, 'node_modules/tailwind-merge'),
    },
  },
  test: {
    include: ['test_renderer/**/*.test.tsx'],
    environment: 'jsdom',
    setupFiles: ['test_renderer/setup.ts'],
    clearMocks: true,
    restoreMocks: true,
    testTimeout: 15_000,
    hookTimeout: 15_000,
    pool: 'forks',
    poolOptions: {
      forks: { singleFork: true },
    },
  },
})
