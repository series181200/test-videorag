import { files, handler, initializationCalls, loadApplication, mocks, permissions, setConfiguration, validSettings } from './support'

it.each(['damaged-json', 'storeDirectory', 'openaiApiKey', 'dashscopeApiKey'])(
  'TC-SC-003 / %s blocks initialization and can be repaired in the same application', async field => {
    const settings: Record<string, unknown> = validSettings()
    if (field === 'damaged-json') files.set('bootstrap', '{"storeDirectory":')
    else { delete settings[field]; setConfiguration(settings) }
    await loadApplication()
    await handler('load-settings')()
    const invalid = await handler('videorag:reinitialize-config')()
    expect(invalid.success).toBe(false)
    expect(invalid.error).toMatch(/configuration|settings|missing/i)
    expect(initializationCalls()).toHaveLength(0)
    expect(mocks.spawn).not.toHaveBeenCalled()
    // Repair through the real settings handler, without reloading application modules.
    expect(await handler('save-settings')(validSettings())).toMatchObject({ success: true })
    expect(await handler('load-settings')()).toMatchObject({ success: true, settings: validSettings() })
    expect(await handler('videorag:reinitialize-config')()).toMatchObject({ success: true })
    expect(initializationCalls()).toHaveLength(1)
    expect(initializationCalls()[0][0].data.base_storage_path).toBe(validSettings().storeDirectory)
  },
)

it.each(['missing-model', 'read-only-storage'])(
  'TC-SC-005 / %s fails before backend initialization and succeeds after repair', async fault => {
    permissions.modelMissing = fault === 'missing-model'
    permissions.storeReadOnly = fault === 'read-only-storage'
    await loadApplication()
    const invalid = await handler('videorag:reinitialize-config')()
    expect.soft(invalid.success, 'Resources must be usable before reporting initialized').toBe(false)
    expect.soft(String(invalid.error)).toMatch(fault === 'missing-model' ? /model|imagebind/i : /storage|permission|writ|EACCES/i)
    expect.soft(initializationCalls(), 'Invalid resources must not reach /initialize').toHaveLength(0)
    expect(mocks.spawn).not.toHaveBeenCalled()
    permissions.modelMissing = false
    permissions.storeReadOnly = false
    mocks.axios.mockClear()
    expect(await handler('videorag:reinitialize-config')()).toMatchObject({ success: true })
    expect(initializationCalls()).toHaveLength(1)
  },
)
