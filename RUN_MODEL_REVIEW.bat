@echo off
cd /d "%~dp0"
call conda activate pytorch_gpu
streamlit run app\model_review.py
pause
