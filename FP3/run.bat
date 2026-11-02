@echo off
cd /d "%~dp0"
rem Use this folder's environment (made by install.bat); otherwise fall back to the shared one in v1
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    "..\v1\.venv\Scripts\python.exe" main.py
)
pause
