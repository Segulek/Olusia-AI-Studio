@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Olusia AI Studio - Local Windows app
if not exist ".venv-core\Scripts\python.exe" (
  echo First run 1_INSTALL_WINDOWS.bat
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg not found. Rerun 1_INSTALL_WINDOWS.bat.
  pause
  exit /b 1
)
echo.
echo Olusia AI Studio is starting at http://127.0.0.1:8501
echo This application is only accessible on this PC.
echo Keep this window open. Press Ctrl+C to close the application.
echo.
".venv-core\Scripts\python.exe" -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501 --browser.gatherUsageStats=false
if errorlevel 1 (
  echo App exited with an error. See the messages above.
  pause
  exit /b 1
)
