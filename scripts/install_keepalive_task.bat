@echo off
REM ============================================================
REM CNPI Hybrid RAG — Windows Task Scheduler Setup
REM ============================================================
REM Run this script ONCE as Administrator to install the keep-alive task.
REM It pings Render every 14 minutes so the free-tier never sleeps.
REM ============================================================

set TASK_NAME=CNPI-KeepAlive
set SCRIPT_PATH=G:\CNPI_Hybrid_RAG\scripts\keep_alive.ps1
set INTERVAL_MIN=14

echo ============================================================
echo  Installing Task Scheduler job: %TASK_NAME%
echo  Interval : every %INTERVAL_MIN% minutes
echo  Script   : %SCRIPT_PATH%
echo ============================================================

REM Delete existing task (ignore error if not found)
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Create new task running as SYSTEM (no login required)
schtasks /create ^
  /tn  "%TASK_NAME%" ^
  /tr  "powershell -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File \"%SCRIPT_PATH%\"" ^
  /sc  MINUTE ^
  /mo  %INTERVAL_MIN% ^
  /ru  SYSTEM ^
  /rl  HIGHEST ^
  /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Task "%TASK_NAME%" created successfully.
    echo.
    schtasks /query /tn "%TASK_NAME%"
) else (
    echo.
    echo [ERROR] Failed to create task. Run this script as Administrator.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  To check logs : type G:\CNPI_Hybrid_RAG\logs\keep_alive.log
echo  To remove task: schtasks /delete /tn "%TASK_NAME%" /f
echo ============================================================
pause
