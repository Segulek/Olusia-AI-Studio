@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Olusia AI Studio - One local AI engine
echo.
echo One model for handwritten notes, English flashcards
echo and oral answer feedback.
echo Model: qwen3-vl:4b (around 3.3 GB plus dependencies)
echo No other Ollama model is required by Learning Plus.
echo.
if not exist ".venv-core\Scripts\python.exe" (
  echo First run 1_INSTALL_WINDOWS.bat
  goto failed
)
where ollama >nul 2>nul
if errorlevel 1 (
  echo Please install the official Ollama for Windows:
  echo https://ollama.com/download/windows
  echo Reopen this window after installation.
  goto failed
)
".venv-core\Scripts\python.exe" -c "import re,subprocess;v=subprocess.check_output(['ollama','--version'],text=True);m=re.search(r'(\d+)\.(\d+)\.(\d+)',v);assert m and tuple(map(int,m.groups()))>=(0,12,7)"
if errorlevel 1 (
  echo Update Ollama to version 0.12.7 or newer before continuing.
  echo https://ollama.com/download/windows
  goto failed
)
echo.
echo Installing required light Python libraries...
".venv-core\Scripts\python.exe" -m pip install "fsrs>=6.0,<7" "Pillow>=10,<13"
if errorlevel 1 goto failed
echo Downloading model once. It will later work offline.
ollama pull qwen3-vl:4b
if errorlevel 1 (
  echo If Ollama is not running, open the Ollama Windows app first.
  goto failed
)
echo.
echo Success. Open 2_START_WINDOWS.bat and choose Fiszki.
pause
exit /b 0
:failed
echo Setup incomplete.
pause
exit /b 1
