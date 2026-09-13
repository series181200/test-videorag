@echo off
cd /d "%~dp0"

REM Go to the project root, since the app and package.json are one level above this folder.
cd ..

REM 1. Install JavaScript dependencies without downloading the Electron binary.
REM The renderer tests run against the built web page and do not need Electron's postinstall download.
call npm.cmd install --ignore-scripts
if errorlevel 1 (
    echo.
    echo [ERROR] npm install failed.
    pause
    exit /b 1
)

REM 2. Build app
call npm.cmd run build
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

REM 3. Install Playwright browser
call npx.cmd playwright install chromium
if errorlevel 1 (
    echo.
    echo [ERROR] Playwright browser install failed.
    pause
    exit /b 1
)

REM 4. Run frontend tests from this test directory.
call node_modules\.bin\playwright.cmd test -c test_renderer\playwright.config.ts
if errorlevel 1 (
    echo.
    echo [ERROR] Frontend test failed.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Frontend tests completed.
pause
