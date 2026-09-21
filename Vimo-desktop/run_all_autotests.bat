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
    echo [ERROR] 未找到 Python。请激活 vimo 环境，或通过 VIMO_TEST_PYTHON 指定 python.exe。
    echo.
    pause
    exit /b 2
)

echo ================================================================
echo Vimo 第二阶段四组自动化测试
echo SC 启动与配置 / SR 状态与恢复 / VI 视频索引 / VQ 视频查询
echo ================================================================

"%PYTHON_EXE%" %PYTHON_ARGS% run_all_autotests.py
set "FINAL_RESULT=%ERRORLEVEL%"

echo.
if "%FINAL_RESULT%"=="0" (
    echo [OK] 四组测试全部通过
) else if "%FINAL_RESULT%"=="1" (
    echo [NG] 测试发现失败项，请查看上方对应测试组输出
) else (
    echo [ERROR] 测试环境或运行器异常，请查看上方错误信息
)

echo.
if /I not "%VIMO_TEST_NO_PAUSE%"=="1" pause
exit /b %FINAL_RESULT%
