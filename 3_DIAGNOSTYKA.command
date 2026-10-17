#!/bin/bash
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
echo "🔍 DIAGNOSTYKA OLUSIA AI STUDIO 2.4"
echo "macOS: $(sw_vers -productVersion 2>/dev/null || echo '?')"
echo "Procesor: $(uname -m)"
command -v brew >/dev/null && echo "✓ Homebrew: $(command -v brew)" || echo "✗ Brak Homebrew"
command -v python3.11 >/dev/null && echo "✓ Python 3.11: $(command -v python3.11)" || echo "✗ Brak Python 3.11"
command -v ffmpeg >/dev/null && echo "✓ FFmpeg: $(command -v ffmpeg)" || echo "✗ Brak FFmpeg"
[ -x .venv-core/bin/python ] && .venv-core/bin/python -c 'import streamlit, faster_whisper; print("✓ Strona i Whisper")' 2>&1 || echo "✗ Strona / Whisper — uruchom instalator"
[ -x .venv-isolation/bin/python ] && .venv-isolation/bin/python -c 'import demucs, torchaudio; print("✓ Izolacja głosu")' 2>&1 || echo "✗ Demucs — uruchom instalator"
[ -x .venv-core/bin/python ] && .venv-core/bin/python -c 'import fsrs; print("✓ Olusia Learning Plus (FSRS)")' 2>&1 || echo "✗ FSRS — uruchom 5_DOINSTALUJ_FISZKI.command"
echo
read -r -p "ENTER, aby zakończyć." _ || true
