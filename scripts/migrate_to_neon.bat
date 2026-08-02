@echo off
REM ============================================================
REM  CNPI RAG -> Neon Migration (CMD wrapper)
REM  Run: scripts\migrate_to_neon.bat
REM ============================================================
powershell -ExecutionPolicy Bypass -File "%~dp0migrate_to_neon.ps1"
pause
