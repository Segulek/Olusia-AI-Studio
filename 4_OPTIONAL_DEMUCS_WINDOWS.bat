@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Olusia AI Studio - Optional voice separation
echo.
echo OPTIONAL: Install Demucs and PyTorch for isolating vocals.
echo Requires additional disk space (often over 1 GB).
echo Skip this step if you only need flashcards and transcription.
echo.
if not exist ".venv-core\Scripts\python.exe" (
  echo First run 1_INSTALL_WINDOWS.bat
  goto failed
)
set /p CONFIRM=Install extra Demucs dependencies? [Y/N]:
if /i not "%CONFIRM%"=="Y" (
  echo Skipped. No changes made.
  pause
  exit /b 0
)
if not exist ".venv-isolation\Scripts\python.exe" (
  py -3.11 -m venv .venv-isolation
  if errorlevel 1 goto failed
)
".venv-isolation\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv-isolation\Scripts\python.exe" -m pip install "numpy>=1.24,<2" "torch==2.6.0" "torchaudio==2.6.0" "demucs==4.0.1"
if errorlevel 1 goto failed
".venv-isolation\Scripts\python.exe" -c "import torch,torchaudio,demucs;print('Demucs and PyTorch available')"
if errorlevel 1 goto failed
echo Demucs is installed. Voice isolation may run slowly on CPU.
pause
exit /b 0
:failed
echo Demucs setup failed. Other studio features still work.
pause
exit /b 1
