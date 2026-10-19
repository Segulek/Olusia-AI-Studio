@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Olusia AI Studio - Windows setup
echo.
echo ====================================================
echo   OLUSIA AI STUDIO - Windows installation
echo ====================================================
echo Python 3.11 x64, FFmpeg and basic local libraries.
echo Local AI model and Demucs are installed separately
echo to save disk space.
echo.

where py >nul 2>nul
if errorlevel 1 goto python_missing
py -3.11 -c "import platform,sys;assert sys.version_info[:2]==(3,11) and platform.architecture()[0]=='64bit'"
if errorlevel 1 goto python_missing

where ffmpeg >nul 2>nul
if errorlevel 1 goto ffmpeg_missing
where ffprobe >nul 2>nul
if errorlevel 1 goto ffmpeg_missing

if not exist ".venv-core\Scripts\python.exe" (
    echo [1/3] Creating Python environment...
    py -3.11 -m venv .venv-core
    if errorlevel 1 goto failed
)
echo [2/3] Installing interface, FSRS and Whisper...
".venv-core\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv-core\Scripts\python.exe" -m pip install -r requirements-core.txt
if errorlevel 1 goto failed

echo [3/3] Checking dependencies...
".venv-core\Scripts\python.exe" -c "import streamlit,fsrs,faster_whisper,PIL;print('All core modules available')"
if errorlevel 1 goto failed
ffmpeg -version >nul
if errorlevel 1 goto failed

echo.
echo Ready! Double-click 2_START_WINDOWS.bat.
echo For English medical flashcards, run 3_INSTALL_AI_WINDOWS.bat.
echo For voice separation only, run 4_OPTIONAL_DEMUCS_WINDOWS.bat.
goto done

:python_missing
echo Python 3.11 (64-bit) is not installed or its launcher is unavailable.
echo Install it from https://www.python.org/downloads/windows/
echo Or use: winget install -e --id Python.Python.3.11
echo Then CLOSE this window and rerun the installer.
goto failed

:ffmpeg_missing
echo FFmpeg / ffprobe are missing from PATH.
echo Install with: winget install -e --id Gyan.FFmpeg
echo Then CLOSE this window and rerun the installer.
goto failed

:failed
echo.
echo Installation did not complete. Read the message above.
pause
exit /b 1

:done
echo.
pause
exit /b 0
