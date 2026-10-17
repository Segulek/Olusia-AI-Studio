#!/bin/bash
# Builds a locally generated .app launcher with no paid Apple developer membership.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
finish() {
  code=$?
  echo
  if [ "$code" -eq 0 ]; then
    echo "✅ Ikona aplikacji została utworzona."
  else
    echo "❌ Nie udało się utworzyć aplikacji."
  fi
  echo "Wciśnij ENTER, aby zamknąć okno."
  read -r _ || true
}
trap finish EXIT
if [ "$(uname -s)" != "Darwin" ]; then
  echo "Wymagany macOS."
  exit 1
fi
if [ ! -f "$BASE/2_URUCHOM.command" ]; then
  echo "Brak pliku uruchamiającego."
  exit 1
fi
APPS="$HOME/Applications"
BUNDLE="$APPS/Olusia AI Studio.app"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"
cat > "$BUNDLE/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundleIdentifier</key><string>local.olusia.aistudio</string>
  <key>CFBundleName</key><string>Olusia AI Studio</string>
  <key>CFBundleDisplayName</key><string>Olusia AI Studio</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>2.1.1</string>
  <key>CFBundleShortVersionString</key><string>2.1.1</string>
</dict></plist>
PLIST
{
  echo '#!/bin/bash'
  printf 'open -a Terminal %q\n' "$BASE/2_URUCHOM.command"
  echo 'sleep 2'
  echo 'open "http://127.0.0.1:8501"'
} > "$BUNDLE/Contents/MacOS/launcher"
chmod +x "$BUNDLE/Contents/MacOS/launcher"
touch "$BUNDLE"
printf '\nAplikacja: %s\n' "$BUNDLE"
printf 'Ikona otwiera Terminal (serwer) oraz stronę w przeglądarce. To lekka otoczka .app, nie natywne GUI.\n'
