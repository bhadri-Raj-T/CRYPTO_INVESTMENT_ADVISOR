@echo off
cd /d "%~dp0"
call conda activate pytorch_gpu
python -m producer.run_producer
pause
