@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist "test_renderer\node_modules\.bin\vitest.cmd" (
    echo [准备] 首次安装 renderer Vitest 测试依赖...
    call npm.cmd install --prefix test_renderer
    if errorlevel 1 (
        echo [NG] renderer 测试依赖安装失败。
        pause
        exit /b 2
    )
)

call test_renderer\node_modules\.bin\vitest.cmd run --config test_renderer\vitest.config.ts --reporter=verbose
set "FINAL_RESULT=%ERRORLEVEL%"

echo.
if "%FINAL_RESULT%"=="0" (
    echo [OK] renderer Vitest 测试全部通过。
) else (
    echo [NG] renderer Vitest 测试发现失败项。
)
pause
exit /b %FINAL_RESULT%
