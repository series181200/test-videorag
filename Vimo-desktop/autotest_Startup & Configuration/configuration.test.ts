import { files, handler, loadApplication, permissions, validSettings } from './support'

it('TC-SC-003 / damaged configuration can be repaired and initialized again', async () => {
  files.set('bootstrap', '{"storeDirectory":')
  await loadApplication()
  const invalid = await handler('videorag:reinitialize-config')()
  expect(invalid.success).toBe(false)
  expect(invalid.error).toBeTruthy()
  // Correct and retry in the same running application.
  expect(await handler('save-settings')(validSettings())).toMatchObject({ success: true })
  expect(await handler('videorag:reinitialize-config')()).toMatchObject({ success: true })
})

it('TC-SC-005 / missing ImageBind model prevents initialization until restored', async () => {
  permissions.modelMissing = true
  await loadApplication()
  const invalid = await handler('videorag:reinitialize-config')()
  expect(invalid.success).toBe(false)
  expect(invalid.error).toBeTruthy()
  permissions.modelMissing = false
  expect(await handler('videorag:reinitialize-config')()).toMatchObject({ success: true })
})
