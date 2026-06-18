@echo off
setlocal
cd /d "%~dp0.."
"backend\.venv\Scripts\python.exe" "infra\pacs\viewer_server.py" --port 8080 --orthanc http://localhost:8042
