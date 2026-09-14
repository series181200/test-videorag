@echo off
setlocal

rem 默认使用已配置的 Conda Python 解释器。
set "PYTHON_EXE=D:\develop\conda_envs\langchain_env\python.exe"
if not exist "%PYTHON_EXE%" (
    echo [错误] 未找到 Python 解释器：
    echo         %PYTHON_EXE%
    echo.
    echo 请修改本文件中的 PYTHON_EXE 路径后重试。
    pause
    exit /b 2
)

cd /d "%~dp0"
echo ========================================
echo VideoRAG API 测试
echo ========================================
echo.

"%PYTHON_EXE%" run_tests.py
set "FINAL_RESULT=%ERRORLEVEL%"
echo.
if "%FINAL_RESULT%"=="0" (
    echo [通过] 全部测试通过。
) else (
    echo [失败] 测试发现业务缺陷，请查看上方报告。
)
pause
exit /b %FINAL_RESULT%
