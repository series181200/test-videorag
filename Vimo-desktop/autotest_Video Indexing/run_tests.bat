@echo off
setlocal
cd /d "%~dp0.."
python -m pytest -c "autotest_Video Indexing\pytest.ini" "autotest_Video Indexing" --basetemp "output\pytest_tmp_video_indexing"
endlocal
