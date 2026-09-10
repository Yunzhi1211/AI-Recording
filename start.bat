@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist config.json if exist "assets\config.template.json" copy /Y "assets\config.template.json" config.json >nul
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe 05_qt_app.py
) else (
  python 05_qt_app.py
)
if errorlevel 1 pause
