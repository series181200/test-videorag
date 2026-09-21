const fs = require('node:fs')
const path = require('node:path')
const crypto = require('node:crypto')
const { spawnSync, execFileSync } = require('node:child_process')

const root = __dirname
const expected = { 'TC-SC-001': 1, 'TC-SC-002': 1, 'TC-SC-003': 1, 'TC-SC-004': 1, 'TC-SC-005': 1 }
let vitestPackage
try {
  vitestPackage = require.resolve('vitest/package.json', { paths: [root, path.resolve(root, '../test_communication')] })
} catch {
  console.error('缺少 Vitest。请执行 npm.cmd install --prefix Vimo-desktop/test_startup_configuration')
  process.exit(2)
}
const version = JSON.parse(fs.readFileSync(vitestPackage, 'utf8')).version
if (version !== '2.1.9') {
  console.error(`需要 Vitest 2.1.9，当前解析到 ${version}。请安装本目录 package.json 中的依赖。`)
  process.exit(2)
}
const stamp = new Date().toISOString().replace(/[:.]/g, '-')
const output = path.join(root, 'results', `${stamp}-${process.pid}`)
fs.mkdirSync(output, { recursive: true })
const repository = path.resolve(root, '../..')
function git(...args) {
  try {
    return execFileSync('git', ['-c', `safe.directory=${repository.replaceAll('\\', '/')}`, ...args],
      { cwd: repository, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
  } catch { return null }
}
const sourcePaths = ['src/main/handlers/settings.ts', 'src/main/handlers/videorag-handlers.ts']
const hashFile = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')
const manifest = {
  startedAt: new Date().toISOString(), node: process.version, platform: process.platform,
  vitest: version, vitestPackage, commit: git('rev-parse', 'HEAD'),
  workingTree: git('status', '--short'),
  scope: 'one representative functional sample per business ID; no fixed retry-count SLA',
  sources: sourcePaths.map(relative => {
    const absolute = path.resolve(root, '..', relative)
    return { path: relative, sha256: hashFile(absolute) }
  }),
  tests: fs.readdirSync(root).filter(file => /\.(ts|cjs|json)$/.test(file)).map(file => ({
    path: file, sha256: hashFile(path.join(root, file)),
  })),
}
fs.writeFileSync(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2))
const result = spawnSync(process.execPath, [
  path.join(path.dirname(vitestPackage), 'vitest.mjs'), 'run',
  '--config', path.join(root, 'vitest.config.ts'),
  '--reporter=verbose', '--reporter=json',
  `--outputFile.json=${path.join(output, 'vitest.json')}`,
], { cwd: root, encoding: 'utf8', timeout: 120000, maxBuffer: 10 * 1024 * 1024, env: { ...process.env, NO_COLOR: '1' } })
fs.writeFileSync(path.join(output, 'console.txt'), (result.stdout || '') + (result.stderr || '') + (result.error ? String(result.error) : ''))
let report
try { report = JSON.parse(fs.readFileSync(path.join(output, 'vitest.json'), 'utf8')) } catch {}
const assertions = report?.testResults?.flatMap(suite => suite.assertionResults || []) || []
// Vitest 2.1.9's JUnit reporter adds process listeners for each soft failure.
// Derive JUnit from the retained JSON to avoid its MaxListenersExceededWarning.
const xml = value => String(value).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&apos;')
const rows = Object.entries(expected).map(([id, count]) => {
  const checks = assertions.filter(test => (test.fullName || test.title).includes(id))
  const passed = checks.filter(test => test.status === 'passed').length
  const failed = checks.filter(test => test.status === 'failed').length
  return { id, expected: count, collected: checks.length, passed, failed,
    status: checks.length !== count ? 'ERROR' : failed ? 'FAIL' : passed === count ? 'PASS' : 'INCOMPLETE',
    checks: checks.map(test => ({ name: test.fullName || test.title, status: test.status, messages: test.failureMessages || [] })),
  }
})
const infrastructureError = Boolean(result.error || !report || report.numRuntimeErrorTestSuites > 0
  || report.unhandledErrors?.length || rows.some(row => row.status === 'ERROR')
  || assertions.length !== Object.values(expected).reduce((a, b) => a + b, 0))
const exitCode = infrastructureError ? 2 : rows.every(row => row.status === 'PASS') && result.status === 0 ? 0 : 1
const summary = {
  finishedAt: new Date().toISOString(), exitCode, infrastructureError,
  executed: assertions.length, passed: assertions.filter(test => test.status === 'passed').length,
  failed: assertions.filter(test => test.status === 'failed').length, businessCases: rows,
}
const elements = assertions.map(test => {
  const detail = test.status === 'failed' ? `<failure>${xml((test.failureMessages || []).join('\n'))}</failure>`
    : test.status === 'passed' ? '' : '<skipped/>'
  return `<testcase classname="StartupConfiguration" name="${xml(test.fullName || test.title)}" time="${(test.duration || 0) / 1000}">${detail}</testcase>`
})
if (infrastructureError) elements.push('<testcase name="runner-infrastructure"><error>See console.txt and vitest.json</error></testcase>')
fs.writeFileSync(path.join(output, 'junit.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<testsuites><testsuite name="SC" tests="${elements.length}" failures="${summary.failed}" errors="${infrastructureError ? 1 : 0}" skipped="${assertions.filter(test => !['passed', 'failed'].includes(test.status)).length}">${elements.join('\n')}</testsuite></testsuites>\n`)
fs.writeFileSync(path.join(output, 'summary.json'), JSON.stringify(summary, null, 2))
fs.writeFileSync(path.join(output, 'summary.csv'), '\ufeffID,Status,Expected,Collected,Passed,Failed\n' + rows.map(
  row => [row.id, row.status, row.expected, row.collected, row.passed, row.failed].join(','),
).join('\n'))
for (const row of rows) console.log(`${row.id} ${row.status} (${row.passed}/${row.expected} checks passed)`)
console.log(`Checks: ${summary.executed}; passed: ${summary.passed}; failed: ${summary.failed}`)
console.log(`Reports: ${output}`)
if (infrastructureError) console.error('测试环境、收集或运行异常，请查看 console.txt 和 vitest.json。')
process.exitCode = exitCode
