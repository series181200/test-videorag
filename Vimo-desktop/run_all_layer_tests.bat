@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if defined VIMO_TEST_PYTHON set "PYTHON_EXE=%VIMO_TEST_PYTHON%"
if not defined PYTHON_EXE if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" set "PYTHON_EXE=%CONDA_PREFIX%\python.exe"

if not defined PYTHON_EXE (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    ) else if exist "C:\ProgramData\miniconda3\python.exe" (
        set "PYTHON_EXE=C:\ProgramData\miniconda3\python.exe"
    ) else (
        where py >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=py"
            set "PYTHON_ARGS=-3"
        )
    )
)

if not defined PYTHON_EXE (
    echo [NG] 未找到 Python。请安装 Python，或通过 VIMO_TEST_PYTHON 指定 python.exe。
    echo.
    pause
    exit /b 2
)

echo ================================================================
echo Vimo 四层统一测试
echo ================================================================
echo.

"%PYTHON_EXE%" %PYTHON_ARGS% run_all_layer_tests.py
set "FINAL_RESULT=%ERRORLEVEL%"

echo.
if "%FINAL_RESULT%"=="0" (
    echo [OK] 全部测试通过
) else (
    echo [NG] 测试中发现失败项，请查看上方逐条结果
)

echo.
pause
exit /b %FINAL_RESULT%
