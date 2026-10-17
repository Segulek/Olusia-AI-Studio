#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

finish() {
    code=$?
    echo
    if [ "$code" -eq 0 ]; then
        echo "✅ INSTALACJA ZAKOŃCZONA. Uruchom 2_URUCHOM.command."
    else
        echo "❌ Instalacja przerwana. Sprawdź komunikaty wyżej i spróbuj ponownie."
    fi
    echo "Naciśnij ENTER, by zamknąć to okno."
    read -r _ || true
}
trap finish EXIT

echo "🎧 OLUSIA AI STUDIO — INSTALACJA NA MACU"
echo "========================================"
echo "Zainstalujemy Python 3.11, FFmpeg oraz lokalne biblioteki AI."
echo "Internet jest potrzebny tylko do instalacji i pobrania modeli."
echo "Modele AI działają później bez opłat za transkrypcję."
echo

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Ta instalacja jest przeznaczona dla macOS."
    exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
    echo "Brakuje Homebrew. Najpierw zainstaluj go z oficjalnej strony: https://brew.sh"
    echo "Po instalacji Homebrew ponownie kliknij 1_ZAINSTALUJ.command."
    exit 1
fi

echo "[1/4] Sprawdzam Pythona i FFmpeg..."
if ! command -v python3.11 >/dev/null 2>&1; then
    brew install python@3.11
fi
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    brew install ffmpeg
fi
if ! command -v python3.11 >/dev/null 2>&1; then
    echo "Nie udało się znaleźć Python 3.11."
    exit 1
fi

PYTHON_BIN="$(command -v python3.11)"
echo "[2/4] Instaluję interfejs i transkrypcję Whisper..."
"$PYTHON_BIN" -m venv .venv-core
.venv-core/bin/python -m pip install --upgrade pip
.venv-core/bin/python -m pip install -r requirements-core.txt

echo "[3/4] Instaluję Demucs do izolowania głosu (to może pobrać duże biblioteki)..."
"$PYTHON_BIN" -m venv .venv-isolation
.venv-isolation/bin/python -m pip install --upgrade pip
ARCH="$(uname -m)"
if [ "$ARCH" = "arm64" ]; then
    # PyTorch 2.6 keeps the older torchaudio.save API required by Demucs 4.0.1.
    .venv-isolation/bin/python -m pip install "numpy>=1.24,<2" "torch==2.6.0" "torchaudio==2.6.0" "demucs==4.0.1"
elif [ "$ARCH" = "x86_64" ]; then
    # 2.2.x is the last macOS x86_64 wheel series.
    .venv-isolation/bin/python -m pip install "numpy>=1.24,<2" "torch==2.2.2" "torchaudio==2.2.2" "demucs==4.0.1"
else
    echo "Nieobsługiwany procesor Maca: $ARCH"
    exit 1
fi

echo "[4/4] Kontroluję instalację..."
.venv-core/bin/python -c "import streamlit, faster_whisper; print('✓ Strona i Whisper działają')"
.venv-isolation/bin/python -c "import torch, torchaudio, demucs; print('✓ Demucs i Torch działają')"
ffmpeg -version | head -1
printf '\nModele Whisper i Demucs będą pobrane przy pierwszym użyciu odpowiednich przycisków.\n'
