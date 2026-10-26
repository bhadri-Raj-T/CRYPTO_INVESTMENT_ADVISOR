@echo off
cd /d E:\RTA_RUNTIME_V4
call conda activate pytorch_gpu
python scripts\prepare_dashboard_history.py --source "E:\crypto-rt-analytics" --days 30 --mode auto
pause
