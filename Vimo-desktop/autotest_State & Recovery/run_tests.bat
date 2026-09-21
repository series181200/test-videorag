@echo off
setlocal
cd /d "%~dp0.."
python -m pytest -c "autotest_State & Recovery\pytest.ini" "autotest_State & Recovery" --basetemp "output\pytest_tmp_state_recovery"
endlocal
