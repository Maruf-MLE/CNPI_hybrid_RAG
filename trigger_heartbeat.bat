@echo off
REM ====================
REM Simple Heartbeat Trigger Script
REM ====================
REM This script triggers a Django management command to send heartbeat.
REM Run this manually or via your task scheduler.

set VENV_PATH=C:\Users\hmaru\.virtualenvs\cnpi-api
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe
set PROJECT_DIR=G:\CNPI_Hybrid_RAG\cnpi_api

echo [Heartbeat] Triggered at %date% %time%

cd /d "%PROJECT_DIR%"
%PYTHON_EXE% manage.py heartbeat

echo [Heartbeat] Completed at %date% %time%