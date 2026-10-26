@echo off
cd /d "%~dp0"
call conda activate pytorch_gpu
set RTA_INFERENCE_DEVICE=cpu
python -m streaming.spark_session
pause
