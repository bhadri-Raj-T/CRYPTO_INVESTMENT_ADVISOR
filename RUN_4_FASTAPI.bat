@echo off
cd /d "%~dp0"
call conda activate pytorch_gpu
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
pause
