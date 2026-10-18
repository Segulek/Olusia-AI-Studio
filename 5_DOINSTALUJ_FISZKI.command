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
printf '📚 Instaluję darmowe, lokalne fiszki AI (OCR i model językowy)...\n'
printf 'Potrzeba internetu i około 2–4 GB miejsca.\n\n'

if [ ! -x .venv-core/bin/python ]; then
  echo "Najpierw uruchom 1_ZAINSTALUJ.command."
  exit 1
fi
printf "Instaluję FSRS — lokalny algorytm adaptacyjnych powtórek...\n"
.venv-core/bin/python -m pip install "fsrs>=6.0,<7"

if ! command -v tesseract >/dev/null 2>&1; then
  brew install tesseract
fi
if ! brew list --formula tesseract-lang >/dev/null 2>&1; then
  brew install tesseract-lang
fi
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

printf '\nWybierz model do fiszek:\n'
printf '  1 — dokładniejszy (qwen2.5:3b, ok. 1,9 GB) [domyślny]\n'
printf '  2 — lżejszy (qwen2.5:1.5b, ok. 1 GB)\n'
read -r -p 'Wybór [1/2]: ' CHOICE || true
if [ "${CHOICE:-1}" = "2" ]; then
  MODEL="qwen2.5:1.5b"
else
  MODEL="qwen2.5:3b"
fi
echo "Pobieram lokalny model $MODEL — tylko przy pierwszym uruchomieniu..."
ollama pull "$MODEL"
echo
echo "🧠 Dodatkowy tryb rozumienia zdjęć notatek (opcjonalny)"
echo "  Model qwen3-vl:2b zajmuje około 1,9 GB i wymaga Ollama 0.12.7+."
read -r -p "Czy pobrać model Vision AI? [t/N]: " VISION_CHOICE || true
if [ "${VISION_CHOICE:-n}" = "t" ] || [ "${VISION_CHOICE:-n}" = "T" ] || [ "${VISION_CHOICE:-n}" = "y" ] || [ "${VISION_CHOICE:-n}" = "Y" ]; then
  echo "Pobieram osobny lokalny model obrazu..."
  ollama pull qwen3-vl:2b
else
  echo "Pominięto model obrazu — możesz pobrać go później: ollama pull qwen3-vl:2b"
fi
if ! command -v tesseract >/dev/null 2>&1; then
  echo "Nie znaleziono Tesseract po instalacji."
  exit 1
fi
printf '\nZainstalowano model: %s\n' "$MODEL"
printf 'Możesz korzystać offline po pobraniu modelu, bez płacenia za fiszki.\n'
