@echo off
cd /d "%~dp0"
rem Uses the shared Python environment in v1 (no per-version install needed)
"..\v1\.venv\Scripts\python.exe" main.py
pause
