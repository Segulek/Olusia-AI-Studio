OLUSIA AI STUDIO 2.8.0 - WINDOWS 10/11 x64
=======================================

Olusia Learning Plus + English medical flashcards + Whisper
+ audio tools + local backups. Runs on YOUR Windows computer
through a local Streamlit window in the browser (127.0.0.1).
NOT a standalone .exe. Models and dependencies downloaded separately.

QUICK START
1. Extract this ZIP to a regular directory such as Documents\Olusia AI Studio.
2. Install Python 3.11 x64 from python.org.
   Install FFmpeg from https://www.gyan.dev/ffmpeg/builds/
   or with: winget install -e --id Gyan.FFmpeg
   Close/reopen the Command Prompt after changing PATH.
3. Double-click 1_INSTALL_WINDOWS.bat (basic app + local Whisper).
4. Double-click 3_INSTALL_AI_WINDOWS.bat (one Qwen3-VL 4B model,
   approx 3.3 GB) if you want flashcards or image understanding.
   It will ask you to install Ollama from its official site if missing.
5. Double-click 2_START_WINDOWS.bat and open http://127.0.0.1:8501
6. Optional: 4_OPTIONAL_DEMUCS_WINDOWS.bat for heavy voice isolation.

NOTES
- No subscription and no cloud API for study materials.
- Internet is required the first time to download dependencies/models.
- English-only medical flashcards with manual verification of medical facts.
- Audio transcription uses Whisper, not the generative Qwen model.
- Voice separation is OPTIONAL and needs additional PyTorch packages.
- Classical OCR is OPTIONAL; images work through Qwen3-VL.
- User data / study review history / compressed local backups are kept in
  %LOCALAPPDATA%\Olusia AI Studio\ (separate from application files).
- Backups auto-retain the last seven UTC days; manual archives are not pruned.
- Mac and Windows store separate user databases. Use the built-in backup ZIP
  export / restore to transfer cards and FSRS history between computers.
- Running two copies using the same data folder simultaneously is unsupported.
- Windows Defender or SmartScreen may warn about unrecognized BAT files.
  Always download from the official release; inspect BAT files if unsure.
- No elevated permissions required by the application itself.
- The release ZIP contains code/scripts, NOT pre-downloaded Ollama models.

SPACE: basic Python + FFmpeg + Whisper dependencies may take 1-3 GB
depending on system; the Qwen3-VL 4B model adds about 3.3 GB.
Demucs adds substantial extra libraries, so leave it uninstalled if unused.

UPDATES: use the Updates tab after installation. Updates only modify
allowlisted application source files, never your models or user databases.
Restart by closing the CMD window and double-clicking 2_START_WINDOWS.bat.

Official code: https://github.com/Segulek/Olusia-AI-Studio
Official releases: https://github.com/Segulek/Olusia-AI-Studio/releases
