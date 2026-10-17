#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
finish() {
  code=$?
  echo
  if [ "$code" -eq 0 ]; then
    echo "✅ Gotowe. Zrestartuj aplikację: Ctrl+C w Terminalu, następnie 2_URUCHOM.command."
  else
    echo "❌ Aktualizacja nie została zainstalowana. Szczegóły powyżej."
  fi
  echo "Wciśnij ENTER, aby zamknąć okno."
  read -r _ || true
}
trap finish EXIT
if [ ! -x .venv-core/bin/python ]; then
  echo "Nie ma zainstalowanego środowiska aplikacji. Uruchom 1_ZAINSTALUJ.command."
  exit 1
fi
if [ "$#" -gt 0 ]; then
  ZIP="$1"
else
  ZIP="$(osascript -e 'POSIX path of (choose file with prompt "Wybierz paczkę aktualizacji Olusia AI Studio (.zip):")')" || exit 1
fi
if [ ! -f "$ZIP" ]; then
  echo "Nie znaleziono wybranego pliku."
  exit 1
fi
.venv-core/bin/python - "$PWD" "$ZIP" <<'PY'
from pathlib import Path
import sys
from updater import apply_update, UpdateError, VERSION
try:
    result = apply_update(Path(sys.argv[2]).read_bytes(), Path(sys.argv[1]), VERSION)
    print(f"✅ Aktualizacja do v{result} zainstalowana.")
except UpdateError as exc:
    print(f"❌ {exc}")
    sys.exit(1)
PY
