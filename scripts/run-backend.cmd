@echo off
setlocal
cd /d "%~dp0..\backend"
set AUTO_DB_BOOTSTRAP=false
set PYTHONPATH=.
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload
