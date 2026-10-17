#!/bin/bash
# One-time migration for users of the original Olusia AI Studio v1.
set -euo pipefail
SOURCE="$(cd "$(dirname "$0")" && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
finish() {
  code=$?
  echo
  if [ "$code" -eq 0 ]; then
    echo "✅ Zaktualizowano poprzednią aplikację do v2.1 — bez ponownej instalacji Whisper i Demucs."
  else
    echo "❌ Migracja nie została ukończona."
  fi
  echo "Wciśnij ENTER, aby zamknąć okno."
  read -r _ || true
}
trap finish EXIT
printf '🎧 Olusia AI Studio v2.1 — uaktualnienie obecnej, działającej wersji\n'
printf 'Wskaż w Finderze folder starej aplikacji (ten z 2_URUCHOM.command).\n'
printf 'Zamknij najpierw starą aplikację (Ctrl+C w jej oknie Terminala).\n\n'
if [ "$#" -gt 0 ]; then
  TARGET="$1"
else
  TARGET="$(osascript -e 'POSIX path of (choose folder with prompt "Wybierz folder starego Olusia AI Studio:")')" || exit 1
fi
if [ ! -f "$TARGET/app.py" ] || [ ! -f "$TARGET/processor.py" ]; then
  echo "To nie jest folder starej aplikacji. Brakuje app.py lub processor.py."
  exit 1
fi
if [ "$(cd "$TARGET" && pwd)" = "$SOURCE" ]; then
  echo "To jest folder nowej paczki. Nie trzeba kopiować go do siebie."
  exit 0
fi
# Only copy program code; deliberately preserve both virtual environments and other files.
FILES=(
  app.py processor.py cards.py flashcards_ui.py ocr_local.py updater.py updates_ui.py
  requirements-core.txt README.md START_TUTAJ.html
  1_ZAINSTALUJ.command 2_URUCHOM.command 3_DIAGNOSTYKA.command
  4_AKTUALIZUJ.command 5_DOINSTALUJ_FISZKI.command 6_UTWORZ_APLIKACJE.command
  0_UAKTUALIZUJ_STARA_WERSJE.command update_source.json VERSION
)
for file in "${FILES[@]}"; do
  cp "$SOURCE/$file" "$TARGET/$file"
done
mkdir -p "$TARGET/.streamlit"
cp "$SOURCE/.streamlit/config.toml" "$TARGET/.streamlit/config.toml"
chmod +x "$TARGET"/*.command
printf '\nZaktualizowano folder: %s\n' "$TARGET"
printf 'TERAZ: uruchom w nim 5_DOINSTALUJ_FISZKI.command, a potem 2_URUCHOM.command.\n'
