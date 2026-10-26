@echo off
cd /d "%~dp0"
call conda activate pytorch_gpu
set API_BASE_URL=http://127.0.0.1:8000
streamlit run app\main.py
pause
