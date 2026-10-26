@echo off
setlocal
cd /d "%~dp0"
call conda activate pytorch_gpu
if errorlevel 1 goto :error
python scripts\prepare_runtime_assets.py --source "E:\crypto-rt-analytics"
if errorlevel 1 goto :error
echo.
echo Runtime assets are ready.
pause
exit /b 0
:error
echo.
echo Runtime asset preparation failed. Review the error above.
pause
exit /b 1
