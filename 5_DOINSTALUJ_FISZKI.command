#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
finish() {
  code=$?
  echo
  if [ "$code" -eq 0 ]; then
    echo "✅ Fiszki AI gotowe. Uruchom ponownie Olusia AI Studio."
  else
    echo "❌ Instalacja modułu fiszek nie powiodła się — szczegóły wyżej."
  fi
  echo "Wciśnij ENTER, aby zamknąć okno."
  read -r _ || true
}
trap finish EXIT
if [ "$(uname -s)" != "Darwin" ]; then
  echo "Ten instalator wymaga macOS."
  exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Najpierw zainstaluj Homebrew z https://brew.sh"
  exit 1
fi
printf '📚 Instaluję jeden lokalny silnik do fiszek AI i zdjęć...\n'
printf 'Potrzeba internetu i około 3,3 GB na jeden silnik AI (+ biblioteki).\n\n'

if [ ! -x .venv-core/bin/python ]; then
  echo "Najpierw uruchom 1_ZAINSTALUJ.command."
  exit 1
fi
printf "Instaluję FSRS — lokalny algorytm adaptacyjnych powtórek...\n"
.venv-core/bin/python -m pip install "fsrs>=6.0,<7" "Pillow>=10,<13"

# OCR is optional and deliberately not installed by the single-model setup.
if ! command -v ollama >/dev/null 2>&1; then
  brew install ollama
fi
printf '\nUruchamiam lokalny serwer Ollama...\n'
brew services start ollama || true

# Service may need time to bind loopback the first time.
ready=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  echo "Ollama nie odpowiada na porcie 11434. Uruchom w Terminalu: brew services restart ollama"
  exit 1
fi

printf '\n🧠 Jeden silnik AI do tekstu, zdjęć i egzaminu ustnego.\n'
printf 'Pobieram Qwen3-VL 4B (ok. 3,3 GB). Nie instaluje się już osobnych modeli tekstowych.\n'
printf 'Wymagana jest Ollama 0.12.7 lub nowsza.\n'

if ! .venv-core/bin/python -c 'import re, subprocess; s=subprocess.check_output(["ollama","--version"],text=True); m=re.search(r"(\d+)\.(\d+)\.(\d+)",s); assert m and tuple(map(int,m.groups())) >= (0,12,7)' >/dev/null 2>&1; then
  echo "Aktualizuję Ollamę do wersji obsługującej rozpoznawanie zdjęć..."
  brew upgrade ollama || { echo "Nie udało się zaktualizować Ollamy. Uruchom: brew upgrade ollama"; exit 1; }
  brew services restart ollama || true
fi
ollama pull qwen3-vl:4b
echo "✅ Jeden lokalny silnik do nauki jest gotowy."
printf '\nZainstalowano model: qwen3-vl:4b\n'
printf 'Możesz korzystać offline po pobraniu modelu, bez płacenia za fiszki.\n'
