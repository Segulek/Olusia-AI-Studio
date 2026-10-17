#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if [ ! -x .venv-core/bin/python ]; then
    echo "Najpierw kliknij 1_ZAINSTALUJ.command"
    echo "ENTER, aby zamknąć."
    read -r _ || true
    exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "Nie znaleziono FFmpeg. Ponownie uruchom instalator."
    read -r _ || true
    exit 1
fi
printf '\n🎧 Uruchamiam Olusia AI Studio...\n'
printf 'Strona: http://127.0.0.1:8501\n'
printf 'Aby zakończyć, wróć do tego okna i naciśnij Ctrl+C.\n\n'
exec .venv-core/bin/python -m streamlit run app.py \
    --server.address=127.0.0.1 --server.port=8501
