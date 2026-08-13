@echo off
REM ====================
REM Server Heartbeat Cron Job
REM ====================
REM This script sends a heartbeat ping to the server every 10 minutes.
REM Usage: Copy this file to a directory accessible by your cron system,
REM        modify the HEARTBEAT_URL below, and add it to your crontab.

set HEARTBEAT_URL=http://localhost:8000/api/health
set VENV_PATH=C:\Users\hmaru\.virtualenvs\cnpi-api
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe
set PROJECT_DIR=G:\CNPI_Hybrid_RAG\cnpi_api

echo [%date% %time%] Sending heartbeat to: %HEARTBEAT_URL%

"%PYTHON_EXE%" -c "import requests; import time; requests.get('%HEARTBEAT_URL%')" >nul 2>&1

echo [%date% %time%] Heartbeat completed.